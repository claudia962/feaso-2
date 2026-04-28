"""Scenarios endpoint — returns base projection for the client-side what-if builder."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.models.database_models import FeasibilityAnalysis, FinancialProjection, FeasibilityStressTest

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@router.get("/{feasibility_id}")
async def get_scenarios(
    feasibility_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    # Verify the analysis exists
    feas = (await db.execute(
        select(FeasibilityAnalysis)
        .where(FeasibilityAnalysis.id == feasibility_id)
    )).scalar_one_or_none()
    if not feas:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    # Load the base financial projection (used by ScenarioBuilder component)
    base_proj = (await db.execute(
        select(FinancialProjection)
        .where(FinancialProjection.feasibility_id == feasibility_id)
        .where(FinancialProjection.projection_type == "base")
    )).scalar_one_or_none()

    base = None
    if base_proj:
        base = {
            "projection_type": base_proj.projection_type,
            "year1_gross_revenue": float(base_proj.year1_gross_revenue) if base_proj.year1_gross_revenue else None,
            "noi": float(base_proj.noi) if base_proj.noi else None,
            "cap_rate": float(base_proj.cap_rate) if base_proj.cap_rate else None,
            "cash_on_cash_return": float(base_proj.cash_on_cash_return) if base_proj.cash_on_cash_return else None,
            "break_even_occupancy": float(base_proj.break_even_occupancy) if base_proj.break_even_occupancy else None,
            "monthly_projections": base_proj.monthly_projections,
            "annual_expenses": base_proj.annual_expenses,
        }

    # Load stress test results as preset scenarios
    stress_rows = (await db.execute(
        select(FeasibilityStressTest)
        .where(FeasibilityStressTest.feasibility_id == feasibility_id)
    )).scalars().all()

    stress_results = [
        {
            "scenario_name": s.scenario_name,
            "scenario_type": s.scenario_type,
            "parameters": s.parameters,
            "revenue_impact_pct": float(s.revenue_impact_pct) if s.revenue_impact_pct is not None else None,
            "still_profitable": s.still_profitable,
            "adaptation_strategy": s.adaptation_strategy,
        }
        for s in stress_rows
    ]

    return {
        "feasibility_id": str(feasibility_id),
        "base_projection": base,
        "stress_results": stress_results,
    }
