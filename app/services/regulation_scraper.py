"""
Regulation scraper — jurisdiction lookup + risk scoring.

Phase 1 data source: `app/data/regulations.json` (hand-curated per state).
Phase 2+: swap to a real council-scraping pipeline; this module's public
surface stays stable.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "regulations.json"
_cache: Optional[dict] = None


@dataclass
class RegulationProfile:
    municipality: str
    state_key: str
    str_allowed: bool
    permit_required: bool
    permit_type: Optional[str]
    max_nights_per_year: Optional[int]
    occupancy_tax_rate: float
    zoning_compatible: bool
    regulation_risk_score: float  # 0-100
    enforcement_level: str
    pending_legislation: Optional[str]
    notes: str
    last_verified: datetime
    str_effectively_banned: bool  # convenience flag

    @property
    def should_halt_analysis(self) -> bool:
        """
        Critical Rule #11: if STR isn't allowed, lead with that.
        We only halt when the answer is unambiguous (banned or <30 night cap).
        """
        if not self.str_allowed:
            return True
        if self.max_nights_per_year is not None and self.max_nights_per_year < 30:
            return True
        return False


def _load() -> dict:
    global _cache
    if _cache is None:
        _cache = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    return _cache


def _detect_state(address: str) -> str:
    """
    Very simple Australian-state detection — matches the current data file.
    Returns a key that exists in regulations.json.
    """
    a = (address or "").lower()
    if any(k in a for k in (" nsw", ",nsw", "new south wales", "sydney", "newcastle", "wollongong")):
        return "new_south_wales"
    if any(k in a for k in (" qld", ",qld", "queensland", "brisbane", "gold coast", "cairns", "townsville")):
        return "queensland"
    if any(k in a for k in (" vic", ",vic", "victoria", "melbourne", "geelong")):
        return "victoria"
    return "default"


def lookup_regulation(address: str) -> RegulationProfile:
    """
    Resolve regulation data for a free-text address.
    Always returns a RegulationProfile (falls back to `default` entry).
    """
    data = _load()
    state_key = _detect_state(address)
    entry = data.get(state_key, data["default"])

    last_verified_str = entry.get("last_verified") or datetime.now(timezone.utc).date().isoformat()
    try:
        last_verified = datetime.fromisoformat(last_verified_str).replace(tzinfo=timezone.utc)
    except ValueError:
        last_verified = datetime.now(timezone.utc)

    profile = RegulationProfile(
        municipality=state_key.replace("_", " ").title(),
        state_key=state_key,
        str_allowed=bool(entry.get("str_allowed", True)),
        permit_required=bool(entry.get("permit_required", False)),
        permit_type=entry.get("permit_type"),
        max_nights_per_year=entry.get("max_nights_per_year"),
        occupancy_tax_rate=float(entry.get("occupancy_tax_rate", 0.0)),
        zoning_compatible=bool(entry.get("zoning_compatible", True)),
        regulation_risk_score=float(entry.get("regulation_risk_score", 30)),
        enforcement_level=entry.get("enforcement_level", "moderate"),
        pending_legislation=entry.get("pending_legislation"),
        notes=entry.get("notes", ""),
        last_verified=last_verified,
        str_effectively_banned=not bool(entry.get("str_allowed", True)),
    )
    logger.info("regulation.resolved", state=state_key, risk=profile.regulation_risk_score,
                halt=profile.should_halt_analysis)
    return profile
