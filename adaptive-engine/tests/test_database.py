import pytest
import os
from app.core.database import init_db, close_db, is_db_available, get_connection
from app.models.database import (
    get_user,
    get_or_create_user_on_score,
    update_user_adaptive,
    insert_score,
    fetch_recent_scores,
    insert_adaptation_log,
)


@pytest.mark.asyncio
async def test_database_in_memory_lifecycle():
    await init_db(":memory:")
    assert is_db_available() is True

    # User creation
    user = await get_or_create_user_on_score(None, "user_test_1")
    assert user["user_id"] == "user_test_1"
    assert user["current_level"] == 1

    # Insert score
    await insert_score(None, "user_test_1", "memory", 88, 1, extra={"accuracy": 92.5})
    scores = await fetch_recent_scores(None, "user_test_1")
    assert scores == [88]

    # Update adaptive state
    await update_user_adaptive(None, "user_test_1", 2, "improving", "Great job!", "too_easy")
    user_updated = await get_user(None, "user_test_1")
    assert user_updated is not None
    assert user_updated["current_level"] == 2
    assert user_updated["trend"] == "improving"

    # Insert log
    await insert_adaptation_log(
        None,
        user_id="user_test_1",
        trend="improving",
        challenge_state="too_easy",
        decision="increase",
        recommended_level=2,
        confidence=0.85,
        analysis="Great progress!",
        decision_source="llm",
        current_level=1,
        average_score=88.0,
        latest_score=88,
    )

    await close_db()
    assert is_db_available() is False
