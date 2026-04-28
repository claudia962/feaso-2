"""Renovation ROI endpoint — runs renovation analysis for an analysis."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.models.database_models import CompAnalysis, FeasibilityAnalysis
from app.services.airdna_client import CompData
from app.services.renovation_roi import analyze_renovation_roi

router = APIRouter(prefix="/api/renovations", tags=["renovations"])


@router.get("/{feasibility_id}")
async def get_renovations(
    feasibility_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    # Load the feasibility record
    feas = (await db.execute(
        select(FeasibilityAnalysis)
        .where(FeasibilityAnalysis.id == feasibility_id)
    )).scalar_one_or_none()
    if not feas:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    # Load comps
    rows = (await db.execute(
        select(CompAnalysis)
        .where(CompAnalysis.feasibility_id == feasibility_id)
        .order_by(CompAnalysis.similarity_score.desc().nullslast())
    )).scalars().all()

    # Convert DB rows to CompData objects for the service
    comp_set = [
        CompData(
            listing_id=c.comp_listing_id or "",
            name=c.comp_name or "",
            latitude=float(c.latitude) if c.latitude else 0.0,
            longitude=float(c.longitude) if c.longitude else 0.0,
            distance_km=float(c.distance_km) if c.distance_km else 0.0,
            bedrooms=c.bedrooms or 0,
            property_type=c.property_type or "",
            annual_revenue=float(c.annual_revenue) if c.annual_revenue else 0.0,
            avg_adr=float(c.avg_adr) if c.avg_adr else 0.0,
            occupancy_rate=float(c.occupancy_rate) if c.occupancy_rate else 0.0,
            avg_review_score=float(c.avg_review_score) if c.avg_review_score else 0.0,
            similarity_score=float(c.similarity_score) if c.similarity_score else 0.0,
            monthly_revenue=c.monthly_revenue or {},
            monthly_occupancy=c.monthly_occupancy or {},
            monthly_adr=c.monthly_adr or {},
            data_source=c.data_source or "mock",
        )
        for c in rows
    ]

    # Compute average ADR and occupancy from comps (or use defaults)
    if comp_set:
        avg_adr = sum(c.avg_adr for c in comp_set) / len(comp_set)
        avg_occ = sum(c.occupancy_rate for c in comp_set) / len(comp_set)
    else:
        avg_adr = 200.0
        avg_occ = 0.65

    results = analyze_renovation_roi(comp_set, avg_adr, avg_occ)

    return {
        "feasibility_id": str(feasibility_id),
        "count": len(results),
        "renovations": [r.as_dict() for r in results],
    }
