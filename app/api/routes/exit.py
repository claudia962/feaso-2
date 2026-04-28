"""Exit strategy endpoint — models continue-STR / LTR / sell paths."""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_session
from app.models.database_models import CompAnalysis, FeasibilityAnalysis, FinancialProjection
from app.services.exit_strategy import model_exit_strategies

router = APIRouter(prefix="/api/exit", tags=["exit"])


@router.get("/{feasibility_id}")
async def get_exit_strategies(
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

    # Load base financial projection
    base_proj = (await db.execute(
        select(FinancialProjection)
        .where(FinancialProjection.feasibility_id == feasibility_id)
        .where(FinancialProjection.projection_type == "base")
    )).scalar_one_or_none()

    # Derive inputs for the exit strategy model
    purchase_price = float(feas.purchase_price) if feas.purchase_price else 800000.0
    down_payment_pct = float(feas.down_payment_pct) if feas.down_payment_pct else 20.0
    mortgage_rate_pct = float(feas.mortgage_rate_pct) if feas.mortgage_rate_pct else 6.0
    mortgage_term = feas.mortgage_term_years or 30

    cash_invested = purchase_price * (down_payment_pct / 100)
    loan_amount = purchase_price - cash_invested

    # Simple annual mortgage estimate (P&I)
    monthly_rate = (mortgage_rate_pct / 100) / 12
    if monthly_rate > 0 and mortgage_term > 0:
        n_payments = mortgage_term * 12
        monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate) ** n_payments) / ((1 + monthly_rate) ** n_payments - 1)
        annual_mortgage = monthly_payment * 12
    else:
        annual_mortgage = 0.0

    annual_str_noi = float(base_proj.noi) if base_proj and base_proj.noi else 30000.0

    # Get avg ADR from comps
    comps = (await db.execute(
        select(CompAnalysis)
        .where(CompAnalysis.feasibility_id == feasibility_id)
    )).scalars().all()
    avg_adr = (sum(float(c.avg_adr) for c in comps if c.avg_adr) / len(comps)) if comps else 200.0

    result = model_exit_strategies(
        purchase_price=purchase_price,
        annual_str_noi=annual_str_noi,
        annual_mortgage=annual_mortgage,
        cash_invested=cash_invested,
        avg_adr=avg_adr,
    )

    return {
        "feasibility_id": str(feasibility_id),
        **result.as_dict(),
    }
