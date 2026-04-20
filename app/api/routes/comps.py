"""Comps endpoint — lists ranked comparables for an analysis."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.models.database_models import CompAnalysis

router = APIRouter(prefix="/api/comps", tags=["comps"])


@router.get("/{feasibility_id}")
async def list_comps(
    feasibility_id: UUID,
    db: AsyncSession = Depends(get_session),
    limit: int = 20,
) -> dict[str, Any]:
    rows = (await db.execute(
        select(CompAnalysis)
        .where(CompAnalysis.feasibility_id == feasibility_id)
        .order_by(CompAnalysis.similarity_score.desc().nullslast())
        .limit(limit)
    )).scalars().all()

    if not rows:
        raise HTTPException(status_code=404, detail="No comps for that analysis.")

    return {
        "feasibility_id": str(feasibility_id),
        "count": len(rows),
        "comps": [
            {
                "listing_id": c.comp_listing_id,
                "name": c.comp_name,
                "latitude": float(c.latitude) if c.latitude else None,
                "longitude": float(c.longitude) if c.longitude else None,
                "distance_km": float(c.distance_km) if c.distance_km else None,
                "bedrooms": c.bedrooms,
                "property_type": c.property_type,
                "annual_revenue": float(c.annual_revenue) if c.annual_revenue else None,
                "avg_adr": float(c.avg_adr) if c.avg_adr else None,
                "occupancy_rate": float(c.occupancy_rate) if c.occupancy_rate else None,
                "avg_review_score": float(c.avg_review_score) if c.avg_review_score else None,
                "similarity_score": float(c.similarity_score) if c.similarity_score else None,
                "monthly_revenue": c.monthly_revenue,
                "data_source": c.data_source,
            }
            for c in rows
        ],
    }
