"""
Comp analyzer — per-spec weighted similarity scoring and ranking.

The most important service: garbage comps = garbage projections.
See PROMPT spec section "Comp Selection Is Everything".

Weights (tunable via CompAnalyzerConfig):
  0.35 bedrooms  +  0.25 property type  +  0.20 distance  +  0.20 quality
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


# --------------------------------------------------------------------------- #
# Config & scoring primitives                                                  #
# --------------------------------------------------------------------------- #

@dataclass
class CompAnalyzerConfig:
    """Tunable weights + thresholds. Override via settings if needed."""
    weight_bedrooms: float = 0.35
    weight_type: float = 0.25
    weight_distance: float = 0.20
    weight_quality: float = 0.20
    min_good_comps: int = 5
    min_similarity_for_good: float = 0.5
    max_radius_km: float = 10.0
    default_radius_km: float = 5.0


# Property type similarity graph (symmetric, transitive within a tier)
TYPE_FAMILIES: dict[str, set[str]] = {
    "apartment": {"apartment", "condo", "unit", "flat", "studio"},
    "house": {"house", "villa", "detached", "single_family"},
    "townhouse": {"townhouse", "row_house", "duplex"},
    "cabin": {"cabin", "cottage", "chalet", "tiny_house", "bungalow"},
}


def _bedroom_similarity(subject: Optional[int], comp: Optional[int]) -> float:
    """1.0 exact, 0.7 ±1, 0.3 ±2, 0.0 ±3+"""
    if subject is None or comp is None:
        return 0.5  # neutral when unknown
    diff = abs(subject - comp)
    if diff == 0:
        return 1.0
    if diff == 1:
        return 0.7
    if diff == 2:
        return 0.3
    return 0.0


def _type_similarity(subject: Optional[str], comp: Optional[str]) -> float:
    """1.0 exact, 0.5 same family, 0.1 different."""
    if not subject or not comp:
        return 0.5
    s, c = subject.lower().strip(), comp.lower().strip()
    if s == c:
        return 1.0
    for family in TYPE_FAMILIES.values():
        if s in family and c in family:
            return 0.5
    return 0.1


def _distance_similarity(distance_km: Optional[float], max_radius_km: float) -> float:
    """1.0 at 0km, linearly decaying to 0.0 at max_radius_km."""
    if distance_km is None or distance_km < 0:
        return 0.0
    if distance_km >= max_radius_km:
        return 0.0
    return max(0.0, 1.0 - (distance_km / max_radius_km))


def _quality_similarity(subject_score: Optional[float], comp_score: Optional[float]) -> float:
    """
    Quality = review score difference.
      |Δ| < 0.5  → 1.0
      |Δ| < 1.0  → 0.7
      |Δ| ≥ 1.0  → 0.3
    When either is unknown, assume neutral.
    """
    if subject_score is None or comp_score is None:
        return 0.7  # neutral-positive (absent data shouldn't over-punish)
    diff = abs(subject_score - comp_score)
    if diff < 0.5:
        return 1.0
    if diff < 1.0:
        return 0.7
    return 0.3


# --------------------------------------------------------------------------- #
# Public API                                                                   #
# --------------------------------------------------------------------------- #

@dataclass
class SubjectProperty:
    bedrooms: Optional[int] = None
    property_type: Optional[str] = None
    review_score: Optional[float] = None  # if we have the subject's own reviews
    latitude: Optional[float] = None
    longitude: Optional[float] = None


def score_comp(
    subject: SubjectProperty,
    comp: Any,
    config: CompAnalyzerConfig,
) -> float:
    """
    Return the weighted composite similarity in [0.0, 1.0].

    `comp` must expose: .bedrooms, .property_type, .distance_km, .avg_review_score
    (dataclass or ORM object — attribute access is enough).
    """
    b = _bedroom_similarity(subject.bedrooms, getattr(comp, "bedrooms", None))
    t = _type_similarity(subject.property_type, getattr(comp, "property_type", None))
    d = _distance_similarity(getattr(comp, "distance_km", None), config.max_radius_km)
    q = _quality_similarity(subject.review_score, getattr(comp, "avg_review_score", None))

    composite = (
        config.weight_bedrooms * b
        + config.weight_type * t
        + config.weight_distance * d
        + config.weight_quality * q
    )
    return round(composite, 3)


def rank_comps(
    subject: SubjectProperty,
    raw_comps: list[Any],
    config: Optional[CompAnalyzerConfig] = None,
) -> list[tuple[Any, float]]:
    """
    Score every comp, return a list of (comp, similarity) sorted descending.
    Does NOT filter — callers decide the cutoff.
    """
    cfg = config or CompAnalyzerConfig()
    scored = [(c, score_comp(subject, c, cfg)) for c in raw_comps]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored


@dataclass
class CompSetSummary:
    count_good: int           # comps above similarity cutoff
    count_total: int
    low_confidence: bool      # True when < min_good_comps
    reason: Optional[str]     # human-readable if low_confidence
    adr_p25: Optional[float]
    adr_p50: Optional[float]  # median
    adr_p75: Optional[float]
    occupancy_p25: Optional[float]
    occupancy_p50: Optional[float]
    occupancy_p75: Optional[float]
    revenue_p25: Optional[float]
    revenue_p50: Optional[float]
    revenue_p75: Optional[float]


def _quantile(values: list[float], q: float) -> Optional[float]:
    if not values:
        return None
    # Use statistics.quantiles when enough data, else fall back to simple sort.
    if len(values) < 2:
        return float(values[0])
    try:
        qs = statistics.quantiles(values, n=4, method="inclusive")
        # qs = [p25, p50, p75]
        return {0.25: qs[0], 0.50: qs[1], 0.75: qs[2]}[q]
    except statistics.StatisticsError:
        s = sorted(values)
        idx = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
        return float(s[idx])


def summarise_comp_set(
    scored: list[tuple[Any, float]],
    config: Optional[CompAnalyzerConfig] = None,
) -> CompSetSummary:
    """
    Aggregate the ranked comp set into P25/P50/P75 for the drivers of the pro forma.

    Flags low_confidence when fewer than min_good_comps above the similarity cutoff —
    never silently use bad comps (Critical Rule #3).
    """
    cfg = config or CompAnalyzerConfig()
    good = [c for c, s in scored if s >= cfg.min_similarity_for_good]
    low_conf = len(good) < cfg.min_good_comps
    reason = None
    if low_conf:
        reason = (
            f"Only {len(good)} comparable properties above similarity {cfg.min_similarity_for_good:.2f} "
            f"(from {len(scored)} raw). Need at least {cfg.min_good_comps}. "
            f"Projections are directional only — verify manually."
        )

    # Use the top 15 good comps (or all good if fewer) for aggregates.
    set_for_agg = good[: max(10, cfg.min_good_comps * 2)] or [c for c, _ in scored[:10]]

    def _field(name: str) -> list[float]:
        return [float(getattr(c, name)) for c in set_for_agg if getattr(c, name, None) is not None]

    adrs = _field("avg_adr")
    occs = _field("occupancy_rate")
    revs = _field("annual_revenue")

    return CompSetSummary(
        count_good=len(good),
        count_total=len(scored),
        low_confidence=low_conf,
        reason=reason,
        adr_p25=_quantile(adrs, 0.25),
        adr_p50=_quantile(adrs, 0.50),
        adr_p75=_quantile(adrs, 0.75),
        occupancy_p25=_quantile(occs, 0.25),
        occupancy_p50=_quantile(occs, 0.50),
        occupancy_p75=_quantile(occs, 0.75),
        revenue_p25=_quantile(revs, 0.25),
        revenue_p50=_quantile(revs, 0.50),
        revenue_p75=_quantile(revs, 0.75),
    )


def analyze_comps(
    subject: SubjectProperty,
    raw_comps: list[Any],
    config: Optional[CompAnalyzerConfig] = None,
) -> tuple[list[tuple[Any, float]], CompSetSummary]:
    """
    Convenience: rank + summarise in one call.
    Returns (scored_comps_with_similarity, summary).
    """
    ranked = rank_comps(subject, raw_comps, config)
    summary = summarise_comp_set(ranked, config)
    logger.info(
        "comp_analyzer.complete",
        total=summary.count_total,
        good=summary.count_good,
        low_confidence=summary.low_confidence,
    )
    return ranked, summary
