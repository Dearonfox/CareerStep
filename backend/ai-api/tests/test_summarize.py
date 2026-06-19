from httpx import AsyncClient, ASGITransport
import pytest_asyncio
import pytest
from app.main import app

@pytest_asyncio.fixture
async def async_client(patch_settings):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

@pytest.fixture(autouse=True)
def mock_mongo_db(monkeypatch):
    """테스트용 MongoDB 모킹"""
    from app.core.mongo import mongo
    from unittest.mock import AsyncMock, MagicMock
    
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=[])
    mock_cursor.limit.return_value = mock_cursor
    mock_db["job_raw"].find.return_value = mock_cursor
    mock_db["job_raw"].aggregate.return_value = mock_cursor
    
    monkeypatch.setattr(mongo, "db", mock_db)
    return mock_db

@pytest.mark.summarize
@pytest.mark.smoke
async def test_summarize_run_dry_run(async_client: AsyncClient, mock_mongo_db):
    """dry_run 모드로 실행 시, 실제 처리를 건너뛰고 대상 건수만 반환하는지 확인"""
    response = await async_client.post(
        "/api/v1/summarize/run",
        json={"dry_run": True, "limit": 2},
        headers={"X-Internal-Key": "test-internal-key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_processed" in data
    assert data["success_count"] == 0

@pytest.mark.summarize
@pytest.mark.smoke
async def test_summarize_status(async_client: AsyncClient, mock_mongo_db):
    """상태 조회 API 확인"""
    # 딕셔너리 형태로 반환하도록 모킹
    mock_mongo_db["job_raw"].aggregate.return_value.to_list.return_value = [
        {"_id": "detailed", "count": 10},
        {"_id": "summarized", "count": 5}
    ]
    response = await async_client.get(
        "/api/v1/summarize/status",
        headers={"X-Internal-Key": "test-internal-key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_jobs" in data
    assert "detailed" in data
    assert "summarized" in data
