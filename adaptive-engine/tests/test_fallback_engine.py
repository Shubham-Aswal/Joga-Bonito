import pytest
from app.services.fallback_engine import fallback_decision


def test_fallback_too_easy_increases_level():
    result = fallback_decision("too_easy", current_level=3)
    assert result["recommended_level"] == 4
    assert result["decision"] == "increase"
    assert result["confidence"] > 0
    assert len(result["analysis"]) > 10


def test_fallback_too_easy_at_level_10_maintains():
    result = fallback_decision("too_easy", current_level=10)
    assert result["recommended_level"] == 10
    assert result["decision"] == "maintain"


def test_fallback_too_hard_decreases_level():
    result = fallback_decision("too_hard", current_level=5)
    assert result["recommended_level"] == 4
    assert result["decision"] == "decrease"


def test_fallback_too_hard_at_level_1_maintains():
    result = fallback_decision("too_hard", current_level=1)
    assert result["recommended_level"] == 1
    assert result["decision"] == "maintain"


def test_fallback_optimal_maintains():
    result = fallback_decision("optimal", current_level=4)
    assert result["recommended_level"] == 4
    assert result["decision"] == "maintain"


def test_fallback_new_user():
    result = fallback_decision("optimal", current_level=1, trend="new_user")
    assert result["recommended_level"] == 1
    assert result["decision"] == "maintain"


def test_fallback_bounds_clamping():
    result_high = fallback_decision("too_easy", current_level=12)
    assert result_high["recommended_level"] == 10

    result_low = fallback_decision("too_hard", current_level=-2)
    assert result_low["recommended_level"] == 1
