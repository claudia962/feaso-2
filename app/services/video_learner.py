"""
Video learner — property walkthrough analysis via Claude Vision.

Graceful: if no video supplied OR ANTHROPIC_API_KEY absent, returns a
noop report so the rest of the pipeline proceeds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import structlog

from app.config import get_settings

logger = structlog.get_logger(__name__)


@dataclass
class VideoAssessment:
    available: bool = False
    condition_score: Optional[float] = None  # 1-10
    positive_features: list[str] = field(default_factory=list)
    visible_issues: list[str] = field(default_factory=list)
    renovation_opportunities: list[dict] = field(default_factory=list)
    note: Optional[str] = None


async def analyse_walkthrough(video_path: Optional[str]) -> VideoAssessment:
    """
    Extract frames from the walkthrough video (2s intervals) and send key frames
    to Claude Vision for assessment.

    No-op path (no video, no key, missing ffmpeg): returns available=False with a
    note. Never raises.
    """
    if not video_path:
        return VideoAssessment(available=False, note="No walkthrough video supplied.")

    if not Path(video_path).exists():
        return VideoAssessment(available=False, note=f"Video not found at {video_path}.")

    settings = get_settings()
    if not getattr(settings, "anthropic_api_key", None):
        return VideoAssessment(
            available=False,
            note="ANTHROPIC_API_KEY not configured — video assessment skipped.",
        )

    # Live path requires ffmpeg + the Anthropic SDK. Kept inside try so missing
    # native deps degrade cleanly rather than crashing the pipeline.
    try:  # pragma: no cover
        import subprocess
        import tempfile
        import base64
        from anthropic import AsyncAnthropic

        frames_dir = Path(tempfile.mkdtemp(prefix="feaso-frames-"))
        subprocess.run(
            ["ffmpeg", "-i", video_path, "-vf", "fps=0.5", str(frames_dir / "f_%04d.jpg")],
            check=True, capture_output=True,
        )
        frame_paths = sorted(frames_dir.glob("f_*.jpg"))[:12]  # cap for cost control
        if not frame_paths:
            return VideoAssessment(available=False, note="ffmpeg produced no frames.")

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        images = []
        for fp in frame_paths:
            with fp.open("rb") as h:
                images.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": base64.b64encode(h.read()).decode("ascii"),
                    },
                })

        msg = await client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{
                "role": "user",
                "content": images + [{
                    "type": "text",
                    "text": (
                        "Assess this property's physical condition, finish quality, and "
                        "identify any visible issues or renovation opportunities. "
                        "Respond as JSON: {condition_score (1-10), positive_features: [...], "
                        "visible_issues: [...], renovation_opportunities: [{item, estimated_cost, "
                        "projected_adr_lift}]}"
                    ),
                }],
            }],
        )
        # Best-effort JSON parse.
        import json
        raw_text = msg.content[0].text if msg.content else "{}"
        parsed: dict = {}
        try:
            # Strip possible markdown code fences.
            cleaned = raw_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            parsed = {"visible_issues": [raw_text[:300]]}

        return VideoAssessment(
            available=True,
            condition_score=parsed.get("condition_score"),
            positive_features=parsed.get("positive_features", []) or [],
            visible_issues=parsed.get("visible_issues", []) or [],
            renovation_opportunities=parsed.get("renovation_opportunities", []) or [],
        )
    except FileNotFoundError as exc:  # ffmpeg missing
        return VideoAssessment(available=False, note=f"ffmpeg not available: {exc}")
    except Exception as exc:
        logger.warning("video_learner.error", error=str(exc)[:200])
        return VideoAssessment(available=False, note=f"Video analysis error: {exc}")
