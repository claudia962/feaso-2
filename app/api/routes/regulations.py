"""Regulations endpoint — surfaces stored regulation assessments."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.models.database_models import RegulationAssessment

router = APIRouter(prefix="/api/regulations", tags=["regulations"])


@router.get("/{feasibility_id}")
async def get_regulation(
    feasibility_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    row = (await db.execute(
        select(RegulationAssessment).where(RegulationAssessment.feasibility_id == feasibility_id)
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="No regulation assessment for that analysis.")
    return {
        "feasibility_id": str(row.feasibility_id),
        "municipality": row.municipality,
        "str_allowed": row.str_allowed,
        "permit_required": row.permit_required,
        "max_nights_per_year": row.max_nights_per_year,
        "regulation_risk_score": float(row.regulation_risk_score) if row.regulation_risk_score else None,
        "last_verified": row.last_verified.isoformat() if row.last_verified else None,
        "notes": row.notes,
    }
