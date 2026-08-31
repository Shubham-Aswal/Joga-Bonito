"""
Performance analyzer — pure Python, no LLM, fully testable.

Analyzes recent scores to determine trend and challenge_state.
Extensible: accepts **extra_metrics without breaking.
"""
from typing import Any


# ── Tunable thresholds (documented for SIH viva) ──
TREND_DELTA_THRESHOLD = 8          # overall delta newest-oldest to be improving/declining
TREND_HALF_AVG_THRESHOLD = 6       # second half avg - first half avg
CHALLENGE_TOO_EASY_AVG = 78
CHALLENGE_TOO_EASY_LATEST = 75
CHALLENGE_TOO_HARD_AVG = 50
CHALLENGE_TOO_HARD_LATEST = 45
CHALLENGE_TOO_HARD_DECLINING_AVG = 60


def analyze_trend(scores: list[int]) -> str:
    """
    Returns: improving | stable | declining | new_user
    - new_user: no scores
    - improving: overall up-trend
    - declining: overall down-trend
    - stable: otherwise
    """
    if not scores:
        return "new_user"
    if len(scores) < 2:
        return "stable"

    delta = scores[-1] - scores[0]

    # Compare first half vs second half average
    mid = len(scores) // 2
    first_half = scores[:mid] if mid > 0 else scores[:1]
    second_half = scores[mid:] if mid < len(scores) else scores[-1:]

    avg_first = sum(first_half) / len(first_half) if first_half else scores[0]
    avg_second = sum(second_half) / len(second_half) if second_half else scores[-1]
    half_diff = avg_second - avg_first

    is_improving = (delta >= TREND_DELTA_THRESHOLD or half_diff >= TREND_HALF_AVG_THRESHOLD) and delta >= 0 and half_diff >= 0
    is_declining = (delta <= -TREND_DELTA_THRESHOLD or half_diff <= -TREND_HALF_AVG_THRESHOLD) and delta <= 0 and half_diff <= 0

    if is_improving:
        return "improving"
    if is_declining:
        return "declining"
    return "stable"


def classify_challenge(
    average: float,
    latest: int,
    trend: str,
) -> str:
    """
    Returns: too_easy | optimal | too_hard

    Refined for SIH demo scenarios:
    - Strong improving (65,72,80,88) avg ~76 should be too_easy -> increase
    - Declining (85,75,60,48) avg ~67 with latest 48 should be too_hard -> decrease
    - Stable (72,74,73,75) avg ~73.5 should be optimal -> maintain
    """
    # Very low absolute -> too_hard regardless of trend
    if average <= CHALLENGE_TOO_HARD_AVG or latest <= CHALLENGE_TOO_HARD_LATEST:
        return "too_hard"

    # High absolute -> too_easy
    if average >= CHALLENGE_TOO_EASY_AVG and latest >= CHALLENGE_TOO_EASY_LATEST and trend != "declining":
        return "too_easy"

    # Improving with decent average -> too_easy (captures 65,72,80,88)
    if trend == "improving" and average >= 70 and latest >= CHALLENGE_TOO_EASY_LATEST:
        return "too_easy"

    # Declining -> too_hard if latest low or average moderate-low
    if trend == "declining":
        if latest < 60 or average < 65:
            return "too_hard"
        if latest <= 62 and average <= 70:
            return "too_hard"
        if average < CHALLENGE_TOO_HARD_DECLINING_AVG:
            return "too_hard"

    return "optimal"


def analyze_performance(
    scores: list[int],
    current_level: int,
    **extra_metrics: Any,
) -> dict[str, Any]:
    """
    Main analyzer entry. Future-proof: accepts accuracy, response_time, etc. via **extra_metrics
    (currently unused but reserved for extension without breaking).
    """
    if not scores:
        return {
            "average": 0.0,
            "latest": 0,
            "trend": "new_user",
            "challenge_state": "optimal",
            "consistency": "unknown",
            "current_level": max(1, min(10, current_level)),
        }

    average = sum(scores) / len(scores)
    latest = scores[-1]
    trend = analyze_trend(scores)
    challenge_state = classify_challenge(average, latest, trend)

    # Consistency: max-min range
    score_range = max(scores) - min(scores)
    if score_range <= 5:
        consistency = "very_stable"
    elif score_range <= 15:
        consistency = "stable"
    else:
        consistency = "variable"

    # Extra metrics hook (reserved): if accuracy/response_time provided, could refine challenge_state
    # For MVP we ignore but keep the signature stable.
    _ = extra_metrics  # intentionally unused, prevents lint warnings

    return {
        "average": round(average, 2),
        "latest": latest,
        "trend": trend,
        "challenge_state": challenge_state,
        "consistency": consistency,
        "current_level": max(1, min(10, current_level)),
    }
