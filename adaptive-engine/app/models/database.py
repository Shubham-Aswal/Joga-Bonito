"""
SQLite database helpers for Adaptive Engine.

Tables:
  users(user_id PK, current_level, trend, last_analysis, challenge_state, created_at, updated_at)
  game_scores(id, user_id, game_type, score, level_played, accuracy, response_time, mistakes, hints_used, session_duration, cognitive_domain, timestamp)
  adaptation_logs(id, user_id, trend, challenge_state, decision, recommended_level, current_level, average_score, latest_score, confidence, analysis, decision_source, created_at)
"""
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.core.database import get_connection

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Users ──

async def get_user(db, user_id: str) -> Optional[dict[str, Any]]:
    try:
        async with get_connection() as conn:
            async with conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
                row = await cur.fetchone()
                if row is None:
                    return None
                return dict(row)
    except Exception as e:
        logger.warning(f"get_user failed for {user_id}: {e}")
        return None


async def get_or_create_user_on_score(db, user_id: str) -> dict[str, Any]:
    try:
        async with get_connection() as conn:
            async with conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
                row = await cur.fetchone()
                if row is not None:
                    return dict(row)
            # Create new user record
            now = _now_iso()
            await conn.execute(
                """
                INSERT INTO users (user_id, current_level, trend, last_analysis, challenge_state, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO NOTHING
                """,
                (user_id, 1, "new_user", "We'll start with an easier level and gradually adjust the challenge based on your performance.", "optimal", now, now),
            )
            await conn.commit()
            async with conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cur:
                row = await cur.fetchone()
                return dict(row) if row else {"user_id": user_id, "current_level": 1, "trend": "new_user"}
    except Exception as e:
        logger.warning(f"get_or_create_user_on_score failed for {user_id}: {e}")
        return {"user_id": user_id, "current_level": 1, "trend": "new_user"}


def extract_current_level(user_doc: Optional[dict[str, Any]]) -> int:
    if user_doc is None:
        return 1
    try:
        lvl = int(user_doc.get("current_level", 1))
        return max(1, min(10, lvl))
    except Exception:
        return 1


def extract_last_analysis(user_doc: Optional[dict[str, Any]]) -> Optional[str]:
    if user_doc is None:
        return None
    try:
        return user_doc.get("last_analysis")
    except Exception:
        return None


async def update_user_adaptive(
    db,
    user_id: str,
    recommended_level: int,
    trend: str,
    analysis: str,
    challenge_state: str,
) -> None:
    try:
        async with get_connection() as conn:
            now = _now_iso()
            await conn.execute(
                """
                INSERT INTO users (user_id, current_level, trend, last_analysis, challenge_state, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    current_level = excluded.current_level,
                    trend = excluded.trend,
                    last_analysis = excluded.last_analysis,
                    challenge_state = excluded.challenge_state,
                    updated_at = excluded.updated_at
                """,
                (user_id, max(1, min(10, recommended_level)), trend, analysis, challenge_state, now, now),
            )
            await conn.commit()
    except Exception as e:
        logger.warning(f"update_user_adaptive failed for {user_id}: {e}")


# ── Scores ──

async def insert_score(
    db,
    user_id: str,
    game_type: str,
    score: int,
    level_played: int,
    extra: Optional[dict[str, Any]] = None,
) -> None:
    try:
        async with get_connection() as conn:
            ts = _now_iso()
            accuracy = extra.get("accuracy") if extra else None
            response_time = extra.get("response_time") if extra else None
            mistakes = extra.get("mistakes") if extra else None
            hints_used = extra.get("hints_used") if extra else None
            session_duration = extra.get("session_duration") if extra else None
            cognitive_domain = extra.get("cognitive_domain") if extra else None
            await conn.execute(
                "INSERT INTO game_scores (user_id, game_type, score, level_played, accuracy, response_time, mistakes, hints_used, session_duration, cognitive_domain, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, game_type, int(score), int(level_played), accuracy, response_time, mistakes, hints_used, session_duration, cognitive_domain, ts),
            )
            await conn.commit()
    except Exception as e:
        logger.warning(f"insert_score failed for {user_id}: {e}")


async def fetch_recent_scores(db, user_id: str, limit: int = 5) -> list[int]:
    try:
        async with get_connection() as conn:
            async with conn.execute(
                "SELECT score FROM game_scores WHERE user_id = ? ORDER BY timestamp DESC, id DESC LIMIT ?", (user_id, limit)
            ) as cur:
                rows = await cur.fetchall()
                return [int(r["score"]) for r in reversed(rows)]
    except Exception as e:
        logger.warning(f"fetch_recent_scores failed for {user_id}: {e}")
        return []


async def insert_adaptation_log(
    db,
    user_id: str,
    trend: str,
    challenge_state: str,
    decision: str,
    recommended_level: int,
    confidence: float,
    analysis: str,
    decision_source: str,
    current_level: int,
    average_score: float,
    latest_score: int,
) -> None:
    try:
        async with get_connection() as conn:
            await conn.execute(
                "INSERT INTO adaptation_logs (user_id, trend, challenge_state, decision, recommended_level, current_level, average_score, latest_score, confidence, analysis, decision_source, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, trend, challenge_state, decision, recommended_level, current_level, average_score, latest_score, confidence, analysis, decision_source, _now_iso()),
            )
            await conn.commit()
    except Exception as e:
        logger.warning(f"insert_adaptation_log failed for {user_id}: {e}")
