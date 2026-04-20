"""
RAG engine — methodology citations for report recommendations.

Two modes:
  - Live: ChromaDB + sentence-transformers when available and populated.
  - Graceful: returns empty citations when the knowledge base isn't set up
    yet. Never blocks analysis.

Ingestion pipeline is kept separate (tasks/rag_ingest.py) so this module
stays lightweight at request time.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# Lazy singletons — None if backing stack isn't installed/populated.
_chroma_client: Optional[object] = None
_embedding_model: Optional[object] = None


@dataclass
class Citation:
    source_name: str
    chunk_text: str
    topic_tags: list[str] = field(default_factory=list)
    similarity: float = 0.0


@dataclass
class RAGResponse:
    query: str
    citations: list[Citation] = field(default_factory=list)
    available: bool = False  # False when RAG stack isn't online
    note: Optional[str] = None


def _try_load() -> bool:
    """Attempt to load ChromaDB + embeddings. Return True if both available."""
    global _chroma_client, _embedding_model
    if _chroma_client is not None and _embedding_model is not None:
        return True
    try:  # pragma: no cover  — exercised only in full prod install
        import chromadb
        from sentence_transformers import SentenceTransformer
        _chroma_client = chromadb.PersistentClient(path="/tmp/feaso-chroma")
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        return True
    except Exception as exc:
        logger.info("rag.unavailable", reason=str(exc)[:120])
        return False


def query_methodology(topic: str, top_k: int = 3) -> RAGResponse:
    """
    Return relevant methodology snippets for a report recommendation.

    When RAG isn't set up, returns an empty RAGResponse with `available=False`
    so the report generator can skip the citations block cleanly.
    """
    if not _try_load():
        return RAGResponse(
            query=topic,
            available=False,
            note=(
                "RAG knowledge base not yet populated. Citations will appear "
                "once training content is ingested."
            ),
        )

    # Live path — only runs when chromadb and sentence-transformers are installed.
    try:  # pragma: no cover
        col = _chroma_client.get_or_create_collection("feasibility_methodology")  # type: ignore[union-attr]
        emb = _embedding_model.encode([topic]).tolist()  # type: ignore[union-attr]
        res = col.query(query_embeddings=emb, n_results=top_k)
        citations: list[Citation] = []
        metadatas = res.get("metadatas", [[]])[0]
        documents = res.get("documents", [[]])[0]
        distances = res.get("distances", [[]])[0]
        for md, doc, dist in zip(metadatas, documents, distances):
            citations.append(Citation(
                source_name=md.get("source_name", "unknown"),
                chunk_text=doc,
                topic_tags=md.get("topic_tags", "").split(",") if md.get("topic_tags") else [],
                similarity=round(1.0 - float(dist), 3),
            ))
        return RAGResponse(query=topic, citations=citations, available=True)
    except Exception as exc:
        logger.warning("rag.query_error", error=str(exc)[:200])
        return RAGResponse(query=topic, available=False, note=f"RAG query failed: {exc}")
