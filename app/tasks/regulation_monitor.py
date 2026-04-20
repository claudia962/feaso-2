"""
Monthly regulation drift scan.

Walks all stored RegulationAssessment rows, re-resolves the current profile
from `regulation_scraper`, and updates `last_verified` / `regulation_risk_score`
when they've drifted. Flags affected analyses as `needs_review` so a human can
look again before trusting the original recommendation.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.database_models import FeasibilityAnalysis, RegulationAssessment
from app.services.regulation_scraper import lookup_regulation
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


async def _scan(db: AsyncSession) -> list[dict]:
    rows = (await db.execute(select(RegulationAssessment))).scalars().all()
    changes: list[dict] = []
    for row in rows:
        # Re-resolve by pulling the related analysis address.
        analysis = (await db.execute(
            select(FeasibilityAnalysis).where(FeasibilityAnalysis.id == row.feasibility_id)
        )).scalar_one_or_none()
        if not analysis:
            continue

        fresh = lookup_regulation(analysis.address)
        drift: dict = {"id": str(row.feasibility_id), "address": analysis.address}
        dirty = False

        if bool(row.str_allowed) != bool(fresh.str_allowed):
            drift["str_allowed"] = {"old": row.str_allowed, "new": fresh.str_allowed}
            row.str_allowed = fresh.str_allowed
            dirty = True
        if (row.max_nights_per_year or 0) != (fresh.max_nights_per_year or 0):
            drift["max_nights_per_year"] = {"old": row.max_nights_per_year, "new": fresh.max_nights_per_year}
            row.max_nights_per_year = fresh.max_nights_per_year
            dirty = True
        old_score = float(row.regulation_risk_score or 0)
        if abs(old_score - fresh.regulation_risk_score) >= 5:
            drift["risk_score"] = {"old": old_score, "new": fresh.regulation_risk_score}
            row.regulation_risk_score = fresh.regulation_risk_score
            dirty = True

        if dirty:
            row.last_verified = datetime.now(timezone.utc)
            await db.execute(
                update(FeasibilityAnalysis)
                .where(FeasibilityAnalysis.id == row.feasibility_id)
                .values(status="needs_review")
            )
            changes.append(drift)
    if changes:
        await db.commit()
    logger.info("regulation_monitor.complete", total=len(rows), drifted=len(changes))
    return changes


async def _run() -> list[dict]:
    async with AsyncSessionLocal() as db:
        return await _scan(db)


@celery_app.task(name="app.tasks.regulation_monitor.scan_for_changes")
def scan_for_changes() -> list[dict]:
    return asyncio.run(_run())
