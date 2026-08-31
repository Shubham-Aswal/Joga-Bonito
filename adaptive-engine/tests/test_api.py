import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import init_db, close_db


@pytest.mark.asyncio
async def test_health_and_root():
    await init_db(":memory:")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Root endpoint
        root_resp = await client.get("/")
        assert root_resp.status_code == 200
        root_data = root_resp.json()
        assert root_data["service"] == "adaptive-engine"

        # Health endpoint
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert health_data["status"] == "healthy"
        assert health_data["database"] == "connected"
    await close_db()


@pytest.mark.asyncio
async def test_adaptive_api_flow():
    await init_db(":memory:")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Get state for new user
        get_resp = await client.get("/api/v1/adaptive/user_100")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["user_id"] == "user_100"
        assert data["current_level"] == 1
        assert data["is_new_user"] is True

        # 2. Submit high score at level 1 -> should increase to level 2
        score_payload = {
            "user_id": "user_100",
            "game_type": "memory",
            "score": 92,
            "level_played": 1,
            "accuracy": 95.0,
        }
        post_resp = await client.post("/api/v1/adaptive/score", json=score_payload)
        assert post_resp.status_code == 200
        score_data = post_resp.json()
        assert score_data["user_id"] == "user_100"
        assert score_data["current_level"] == 1
        assert score_data["recommended_level"] == 2
        assert score_data["decision"] == "increase"
        assert score_data["challenge_state"] == "too_easy"

        # 3. Get state now -> user should have level 2
        get_resp2 = await client.get("/api/v1/adaptive/user_100")
        assert get_resp2.status_code == 200
        data2 = get_resp2.json()
        assert data2["current_level"] == 2
        assert data2["is_new_user"] is False
        assert 92 in data2["recent_scores"]
    await close_db()
