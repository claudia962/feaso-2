"""Test GET /api/renovations/{feasibility_id} returns renovation ROI data."""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from decimal import Decimal


@pytest.mark.asyncio
async def test_renovations_endpoint_returns_renovations():
    """GET /api/renovations/{id} should return 200 with a renovations list."""
    fake_id = uuid4()

    # Mock feasibility record
    mock_feas = MagicMock()
    mock_feas.id = fake_id

    # Build mock execute results for sequential calls
    # Call 1: select(FeasibilityAnalysis) → .scalar_one_or_none()
    feas_result = MagicMock()
    feas_result.scalar_one_or_none.return_value = mock_feas

    # Call 2: select(CompAnalysis) → .scalars().all()  (empty — uses defaults)
    comps_result = MagicMock()
    comps_scalars = MagicMock()
    comps_scalars.all.return_value = []
    comps_result.scalars.return_value = comps_scalars

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=[feas_result, comps_result])

    from app.main import app
    from app.api.dependencies import get_session

    async def override():
        yield mock_db

    app.dependency_overrides[get_session] = override
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get(f"/api/renovations/{fake_id}")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert resp.status_code == 200
    data = resp.json()
    assert "renovations" in data
    assert isinstance(data["renovations"], list)
    assert data["count"] == len(data["renovations"])
    # Default renovation items should be returned even with no comps
    assert len(data["renovations"]) > 0
    assert data["feasibility_id"] == str(fake_id)
