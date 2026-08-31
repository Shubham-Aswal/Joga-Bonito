import pytest
from app.services.ai_service import (
    build_user_prompt,
    _decision_from_delta,
    call_groq,
    LLMError,
)
from app.schemas.adaptive import LLMResponse
from app.core.config import settings


def test_build_user_prompt():
    prompt = build_user_prompt(
        current_level=2,
        allowed_range=[1, 2, 3],
        recent_scores=[70, 75, 80],
        average=75.0,
        trend="improving",
        challenge_state="too_easy",
    )
    assert "Current difficulty level: 2" in prompt
    assert "[1, 2, 3]" in prompt
    assert "Average recent score: 75.0" in prompt


def test_decision_from_delta():
    assert _decision_from_delta(2, 3) == "increase"
    assert _decision_from_delta(2, 1) == "decrease"
    assert _decision_from_delta(2, 2) == "maintain"


@pytest.mark.asyncio
async def test_call_groq_without_api_key_raises_error():
    # With empty GROQ_API_KEY, should raise LLMError immediately
    original_key = settings.GROQ_API_KEY
    try:
        settings.GROQ_API_KEY = ""
        with pytest.raises(LLMError) as exc_info:
            await call_groq(
                current_level=1,
                allowed_range=[1, 2],
                recent_scores=[80],
                average=80.0,
                trend="stable",
                challenge_state="optimal",
            )
        assert "not configured" in str(exc_info.value).lower()
    finally:
        settings.GROQ_API_KEY = original_key
