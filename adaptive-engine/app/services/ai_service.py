"""
Groq LLM service — supportive coach, structured JSON, strict validation.
Never makes medical claims. Always bounded by allowed_range.
"""
import json
import logging
from typing import Any

from app.core.config import settings
from app.schemas.adaptive import LLMResponse

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a supportive cognitive gaming coach for elderly users.
You help decide the next difficulty level for brain-training games.

CRITICAL RULES:
- You are NOT a medical professional. Never diagnose, never mention dementia, cognitive decline, or medical conditions.
- Never mention algorithms, models, or internal logic.
- Be warm, simple, encouraging, concise (1-2 sentences). Use plain language an elderly user understands.
- Never shame or criticize.
- You must return ONLY valid JSON with exactly these fields: recommended_level (int), decision (increase|maintain|decrease), confidence (0.0-1.0), analysis (string).
- The analysis must match the decision tone:
  - increase: celebrate progress, suggest slightly harder
  - decrease: gently acknowledge difficulty, suggest slightly easier
  - maintain: encourage steady practice at same level
- recommended_level MUST be within the allowed_range provided. Never choose outside it.
"""

class LLMError(Exception):
    """Base LLM error — triggers fallback."""
    pass

class LLMInvalidError(LLMError):
    """LLM returned invalid JSON or out-of-range value."""
    pass


def build_user_prompt(
    current_level: int,
    allowed_range: list[int],
    recent_scores: list[int],
    average: float,
    trend: str,
    challenge_state: str,
) -> str:
    return f"""Current difficulty level: {current_level}
Allowed next levels (you MUST choose one of these): {allowed_range}
Recent scores (oldest to newest, 0-100): {recent_scores}
Average recent score: {average}
Trend: {trend}
Challenge assessment: {challenge_state}

Based on this, decide whether to increase, maintain, or decrease difficulty by at most 1 level.
Return JSON only:
{{"recommended_level": <int from allowed_range>, "decision": "increase"|"maintain"|"decrease", "confidence": <0.0-1.0>, "analysis": "<warm 1-2 sentence message>"}}
"""


def _map_exception_to_msg(e: Exception) -> str:
    return f"{type(e).__name__}: {str(e)[:300]}"


async def call_groq(
    current_level: int,
    allowed_range: list[int],
    recent_scores: list[int],
    average: float,
    trend: str,
    challenge_state: str,
) -> LLMResponse:
    """
    Call Groq and return validated LLMResponse. Raises LLMError / LLMInvalidError on failure.
    """
    if not settings.is_groq_configured:
        raise LLMError("Groq not configured (missing GROQ_API_KEY)")

    # Lazy import so tests without groq installed still run
    try:
        from groq import Groq
    except ImportError as e:
        raise LLMError(f"groq package not installed: {e}")

    user_prompt = build_user_prompt(
        current_level=current_level,
        allowed_range=allowed_range,
        recent_scores=recent_scores,
        average=average,
        trend=trend,
        challenge_state=challenge_state,
    )

    try:
        # Use AsyncGroq to avoid blocking event loop; fallback to sync Groq if async not available
        try:
            from groq import AsyncGroq

            client = AsyncGroq(
                api_key=settings.GROQ_API_KEY,
                timeout=settings.GROQ_TIMEOUT,
                max_retries=settings.GROQ_MAX_RETRIES,
            )
            completion = await client.chat.completions.create(
                model=settings.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=500,
                response_format={"type": "json_object"},
            )
            content = completion.choices[0].message.content
        except ImportError:
            # Fallback to sync client run in thread
            import asyncio
            from groq import Groq

            def _sync_call():
                sync_client = Groq(
                    api_key=settings.GROQ_API_KEY,
                    timeout=settings.GROQ_TIMEOUT,
                    max_retries=settings.GROQ_MAX_RETRIES,
                )
                return sync_client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                    max_tokens=500,
                    response_format={"type": "json_object"},
                )

            completion = await asyncio.to_thread(_sync_call)
            content = completion.choices[0].message.content

        if not content:
            raise LLMInvalidError("Empty LLM response")

        # Parse JSON - handle case where model returns extra text before/after JSON
        try:
            parsed: Any = json.loads(content)
        except json.JSONDecodeError as je:
            # Try to extract JSON substring if model added extra text
            try:
                start = content.index("{")
                end = content.rindex("}") + 1
                parsed = json.loads(content[start:end])
            except Exception:
                raise LLMInvalidError(f"Invalid JSON from LLM: {content[:500]} — {je}")

        # Validate via Pydantic
        try:
            llm_resp = LLMResponse(**parsed)
        except Exception as ve:
            raise LLMInvalidError(f"LLM response validation failed: {ve} — raw: {parsed}")

        # Extra validation: recommended_level must be in allowed_range
        if llm_resp.recommended_level not in allowed_range:
            raise LLMInvalidError(
                f"LLM recommended_level {llm_resp.recommended_level} not in allowed_range {allowed_range}"
            )

        expected_decision = _decision_from_delta(current_level, llm_resp.recommended_level)
        if llm_resp.decision != expected_decision:
            # Boundary handling: if capped at 10 or floor at 1, normalize to maintain
            if (current_level >= 10 and llm_resp.recommended_level >= 10) or (current_level <= 1 and llm_resp.recommended_level <= 1):
                llm_resp.decision = "maintain"
            else:
                raise LLMInvalidError(
                    f"LLM decision {llm_resp.decision} mismatches level delta "
                    f"(current {current_level} -> recommended {llm_resp.recommended_level}, expected {expected_decision})"
                )

        # Clamp analysis length if needed (Pydantic already checks, but be safe)
        if not (10 <= len(llm_resp.analysis) <= 500):
            raise LLMInvalidError(f"Analysis length invalid: {len(llm_resp.analysis)}")

        return llm_resp

    except LLMInvalidError:
        raise
    except LLMError:
        raise
    except Exception as e:
        # Any other Groq/network error
        logger.warning(f"Groq call failed: {_map_exception_to_msg(e)}")
        raise LLMError(_map_exception_to_msg(e)) from e


def _decision_from_delta(current: int, recommended: int) -> str:
    if recommended > current:
        return "increase"
    if recommended < current:
        return "decrease"
    return "maintain"
