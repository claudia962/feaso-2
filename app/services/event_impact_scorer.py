"""
Event impact scorer — quantifies the annual revenue contribution from events
near a property. Reads the shared `events` table.

Graceful: if no events found, returns an empty result (not an error).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database_models import Event

logger = structlog.get_logger(__name__)


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


@dataclass
class EventImpact:
    event_id: str
    event_name: str
    start_date: date
    end_date: date
    distance_km: float
    affected_nights: int
    # Conservative default if no history:
    adr_lift_pct: float = 0.30   # +30% ADR during event (realistic for major events)
    occupancy_lift_pct: float = 0.15
    estimated_revenue_lift: float = 0.0


@dataclass
class EventImpactReport:
    events_within_radius: int
    total_event_nights: int
    annual_event_revenue_contribution: float
    events: list[EventImpact] = field(default_factory=list)
    market_comparison: Optional[str] = None  # e.g. "event-advantaged"

    def is_event_advantaged(self, market_avg_event_nights: int = 8) -> bool:
        return self.total_event_nights > market_avg_event_nights * 1.3


async def score_events_near_property(
    db: AsyncSession,
    latitude: float,
    longitude: float,
    baseline_adr: float,
    baseline_occupancy: float,
    radius_km: float = 10.0,
    lookahead_months: int = 12,
) -> EventImpactReport:
    """
    Query events within `radius_km` of the property over the next `lookahead_months`.
    Estimate the incremental revenue contribution.
    """
    rows = (await db.execute(select(Event))).scalars().all()
    impacts: list[EventImpact] = []

    for ev in rows:
        if ev.latitude is None or ev.longitude is None:
            continue
        dist = _haversine_km(latitude, longitude, float(ev.latitude), float(ev.longitude))
        if dist > radius_km:
            continue

        nights = max(1, (ev.end_date - ev.start_date).days + 1)
        lifted_adr = baseline_adr * (1 + 0.30)
        lifted_occ = min(0.97, baseline_occupancy * (1 + 0.15))
        base_revenue = nights * baseline_adr * baseline_occupancy
        lifted_revenue = nights * lifted_adr * lifted_occ
        incremental = max(0.0, lifted_revenue - base_revenue)

        impacts.append(EventImpact(
            event_id=str(ev.id),
            event_name=ev.name,
            start_date=ev.start_date,
            end_date=ev.end_date,
            distance_km=round(dist, 2),
            affected_nights=nights,
            estimated_revenue_lift=round(incremental, 2),
        ))

    total_nights = sum(i.affected_nights for i in impacts)
    total_revenue = sum(i.estimated_revenue_lift for i in impacts)

    report = EventImpactReport(
        events_within_radius=len(impacts),
        total_event_nights=total_nights,
        annual_event_revenue_contribution=round(total_revenue, 2),
        events=impacts,
    )

    if report.events_within_radius == 0:
        report.market_comparison = "No events within radius — no event advantage"
    elif report.is_event_advantaged():
        report.market_comparison = (
            f"Event-advantaged: {total_nights} event nights vs market avg ~8. "
            f"~${total_revenue:,.0f} incremental annual revenue."
        )
    else:
        report.market_comparison = (
            f"Moderate event exposure: {total_nights} event nights. "
            f"~${total_revenue:,.0f} incremental annual revenue."
        )

    logger.info("event_impact.complete", events=len(impacts), nights=total_nights,
                revenue=total_revenue)
    return report
