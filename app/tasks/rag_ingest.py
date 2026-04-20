"""
RAG ingestion pipeline — transcribe training videos, chunk, embed, persist.

Usage:
  from app.tasks.rag_ingest import ingest_video, ingest_text
  ingest_video(Path("/videos/masterclass-1.mp4"), source_name="Revenue Masterclass, Ch 1")
  ingest_text("…long transcript…", source_name="AirDNA Blog — Seasonality 2026")

All dependencies (openai-whisper, sentence-transformers, chromadb) are
imported lazily so the main app can run without them installed.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)


@dataclass
class IngestionReport:
    source_name: str
    source_type: str
    chunks_written: int
    skipped: bool
    note: Optional[str] = None


# --------------------------------------------------------------------------- #
# Chunking (always available)                                                  #
# --------------------------------------------------------------------------- #

def chunk_text(text: str, target_tokens: int = 500, overlap_tokens: int = 100) -> list[str]:
    """
    Token-aware-ish chunker — approximates tokens by word count (4-char avg).
    500/100 matches the spec.
    """
    # Normalise whitespace then split on paragraph breaks first for better semantic chunks.
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    words: list[str] = []
    chunks: list[str] = []
    for para in paragraphs:
        words.extend(para.split())

    step = max(1, target_tokens - overlap_tokens)
    for start in range(0, len(words), step):
        end = min(len(words), start + target_tokens)
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
    return chunks


# --------------------------------------------------------------------------- #
# Backends                                                                     #
# --------------------------------------------------------------------------- #

def _get_chroma_collection():
    """Return the feasibility_methodology collection, or None."""
    try:  # pragma: no cover
        import chromadb
        client = chromadb.PersistentClient(path="/tmp/feaso-chroma")
        return client.get_or_create_collection("feasibility_methodology")
    except Exception as exc:
        logger.info("rag.chromadb_unavailable", reason=str(exc)[:120])
        return None


def _get_embedder():
    """Return sentence-transformers model, or None."""
    try:  # pragma: no cover
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception as exc:
        logger.info("rag.embedder_unavailable", reason=str(exc)[:120])
        return None


def _transcribe_whisper(video_path: Path) -> Optional[str]:
    """Run local Whisper on a video file. Returns None if Whisper is absent."""
    try:  # pragma: no cover
        import whisper  # type: ignore
    except ImportError:
        logger.info("rag.whisper_local_missing")
        return None
    try:  # pragma: no cover
        model = whisper.load_model("base")
        result = model.transcribe(str(video_path))
        return result.get("text", "")
    except Exception as exc:
        logger.warning("rag.whisper_local_error", error=str(exc))
        return None


def _transcribe_openai(video_path: Path) -> Optional[str]:
    """Fall back to the OpenAI Whisper API if the local model isn't available."""
    settings = get_settings()
    key = getattr(settings, "openai_api_key", None)
    if not key:
        return None
    try:  # pragma: no cover
        from openai import OpenAI
        client = OpenAI(api_key=key)
        with video_path.open("rb") as fh:
            transcript = client.audio.transcriptions.create(model="whisper-1", file=fh)
        return transcript.text
    except Exception as exc:
        logger.warning("rag.whisper_api_error", error=str(exc))
        return None


# --------------------------------------------------------------------------- #
# Public API                                                                   #
# --------------------------------------------------------------------------- #

def ingest_text(
    text: str,
    *,
    source_name: str,
    source_type: str = "document",
    topic_tags: Optional[list[str]] = None,
) -> IngestionReport:
    """Ingest a raw text blob (no transcription step)."""
    if not text.strip():
        return IngestionReport(source_name, source_type, 0, skipped=True, note="empty text")

    col = _get_chroma_collection()
    embedder = _get_embedder()
    if not col or not embedder:
        return IngestionReport(
            source_name, source_type, 0, skipped=True,
            note="chromadb or sentence-transformers not installed",
        )

    chunks = chunk_text(text)
    if not chunks:
        return IngestionReport(source_name, source_type, 0, skipped=True, note="no chunks produced")

    embeddings = embedder.encode(chunks).tolist()
    ids = [f"{source_name}:{i}" for i in range(len(chunks))]
    metadatas = [{
        "source_name": source_name,
        "source_type": source_type,
        "chunk_index": i,
        "topic_tags": ",".join(topic_tags or []),
    } for i in range(len(chunks))]

    col.upsert(ids=ids, documents=chunks, embeddings=embeddings, metadatas=metadatas)  # type: ignore[arg-type]
    logger.info("rag.ingested", source=source_name, chunks=len(chunks))
    return IngestionReport(source_name, source_type, len(chunks), skipped=False)


def ingest_video(
    video_path: Path | str,
    *,
    source_name: str,
    topic_tags: Optional[list[str]] = None,
) -> IngestionReport:
    """
    Transcribe → chunk → embed → persist to ChromaDB.
    Transcription tries local whisper first, then OpenAI API as fallback.
    """
    path = Path(video_path)
    if not path.exists():
        return IngestionReport(source_name, "video", 0, skipped=True, note=f"no file at {path}")

    transcript = _transcribe_whisper(path) or _transcribe_openai(path)
    if not transcript:
        return IngestionReport(
            source_name, "video", 0, skipped=True,
            note="Whisper unavailable (no local install, no OPENAI_API_KEY).",
        )
    return ingest_text(
        transcript,
        source_name=source_name,
        source_type="video",
        topic_tags=topic_tags,
    )


def ingest_corpus(manifest_path: Path | str) -> list[IngestionReport]:
    """
    Batch-ingest from a JSON manifest:
      [
        {"type": "video", "path": "/corpus/ep-1.mp4",
         "source_name": "Masterclass Ep 1", "topic_tags": ["pricing","abr"]},
        {"type": "text",  "path": "/corpus/airdna-seasonality.md",
         "source_name": "AirDNA Seasonality Article"}
      ]
    """
    m = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    reports: list[IngestionReport] = []
    for item in m:
        kind = item.get("type")
        source_name = item["source_name"]
        tags = item.get("topic_tags") or []
        if kind == "video":
            reports.append(ingest_video(item["path"], source_name=source_name, topic_tags=tags))
        elif kind == "text":
            text = Path(item["path"]).read_text(encoding="utf-8")
            reports.append(ingest_text(text, source_name=source_name, topic_tags=tags))
        else:
            reports.append(IngestionReport(source_name, kind or "unknown", 0, skipped=True, note="unknown type"))
    return reports


if __name__ == "__main__":  # pragma: no cover
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m app.tasks.rag_ingest <manifest.json>")
        sys.exit(1)
    for r in ingest_corpus(sys.argv[1]):
        status = "skip" if r.skipped else f"{r.chunks_written} chunks"
        print(f"[{status}] {r.source_name}  ({r.source_type})  {r.note or ''}")
