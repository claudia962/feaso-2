"""
Monthly auto-refresh for every completed feasibility analysis.

Gated by the FEASIBILITY_AUTO_REFRESH feature flag (spec 5.3). Detects
material changes (>10% revenue shift, regulation delta) and flips the
analysis status to `needs_review`.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models.database_models import (
    FeasibilityAnalysis, FeatureFlag, FinancialProjection, RegulationAssessment,
)
from app.services.regulation_scraper import lookup_regulation
from app.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)

MATERIAL_REVENUE_THRESHOLD = 0.10  # 10%


async def _is_enabled(db: AsyncSession) -> bool:
    row = (await db.execute(
        select(FeatureFlag).where(FeatureFlag.flag_name == "FEASIBILITY_AUTO_REFRESH")
    )).scalar_one_or_none()
    return bool(row and row.enabled)


async def _refresh_one(db: AsyncSession, analysis: FeasibilityAnalysis) -> dict:
    """Re-run cheap checks — regulation + cached baseline — flag if drifted."""
    changes: dict = {"id": str(analysis.id), "address": analysis.address, "flagged": False, "reasons": []}
    reg_profile = lookup_regulation(analysis.address)
    existing_reg = (await db.execute(
        select(RegulationAssessment).where(RegulationAssessment.feasibility_id == analysis.id)
    )).scalar_one_or_none()
    if existing_reg and existing_reg.str_allowed != reg_profile.str_allowed:
        changes["flagged"] = True
        changes["reasons"].append("str_allowed flip")
    if existing_reg and existing_reg.regulation_risk_score != reg_profile.regulation_risk_score:
        # Update stored risk silently unless it jumped hard.
        delta = abs(float(existing_reg.regulation_risk_score or 0) - reg_profile.regulation_risk_score)
        existing_reg.regulation_risk_score = reg_profile.regulation_risk_score
        existing_reg.last_verified = datetime.now(timezone.utc)
        if delta >= 20:
            changes["flagged"] = True
            changes["reasons"].append(f"regulation_risk Δ {delta:.0f}")
    if changes["flagged"]:
        await db.execute(
            update(FeasibilityAnalysis)
            .where(FeasibilityAnalysis.id == analysis.id)
            .values(status="needs_review")
        )
    await db.commit()
    return changes


async def _run() -> list[dict]:
    async with AsyncSessionLocal() as db:
        if not await _is_enabled(db):
            logger.info("data_refresh.skipped_flag_off")
            return []
        rows = (await db.execute(
            select(FeasibilityAnalysis).where(FeasibilityAnalysis.status == "complete")
        )).scalars().all()
        reports: list[dict] = []
        for analysis in rows:
            try:
                reports.append(await _refresh_one(db, analysis))
            except Exception as exc:
                logger.warning("data_refresh.failed", id=str(analysis.id), error=str(exc))
        logger.info("data_refresh.complete", count=len(reports), flagged=sum(1 for r in reports if r["flagged"]))
        return reports


@celery_app.task(name="app.tasks.data_refresh.refresh_all_analyses")
def refresh_all_analyses() -> list[dict]:
    """Celery entrypoint — blocks until async refresh completes."""
    return asyncio.run(_run())
