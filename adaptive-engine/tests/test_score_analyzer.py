import pytest
from app.services.score_analyzer import (
    analyze_trend,
    classify_challenge,
    analyze_performance,
)


def test_analyze_trend_empty():
    assert analyze_trend([]) == "new_user"


def test_analyze_trend_single_score():
    assert analyze_trend([75]) == "stable"


def test_analyze_trend_improving():
    scores = [65, 72, 80, 88]
    assert analyze_trend(scores) == "improving"


def test_analyze_trend_declining():
    scores = [85, 75, 60, 48]
    assert analyze_trend(scores) == "declining"


def test_analyze_trend_stable():
    scores = [70, 72, 71, 73]
    assert analyze_trend(scores) == "stable"


def test_analyze_trend_conflicting_signals():
    # Delta is positive (+10), but second half average drops heavily (-20)
    scores = [50, 90, 40, 60]
    assert analyze_trend(scores) == "stable"


def test_classify_challenge_too_hard_low_average():
    assert classify_challenge(average=45.0, latest=50, trend="declining") == "too_hard"


def test_classify_challenge_too_hard_low_latest():
    assert classify_challenge(average=65.0, latest=40, trend="stable") == "too_hard"


def test_classify_challenge_too_easy_high_score():
    assert classify_challenge(average=82.0, latest=85, trend="stable") == "too_easy"


def test_classify_challenge_too_easy_improving():
    assert classify_challenge(average=74.0, latest=80, trend="improving") == "too_easy"


def test_classify_challenge_optimal():
    assert classify_challenge(average=72.0, latest=70, trend="stable") == "optimal"


def test_analyze_performance_full():
    scores = [70, 75, 80, 85]
    perf = analyze_performance(scores, current_level=3)
    assert perf["average"] == 77.5
    assert perf["latest"] == 85
    assert perf["trend"] == "improving"
    assert perf["challenge_state"] == "too_easy"
    assert perf["current_level"] == 3
    assert perf["consistency"] == "stable"


def test_analyze_performance_empty():
    perf = analyze_performance([], current_level=1)
    assert perf["average"] == 0.0
    assert perf["trend"] == "new_user"
    assert perf["challenge_state"] == "optimal"
    assert perf["current_level"] == 1
