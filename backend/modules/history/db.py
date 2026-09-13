"""
SQLite-backed persistent chat history and projects.

Persisted at backend/data/chat_history.db (not localStorage) so history is
shared across every screen that talks to this backend, including a second
laptop reaching it over LAN.

Projects are an optional grouping layer: a session or document with no
project_id is "unscoped" and behaves exactly as it did before projects
existed (searches/lists across everything).
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# backend/modules/history/db.py -> parents[2] == backend/
DB_PATH = Path(__file__).resolve().parents[2] / "data" / "chat_history.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


@contextmanager
def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _column_exists(conn, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT,
                project_id TEXT,
                created_at TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                sources_json TEXT,
                created_at TIMESTAMP
            )
            """
        )
        # Migration for databases created before projects existed.
        if not _column_exists(conn, "sessions", "project_id"):
            conn.execute("ALTER TABLE sessions ADD COLUMN project_id TEXT")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_project(project_id: str, name: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO projects (id, name, created_at) VALUES (?, ?, ?)",
            (project_id, name, _now()),
        )


def list_projects() -> list:
    """Return [{"id", "name", "created_at"}, ...] newest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, created_at FROM projects ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]


def project_exists(project_id: str) -> bool:
    with _connect() as conn:
        row = conn.execute("SELECT 1 FROM projects WHERE id = ?", (project_id,)).fetchone()
        return row is not None


def create_session(session_id: str, title: str, project_id: Optional[str] = None) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO sessions (id, title, project_id, created_at) VALUES (?, ?, ?, ?)",
            (session_id, title, project_id, _now()),
        )


def session_exists(session_id: str) -> bool:
    with _connect() as conn:
        row = conn.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,)).fetchone()
        return row is not None


def add_message(session_id: str, role: str, content: str, sources: Optional[list] = None) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO messages (session_id, role, content, sources_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, role, content, json.dumps(sources) if sources is not None else None, _now()),
        )


def list_sessions(project_id: Optional[str] = None) -> list:
    """
    Return [{"id", "title", "project_id", "created_at"}, ...] newest first.

    With no project_id, returns every session (unscoped and project-scoped
    alike) — this is the "All documents" view.
    """
    with _connect() as conn:
        if project_id:
            rows = conn.execute(
                """
                SELECT id, title, project_id, created_at FROM sessions
                WHERE project_id = ? ORDER BY created_at DESC
                """,
                (project_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, title, project_id, created_at FROM sessions ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]


def get_messages(session_id: str) -> list:
    """Return the full ordered message list for one session."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, role, content, sources_json, created_at FROM messages
            WHERE session_id = ? ORDER BY id ASC
            """,
            (session_id,),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "role": row["role"],
                "content": row["content"],
                "sources": json.loads(row["sources_json"]) if row["sources_json"] else [],
                "created_at": row["created_at"],
            }
            for row in rows
        ]


def delete_session(session_id: str) -> bool:
    """Delete a session and its messages. Returns True if it existed."""
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        return cursor.rowcount > 0


init_db()
