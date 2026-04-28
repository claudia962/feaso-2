"""Test GET /api/scenarios/{feasibility_id} returns scenario data."""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from decimal import Decimal


@pytest.mark.asyncio
async def test_scenarios_endpoint_returns_base_projection():
    """GET /api/scenarios/{id} should return 200 with a non-null base_projection."""
    fake_id = uuid4()

    # Mock feasibility record
    mock_feas = MagicMock()
    mock_feas.id = fake_id

    # Mock financial projection
    mock_proj = MagicMock()
    mock_proj.projection_type = "base"
    mock_proj.year1_gross_revenue = Decimal("58900")
    mock_proj.noi = Decimal("25000")
    mock_proj.cap_rate = Decimal("0.045")
    mock_proj.cash_on_cash_return = Decimal("0.082")
    mock_proj.break_even_occupancy = Decimal("55.0")
    mock_proj.monthly_projections = [{"month": "jan", "revenue": 5500}]
    mock_proj.annual_expenses = {"cleaning": 8000, "insurance": 2000}

    # Mock stress test
    mock_stress = MagicMock()
    mock_stress.scenario_name = "Demand shock"
    mock_stress.scenario_type = "demand"
    mock_stress.parameters = {"occupancy_drop": 0.15}
    mock_stress.revenue_impact_pct = Decimal("-12.5")
    mock_stress.still_profitable = True
    mock_stress.adaptation_strategy = "Lower ADR to maintain occupancy"

    # Build mock execute results for sequential calls
    # Call 1: select(FeasibilityAnalysis) → .scalar_one_or_none()
    feas_result = MagicMock()
    feas_result.scalar_one_or_none.return_value = mock_feas

    # Call 2: select(FinancialProjection) → .scalar_one_or_none()
    proj_result = MagicMock()
    proj_result.scalar_one_or_none.return_value = mock_proj

    # Call 3: select(FeasibilityStressTest) → .scalars().all()
    stress_result = MagicMock()
    stress_scalars = MagicMock()
    stress_scalars.all.return_value = [mock_stress]
    stress_result.scalars.return_value = stress_scalars

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[feas_result, proj_result, stress_result])

    from app.main import app
    from app.api.dependencies import get_session

    async def override():
        yield mock_db

    app.dependency_overrides[get_session] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/scenarios/{fake_id}")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["base_projection"] is not None
    assert data["base_projection"]["projection_type"] == "base"
    assert data["base_projection"]["year1_gross_revenue"] == 58900.0
    assert "stress_results" in data
    assert len(data["stress_results"]) == 1
    assert data["stress_results"][0]["scenario_name"] == "Demand shock"
    assert data["feasibility_id"] == str(fake_id)
