"""Pydantic v2 schemas for all API request/response types."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AnalysisStatus, Recommendation, ProjectionType  # noqa: F401 -- re-exported


_ORM_CONFIG = ConfigDict(from_attributes=True)


class FeasibilityAnalysisRequest(BaseModel):
    address: str = Field(..., min_length=5)
    property_type: Optional[str] = None
    bedrooms: int = Field(..., ge=1, le=10)
    bathrooms: Decimal = Field(..., ge=1, le=10)
    purchase_price: Decimal = Field(..., gt=0)
    estimated_renovation: Optional[Decimal] = None
    down_payment_pct: Decimal = Field(default=Decimal("20.0"), ge=5, le=100)
    mortgage_rate_pct: Optional[Decimal] = Field(default=Decimal("6.5"))
    mortgage_term_years: int = Field(default=30)
    created_by: Optional[str] = None


class FeasibilityAnalysisResponse(BaseModel):
    analysis_id: UUID
    status: AnalysisStatus
    message: str


class NeighborhoodResponse(BaseModel):
    model_config = _ORM_CONFIG

    walk_score: Optional[int] = None
    transit_score: Optional[int] = None
    bike_score: Optional[int] = None
    nearest_airport_km: Optional[float] = None
    nearest_airport_name: Optional[str] = None
    nearest_beach_km: Optional[float] = None
    nearest_downtown_km: Optional[float] = None
    restaurants_within_1km: Optional[int] = None
    grocery_within_1km: Optional[int] = None
    neighborhood_score: Optional[float] = None
    best_for: Optional[list[str]] = None


class CompAnalysisResponse(BaseModel):
    model_config = _ORM_CONFIG

    comp_listing_id: Optional[str] = None
    comp_name: Optional[str] = None
    distance_km: Optional[float] = None
    bedrooms: Optional[int] = None
    annual_revenue: Optional[float] = None
    avg_adr: Optional[float] = None
    occupancy_rate: Optional[float] = None
    similarity_score: Optional[float] = None
    data_source: str = "mock"


class FinancialProjectionResponse(BaseModel):
    model_config = _ORM_CONFIG

    projection_type: Optional[str] = None
    year1_gross_revenue: Optional[float] = None
    noi: Optional[float] = None
    cap_rate: Optional[float] = None
    cash_on_cash_return: Optional[float] = None
    break_even_occupancy: Optional[float] = None


class FeasibilityStatusResponse(BaseModel):
    model_config = _ORM_CONFIG

    id: UUID
    status: AnalysisStatus
    address: str
    created_at: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    overall_feasibility_score: Optional[float] = None
    risk_score: Optional[float] = None
    recommendation: Optional[str] = None
    recommendation_reasoning: Optional[str] = None
    neighborhood: Optional[NeighborhoodResponse] = None
    comps: list[CompAnalysisResponse] = []
    financials: Optional[FinancialProjectionResponse] = None
    steps_complete: list[str] = []


class RegulationResponse(BaseModel):
    model_config = _ORM_CONFIG

    municipality: Optional[str] = None
    str_allowed: Optional[bool] = None
    permit_required: Optional[bool] = None
    max_nights_per_year: Optional[int] = None
    regulation_risk_score: Optional[float] = None
    last_verified: Optional[datetime] = None


class StressTestRequest(BaseModel):
    scenario_name: str
    scenario_type: str
    parameters: dict[str, Any]


class StressTestResponse(BaseModel):
    model_config = _ORM_CONFIG

    id: UUID
    scenario_name: str
    revenue_impact_pct: Optional[float] = None
    still_profitable: Optional[bool] = None
    adaptation_strategy: Optional[str] = None


class PortfolioFitResponse(BaseModel):
    model_config = _ORM_CONFIG

    existing_property_count: Optional[int] = None
    overall_portfolio_fit_score: Optional[float] = None
    recommendation: Optional[str] = None


class RenovationResponse(BaseModel):
    model_config = _ORM_CONFIG

    renovation_item: str
    estimated_cost: Optional[float] = None
    roi_1yr_pct: Optional[float] = None
    recommendation: Optional[str] = None
    reasoning: Optional[str] = None


class ExitStrategyResponse(BaseModel):
    model_config = _ORM_CONFIG

    strategy_type: str
    estimated_monthly_income: Optional[float] = None
    estimated_annual_return: Optional[float] = None
    notes: Optional[str] = None
