import logging
import sqlite3
from pathlib import Path
from typing import Optional

import aiosqlite

from app.core.config import settings

logger = logging.getLogger(__name__)

_db_path: Optional[str] = None
_init_done: bool = False
_memory_holder: Optional[aiosqlite.Connection] = None

CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    current_level INTEGER NOT NULL DEFAULT 1 CHECK(current_level BETWEEN 1 AND 10),
    trend TEXT DEFAULT 'new_user',
    last_analysis TEXT,
    challenge_state TEXT DEFAULT 'optimal',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

CREATE_SCORES = """
CREATE TABLE IF NOT EXISTS game_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    game_type TEXT NOT NULL,
    score INTEGER NOT NULL CHECK(score BETWEEN 0 AND 100),
    level_played INTEGER NOT NULL CHECK(level_played BETWEEN 1 AND 10),
    accuracy REAL,
    response_time REAL,
    mistakes INTEGER,
    hints_used INTEGER,
    session_duration REAL,
    cognitive_domain TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
"""

CREATE_LOGS = """
CREATE TABLE IF NOT EXISTS adaptation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    trend TEXT,
    challenge_state TEXT,
    decision TEXT,
    recommended_level INTEGER,
    current_level INTEGER,
    average_score REAL,
    latest_score INTEGER,
    confidence REAL,
    analysis TEXT,
    decision_source TEXT,
    created_at TEXT NOT NULL
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_scores_user_time ON game_scores(user_id, timestamp DESC);",
    "CREATE INDEX IF NOT EXISTS idx_scores_user ON game_scores(user_id);",
    "CREATE INDEX IF NOT EXISTS idx_logs_user ON adaptation_logs(user_id, created_at DESC);",
]


def get_db_path() -> str:
    global _db_path
    if _db_path is not None:
        return _db_path
    return settings.get_sqlite_path()


def _is_memory_path(path: str) -> bool:
    return path == ":memory:" or "mode=memory" in path


def _normalize_connect_path(path: str) -> tuple[str, bool]:
    if path == ":memory:":
        return "file:adaptive_mem?mode=memory&cache=shared", True
    if path.startswith("file:"):
        return path, True
    return path, False


async def init_db(db_path: Optional[str] = None) -> None:
    global _init_done, _db_path, _memory_holder
    path = db_path or get_db_path()
    _db_path = path

    target_path, is_uri = _normalize_connect_path(path)

    if not _is_memory_path(path) and not is_uri:
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    if _is_memory_path(path):
        if _memory_holder is not None:
            try:
                await _memory_holder.close()
            except Exception:
                pass
        _memory_holder = await aiosqlite.connect(target_path, uri=is_uri)
        db = _memory_holder
    else:
        db = await aiosqlite.connect(target_path, uri=is_uri)

    try:
        if not _is_memory_path(path):
            await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        await db.execute(CREATE_USERS)
        await db.execute(CREATE_SCORES)
        await db.execute(CREATE_LOGS)
        for idx_sql in CREATE_INDEXES:
            await db.execute(idx_sql)
        await db.commit()
    finally:
        if not _is_memory_path(path):
            await db.close()

    _init_done = True
    logger.info(f"SQLite ready at {path}")


async def close_db() -> None:
    global _init_done, _memory_holder, _db_path
    if _memory_holder is not None:
        try:
            await _memory_holder.close()
        except Exception as e:
            logger.warning(f"Error closing in-memory DB: {e}")
        _memory_holder = None
    _init_done = False


def is_db_available() -> bool:
    return _init_done


from contextlib import asynccontextmanager


@asynccontextmanager
async def get_connection():
    path = get_db_path()
    target_path, is_uri = _normalize_connect_path(path)
    conn = await aiosqlite.connect(target_path, uri=is_uri)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys=ON;")
    await conn.execute("PRAGMA busy_timeout = 5000;")
    try:
        yield conn
    finally:
        await conn.close()
