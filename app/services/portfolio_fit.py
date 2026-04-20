"""
Portfolio fit — how well does this property diversify an existing portfolio?

Gracefully degrades when owner has zero existing properties (returns a
skip-gracefully report per spec).
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database_models import Property

logger = structlog.get_logger(__name__)


@dataclass
class PortfolioFitReport:
    existing_property_count: int
    geographic_diversification: Optional[float]   # 0-100
    seasonal_diversification: Optional[float]     # 0-100
    segment_diversification: Optional[float]      # 0-100
    cannibalisation_risk: Optional[float]         # 0-100 (higher = worse)
    closest_owned_km: Optional[float]
    overall_score: Optional[float]                # 0-100
    recommendation: str


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


async def assess_portfolio_fit(
    db: AsyncSession,
    new_latitude: float,
    new_longitude: float,
    new_property_type: Optional[str],
) -> PortfolioFitReport:
    """
    Compute fit scores. If no existing properties, return a graceful skip.
    """
    rows = (await db.execute(select(Property))).scalars().all()
    # Exclude properties without geo so scoring is honest.
    geo_rows = [p for p in rows if p.latitude is not None and p.longitude is not None]

    if not geo_rows:
        return PortfolioFitReport(
            existing_property_count=0,
            geographic_diversification=None,
            seasonal_diversification=None,
            segment_diversification=None,
            cannibalisation_risk=None,
            closest_owned_km=None,
            overall_score=None,
            recommendation=(
                "Portfolio fit analysis will be available once existing properties are "
                "added to the system."
            ),
        )

    # --- Geographic: wider spread = higher score.
    distances = [
        _haversine_km(new_latitude, new_longitude, float(p.latitude), float(p.longitude))
        for p in geo_rows
    ]
    closest = min(distances)
    # Score: capped at 100 when average distance > 500km, scales linearly.
    avg_dist = statistics.mean(distances)
    geo_div = float(min(100.0, avg_dist / 5.0))

    # --- Segment diversification: new type adds score.
    existing_types = {(p.property_type or "").lower() for p in geo_rows if p.property_type}
    new_type_lower = (new_property_type or "").lower()
    if new_type_lower and new_type_lower not in existing_types:
        seg_div = 90.0
    elif not new_type_lower:
        seg_div = 50.0
    else:
        # already represented — still some value but capped lower
        seg_div = 40.0

    # --- Seasonal diversification: we don't have monthly seasonality per property yet.
    # Proxy: properties in same lat band share seasonality; further north/south → more decorrelated.
    lat_diffs = [abs(new_latitude - float(p.latitude)) for p in geo_rows]
    # >5 deg latitude diff ~= noticeably different climate
    seasonal_div = float(min(100.0, statistics.mean(lat_diffs) * 20.0))

    # --- Cannibalisation: close + same segment = high risk.
    if closest < 2.0 and new_type_lower in existing_types:
        cannibal = 85.0
    elif closest < 10.0 and new_type_lower in existing_types:
        cannibal = 55.0
    elif closest < 2.0:
        cannibal = 40.0
    else:
        cannibal = max(0.0, 20.0 - closest)

    # Composite per spec: 0.25 geo + 0.30 seasonal + 0.25 segment + 0.20 × (100 - cannibal)
    overall = round(
        0.25 * geo_div + 0.30 * seasonal_div + 0.25 * seg_div + 0.20 * (100.0 - cannibal),
        2,
    )

    if overall >= 75:
        verdict = "Excellent portfolio fit"
    elif overall >= 60:
        verdict = "Good portfolio fit"
    elif overall >= 45:
        verdict = "Marginal portfolio fit"
    else:
        verdict = "Poor portfolio fit — significant overlap with existing holdings"

    rec = (
        f"{verdict} ({overall}/100). Existing properties: {len(geo_rows)}. "
        f"Nearest owned: {closest:.1f}km. "
        f"Segment overlap: {'yes' if new_type_lower in existing_types else 'no'}."
    )

    logger.info("portfolio_fit.complete", count=len(geo_rows), score=overall)

    return PortfolioFitReport(
        existing_property_count=len(geo_rows),
        geographic_diversification=round(geo_div, 2),
        seasonal_diversification=round(seasonal_div, 2),
        segment_diversification=round(seg_div, 2),
        cannibalisation_risk=round(cannibal, 2),
        closest_owned_km=round(closest, 2),
        overall_score=overall,
        recommendation=rec,
    )
