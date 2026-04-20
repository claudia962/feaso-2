"""
Weekly comp refresh for analyses completed in the last 12 months.

Re-queries AirDNA for each analysis, rescoring similarity with the current
weights. Flags analyses whose top-5 comp revenue median has moved more than
10% since the original run.
"""
from __future__ import annotations

import asyncio
import statistics
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.database_models import CompAnalysis, FeasibilityAnalysis
from app.services.airdna_client import search_comps
from app.services.comp_analyzer import CompAnalyzerConfig, SubjectProperty, analyze_comps
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)

MATERIAL_DELTA = 0.10  # 10%
LOOKBACK_DAYS = 365


async def _refresh_one(db: AsyncSession, analysis: FeasibilityAnalysis) -> dict:
    summary: dict = {"id": str(analysis.id), "flagged": False, "reason": None}
    if analysis.latitude is None or analysis.longitude is None:
        summary["reason"] = "no coordinates"
        return summary

    # Existing median for comparison.
    existing = (await db.execute(
        select(CompAnalysis).where(CompAnalysis.feasibility_id == analysis.id)
    )).scalars().all()
    existing_median = statistics.median(
        [float(c.annual_revenue) for c in existing if c.annual_revenue is not None]
    ) if existing else None

    # Fresh pull.
    raw = await search_comps(
        lat=float(analysis.latitude), lng=float(analysis.longitude),
        radius_km=5.0, bedrooms=analysis.bedrooms,
        property_type=analysis.property_type or "apartment", max_results=20,
    )
    subject = SubjectProperty(
        bedrooms=analysis.bedrooms, property_type=analysis.property_type,
        latitude=float(analysis.latitude), longitude=float(analysis.longitude),
    )
    scored, _ = analyze_comps(subject, raw, CompAnalyzerConfig())
    fresh_median = statistics.median(
        [float(c.annual_revenue) for c, _ in scored[:10] if c.annual_revenue is not None]
    ) if scored else None

    if existing_median and fresh_median:
        delta = abs(fresh_median - existing_median) / existing_median
        summary["delta"] = round(delta, 4)
        summary["old_median"] = existing_median
        summary["new_median"] = fresh_median
        if delta >= MATERIAL_DELTA:
            summary["flagged"] = True
            summary["reason"] = f"comp-median revenue drift {delta:.1%}"
            await db.execute(
                update(FeasibilityAnalysis)
                .where(FeasibilityAnalysis.id == analysis.id)
                .values(status="needs_review")
            )
    await db.commit()
    return summary


async def _run() -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(FeasibilityAnalysis).where(
                FeasibilityAnalysis.created_at >= cutoff,
                FeasibilityAnalysis.status.in_(["complete", "needs_review"]),
            )
        )).scalars().all()
        out: list[dict] = []
        for a in rows:
            try:
                out.append(await _refresh_one(db, a))
            except Exception as exc:
                logger.warning("comp_update.failed", id=str(a.id), error=str(exc))
        logger.info("comp_update.complete", total=len(rows), flagged=sum(1 for r in out if r.get("flagged")))
        return out


@celery_app.task(name="app.tasks.comp_update.refresh_recent_comps")
def refresh_recent_comps() -> list[dict]:
    return asyncio.run(_run())
