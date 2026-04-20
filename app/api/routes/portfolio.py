"""Portfolio-fit endpoint — returns stored fit assessment."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.models.database_models import PortfolioFit

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/{feasibility_id}")
async def get_fit(
    feasibility_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    row = (await db.execute(
        select(PortfolioFit).where(PortfolioFit.feasibility_id == feasibility_id)
    )).scalar_one_or_none()
    if not row:
        # No portfolio assessment = empty portfolio or new owner.
        return {
            "feasibility_id": str(feasibility_id),
            "existing_property_count": 0,
            "overall_score": None,
            "recommendation": (
                "Portfolio fit analysis will be available once existing properties "
                "are added to the system."
            ),
        }
    return {
        "feasibility_id": str(row.feasibility_id),
        "existing_property_count": row.existing_property_count,
        "overall_score": float(row.overall_portfolio_fit_score) if row.overall_portfolio_fit_score else None,
        "recommendation": row.recommendation,
    }
