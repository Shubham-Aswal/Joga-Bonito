"""
Fallback engine — deterministic, no LLM, never fails.
Always respects 1..10 and max ±1.
"""
import random


_FALLBACK_MESSAGES = {
    "too_easy_increase": [
        "You've been doing really well, so let's make the next activity a little more challenging.",
        "Great progress! Let's try a slightly harder level next.",
        "You handled that well — time for a small step up in difficulty.",
    ],
    "too_hard_decrease": [
        "This activity seems to have been a little harder. Let's take a small step back and try an easier level.",
        "That one was a bit tricky — let's make the next one a little easier to build confidence.",
        "No worries, let's ease the difficulty slightly for the next activity.",
    ],
    "optimal_maintain": [
        "You're doing steadily at this level. Let's stay here for a while and build confidence.",
        "Nice steady performance. Let's keep the same level and keep practicing.",
        "You're holding well at this level — let's continue here for now.",
    ],
    "new_user": [
        "We'll start with an easier level and gradually adjust the challenge based on your performance.",
        "We will start with an easier level and gradually adjust the challenge as we learn how you perform.",
        "Starting at the easiest level — we'll adapt as we see how you do.",
    ],
}


def _pick(key: str) -> str:
    return random.choice(_FALLBACK_MESSAGES[key])


def fallback_decision(
    challenge_state: str,
    current_level: int,
    trend: str = "stable",
) -> dict:
    """
    Returns dict with recommended_level, decision, confidence, analysis, decision_source=fallback
    """
    curr = max(1, min(10, int(current_level)))

    if challenge_state == "too_easy":
        recommended = min(10, curr + 1)
        decision = "increase"
        # If already at 10, stay
        if curr >= 10:
            recommended = 10
            decision = "maintain"
            analysis = _pick("optimal_maintain")
            confidence = 0.75
        else:
            analysis = _pick("too_easy_increase")
            confidence = 0.82
    elif challenge_state == "too_hard":
        recommended = max(1, curr - 1)
        decision = "decrease"
        if curr <= 1:
            recommended = 1
            decision = "maintain"
            # Softer message at floor
            analysis = "Let's stay at this level and keep practicing at a comfortable pace."
            confidence = 0.75
        else:
            analysis = _pick("too_hard_decrease")
            confidence = 0.82
    else:  # optimal or new_user
        if trend == "new_user":
            recommended = curr  # stays 1 for new user
            decision = "maintain"
            analysis = _pick("new_user")
            confidence = 0.70
        else:
            recommended = curr
            decision = "maintain"
            analysis = _pick("optimal_maintain")
            confidence = 0.78

    # Safety clamp (should already be valid)
    recommended = max(1, min(10, recommended))
    # Ensure ±1
    if abs(recommended - curr) > 1:
        if recommended > curr:
            recommended = min(10, curr + 1)
        else:
            recommended = max(1, curr - 1)

    return {
        "recommended_level": recommended,
        "decision": decision,
        "confidence": confidence,
        "analysis": analysis,
    }
