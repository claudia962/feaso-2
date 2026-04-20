"""
Risk scorer — overall feasibility & risk scoring.

Deliberately transparent (no black-box ML yet). Each input is weighted and
visible. Swap this for a trained model later (revenue_predictor.pkl) without
changing callers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ScoreInputs:
    cap_rate: float                       # 0..1  (e.g. 0.065 for 6.5%)
    cash_on_cash: float                   # 0..1
    occupancy: float                      # 0..1
    neighborhood_score: Optional[float]   # 0..100 (None = unknown)
    regulation_risk: float                # 0..100 (higher = riskier)
    still_profitable_under_stress: bool   # True if ALL stress tests stay profitable
    comp_confidence_low: bool             # True if comp analyzer flagged low confidence


@dataclass
class ScoreOutputs:
    feasibility_score: float  # 0..100 (higher = better)
    risk_score: float         # 0..100 (higher = riskier)
    recommendation: str       # strong_buy / buy / hold / avoid / strong_avoid
    breakdown: dict[str, float]


def compute_scores(inputs: ScoreInputs) -> ScoreOutputs:
    """
    Feasibility = weighted additive model. Spec calls for ML eventually.
    Mapping roughly:
      Cap rate (0..10%)            → up to 25 pts
      Cash-on-cash (0..15%)        → up to 25 pts
      Occupancy (0..100%)          → up to 15 pts
      Neighbourhood (0..100)       → up to 15 pts
      Regulation allowance         → up to 10 pts (inverse of risk)
      Stress-proof bonus           → 10 pts
      Low-comp-confidence penalty  → -10 pts

    Total caps at 100. Minimum 0.
    """
    cap_pts = min(25.0, max(0.0, inputs.cap_rate) * 250.0)       # 10% cap rate = 25 pts
    coc_pts = min(25.0, max(0.0, inputs.cash_on_cash) * 166.67)  # 15% coc = 25 pts
    occ_pts = min(15.0, max(0.0, inputs.occupancy) * 15.0)        # 100% occ = 15 pts
    nbhd_pts = min(15.0, (inputs.neighborhood_score or 0.0) * 0.15)
    reg_pts = min(10.0, max(0.0, (100.0 - inputs.regulation_risk)) * 0.10)
    stress_bonus = 10.0 if inputs.still_profitable_under_stress else 0.0
    comp_penalty = -10.0 if inputs.comp_confidence_low else 0.0

    breakdown = {
        "cap_rate": round(cap_pts, 2),
        "cash_on_cash": round(coc_pts, 2),
        "occupancy": round(occ_pts, 2),
        "neighborhood": round(nbhd_pts, 2),
        "regulation": round(reg_pts, 2),
        "stress_bonus": stress_bonus,
        "comp_penalty": comp_penalty,
    }

    total = sum(breakdown.values())
    feasibility = max(0.0, min(100.0, total))
    # Risk is inverse of feasibility, but shifted by regulation risk.
    risk = max(0.0, min(100.0, 100.0 - feasibility + (inputs.regulation_risk * 0.2)))

    if feasibility >= 75:
        rec = "strong_buy"
    elif feasibility >= 60:
        rec = "buy"
    elif feasibility >= 45:
        rec = "hold"
    elif feasibility >= 30:
        rec = "avoid"
    else:
        rec = "strong_avoid"

    logger.info("risk_scorer.complete", feasibility=feasibility, risk=risk, rec=rec)

    return ScoreOutputs(
        feasibility_score=round(feasibility, 2),
        risk_score=round(risk, 2),
        recommendation=rec,
        breakdown=breakdown,
    )
