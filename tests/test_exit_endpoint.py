"""Test GET /api/exit/{feasibility_id} returns exit strategy data."""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from decimal import Decimal


@pytest.mark.asyncio
async def test_exit_endpoint_returns_strategies():
    """GET /api/exit/{id} should return 200 with paths and recommended_strategy."""
    fake_id = uuid4()

    # Mock feasibility record
    mock_feas = MagicMock()
    mock_feas.id = fake_id
    mock_feas.purchase_price = Decimal("800000")
    mock_feas.down_payment_pct = Decimal("20")
    mock_feas.mortgage_rate_pct = Decimal("6.0")
    mock_feas.mortgage_term_years = 30

    # Mock financial projection
    mock_proj = MagicMock()
    mock_proj.noi = Decimal("45000")

    # Build mock execute results for sequential calls
    # Call 1: select(FeasibilityAnalysis) → .scalar_one_or_none()
    feas_result = MagicMock()
    feas_result.scalar_one_or_none.return_value = mock_feas

    # Call 2: select(FinancialProjection) → .scalar_one_or_none()
    proj_result = MagicMock()
    proj_result.scalar_one_or_none.return_value = mock_proj

    # Call 3: select(CompAnalysis) → .scalars().all()
    comps_result = MagicMock()
    comps_scalars = MagicMock()
    comps_scalars.all.return_value = []
    comps_result.scalars.return_value = comps_scalars

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[feas_result, proj_result, comps_result])

    from app.main import app
    from app.api.dependencies import get_session

    async def override():
        yield mock_db

    app.dependency_overrides[get_session] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/exit/{fake_id}")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    data = resp.json()
    assert "paths" in data
    assert isinstance(data["paths"], list)
    assert len(data["paths"]) == 3  # continue_str, long_term_rental, sell
    assert "recommended_strategy" in data
    assert data["recommended_strategy"] in ["continue_str", "long_term_rental", "sell"]
    assert "recommendation_reasoning" in data
    assert data["feasibility_id"] == str(fake_id)
