"""
Orchestrator — wires Performance Analyzer → Groq → Validator → Fallback → DB update.
Hybrid philosophy: Python validates, LLM interprets, fallback guarantees availability.
"""
import logging
from typing import Any, Optional

from app.core.config import settings
from app.models.database import (
    extract_current_level,
    extract_last_analysis,
    fetch_recent_scores,
    get_or_create_user_on_score,
    get_user,
    insert_adaptation_log,
    insert_score,
    update_user_adaptive,
)
from app.schemas.adaptive import GetStateResponse, ScoreRequest, ScoreResponse
from app.services.ai_service import LLMError, LLMInvalidError, call_groq
from app.services.fallback_engine import fallback_decision
from app.services.score_analyzer import analyze_performance

logger = logging.getLogger(__name__)


def _allowed_range(current_level: int) -> list[int]:
    curr = max(1, min(10, int(current_level)))
    lo = max(1, curr - 1)
    hi = min(10, curr + 1)
    return list(range(lo, hi + 1))


async def get_user_state(db, user_id: str) -> GetStateResponse:
    """
    GET /api/v1/adaptive/{user_id}
    - If user not found → new_user response with Level 1, no DB write.
    - Else → fetch recent scores, analyze, return current adaptive state.
    """
    user_doc = await get_user(db, user_id)

    if user_doc is None:
        return GetStateResponse(
            user_id=user_id,
            current_level=1,
            recent_scores=[],
            average_score=0.0,
            trend="new_user",
            is_new_user=True,
            analysis="We'll start with an easier level and gradually adjust the challenge based on your performance.",
            last_updated=None,
        )

    current_level = extract_current_level(user_doc)
    recent = await fetch_recent_scores(db, user_id, limit=settings.RECENT_SCORES_LIMIT)

    if not recent:
        # User exists but no scores yet
        analysis = extract_last_analysis(user_doc) or "We'll start with an easier level and gradually adjust the challenge based on your performance."
        return GetStateResponse(
            user_id=user_id,
            current_level=current_level,
            recent_scores=[],
            average_score=0.0,
            trend="new_user",
            is_new_user=False,
            analysis=analysis,
            last_updated=user_doc.get("updated_at") or (user_doc.get("adaptive") or {}).get("updated_at"),
        )

    perf = analyze_performance(recent, current_level)
    analysis = extract_last_analysis(user_doc)
    if not analysis:
        # Generate a sensible default based on trend
        if perf["trend"] == "improving":
            analysis = "Your recent performance has been improving steadily."
        elif perf["trend"] == "declining":
            analysis = "Some recent activities have been more challenging."
        else:
            analysis = "You're doing steadily at this level."

    return GetStateResponse(
        user_id=user_id,
        current_level=current_level,
        recent_scores=recent,
        average_score=round(perf["average"], 2),
        trend=perf["trend"],  # type: ignore
        is_new_user=False,
        analysis=analysis,
        last_updated=user_doc.get("updated_at") or (user_doc.get("adaptive") or {}).get("updated_at"),
    )


async def process_score(db, req: ScoreRequest) -> ScoreResponse:
    """
    POST /api/v1/adaptive/score
    Full hybrid flow: store → analyze → LLM → validate → fallback → persist → return.
    """
    user_id = req.user_id.strip()
    # 1. Get or create user (ensures shared users doc exists, adaptive.current_level = 1 if new)
    user_doc = await get_or_create_user_on_score(db, user_id)
    current_level = req.level_played if req.level_played is not None else extract_current_level(user_doc)

    # 2. Store score (include extensible metrics if provided)
    extra = {k: getattr(req, k, None) for k in ("accuracy", "response_time", "mistakes", "hints_used", "session_duration", "cognitive_domain")}
    extra = {k: v for k, v in extra.items() if v is not None}
    await insert_score(db, user_id, req.game_type, req.score, req.level_played, extra=extra)

    # 3. Fetch recent history (includes the just-inserted score if DB available)
    recent = await fetch_recent_scores(db, user_id, limit=settings.RECENT_SCORES_LIMIT)
    # If DB unavailable, synthesize single-score history so analysis still works (fallback path)
    if not recent:
        recent = [req.score]

    # 4. Analyze
    perf = analyze_performance(recent, current_level, **extra)
    trend: str = perf["trend"]
    challenge_state: str = perf["challenge_state"]
    average: float = perf["average"]
    latest: int = perf["latest"]

    allowed = _allowed_range(current_level)

    # 5. Try Groq → fallback on any failure
    decision_source: str = "llm"
    llm_recommended: Optional[int] = None
    llm_decision: Optional[str] = None
    llm_confidence: Optional[float] = None
    llm_analysis: Optional[str] = None

    try:
        llm_resp = await call_groq(
            current_level=current_level,
            allowed_range=allowed,
            recent_scores=recent,
            average=average,
            trend=trend,
            challenge_state=challenge_state,
        )
        llm_recommended = llm_resp.recommended_level
        llm_decision = llm_resp.decision
        llm_confidence = llm_resp.confidence
        llm_analysis = llm_resp.analysis
        decision_source = "llm"

    except LLMInvalidError as e:
        logger.warning(f"LLM invalid for {user_id}: {e} — using fallback")
        decision_source = "fallback_llm_invalid"
    except LLMError as e:
        msg = str(e)
        if "not configured" in msg.lower() or "missing" in msg.lower():
            decision_source = "fallback_no_groq"
            logger.info(f"Groq not configured, using fallback for {user_id}")
        else:
            decision_source = "fallback_llm_error"
            logger.warning(f"LLM error for {user_id}: {e} — using fallback")
    except Exception as e:
        logger.warning(f"Unexpected LLM error for {user_id}: {e} — using fallback")
        decision_source = "fallback_llm_error"

    # 6. Apply fallback if LLM didn't succeed
    if decision_source != "llm":
        fb = fallback_decision(challenge_state, current_level, trend)
        recommended_level = fb["recommended_level"]
        decision = fb["decision"]
        confidence = fb["confidence"]
        analysis = fb["analysis"]
    else:
        assert llm_recommended is not None
        recommended_level = llm_recommended  # type: ignore
        decision = llm_decision  # type: ignore
        confidence = llm_confidence  # type: ignore
        analysis = llm_analysis  # type: ignore

    # 7. Persist updated adaptive state (shared DB: $set adaptive.* only)
    await update_user_adaptive(db, user_id, recommended_level, trend, analysis, challenge_state)
    await insert_adaptation_log(
        db,
        user_id=user_id,
        trend=trend,
        challenge_state=challenge_state,
        decision=decision,
        recommended_level=recommended_level,
        confidence=confidence,
        analysis=analysis,
        decision_source=decision_source,
        current_level=current_level,
        average_score=average,
        latest_score=latest,
    )

    return ScoreResponse(
        user_id=user_id,
        current_level=current_level,
        recommended_level=recommended_level,
        decision=decision,  # type: ignore
        challenge_state=challenge_state,  # type: ignore
        trend=trend,  # type: ignore
        latest_score=latest,
        average_recent_score=round(average, 2),
        confidence=round(float(confidence), 2),
        analysis=analysis,
        decision_source=decision_source,  # type: ignore
    )
