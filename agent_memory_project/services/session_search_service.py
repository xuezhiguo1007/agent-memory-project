from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from agent_memory_project import PROJECT_ROOT


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(slots=True)
class SessionEvent:
    event_id: int
    session_id: str
    role: str
    content: str
    created_at: str
    score: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at,
            "score": self.score,
        }


class SessionSearchService:
    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or PROJECT_ROOT
        self.hermes_root = self.project_root / "generated_memories" / "hermes"
        self.db_path = self.hermes_root / "state.db"
        self._ensure_layout()

    def append_event(self, session_id: str, role: str, content: str) -> SessionEvent:
        normalized_content = " ".join(content.split())
        if not normalized_content:
            raise ValueError("Session event content must not be empty.")

        normalized_session = session_id.strip()
        normalized_role = role.strip() or "user"
        if not normalized_session:
            raise ValueError("session_id must not be empty.")

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO session_events (session_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (normalized_session, normalized_role, normalized_content, utc_now()),
            )
            event_id = int(cursor.lastrowid)
            row = conn.execute(
                """
                SELECT event_id, session_id, role, content, created_at
                FROM session_events
                WHERE event_id = ?
                """,
                (event_id,),
            ).fetchone()
        return self._row_to_event(row)

    def list_events(self, session_id: str, limit: int = 50) -> list[SessionEvent]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT event_id, session_id, role, content, created_at
                FROM session_events
                WHERE session_id = ?
                ORDER BY event_id DESC
                LIMIT ?
                """,
                (session_id.strip(), limit),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def search_events(
        self, session_id: str, query: str, limit: int = 5
    ) -> tuple[list[SessionEvent], str]:
        normalized_session = session_id.strip()
        normalized_query = " ".join(query.split())
        if not normalized_session:
            raise ValueError("session_id must not be empty.")
        if not normalized_query:
            raise ValueError("Query must not be empty.")

        fts_query = " OR ".join(token for token in normalized_query.split() if token)
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT e.event_id, e.session_id, e.role, e.content, e.created_at, bm25(session_events_fts) AS score
                FROM session_events_fts
                JOIN session_events AS e ON e.event_id = session_events_fts.rowid
                WHERE session_events_fts.session_id = ? AND session_events_fts.content MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (normalized_session, fts_query, limit),
            ).fetchall()

        events = [self._row_to_event(row) for row in rows]
        summary = self._summarize(events)
        return events, summary

    def list_sessions(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT session_id, MAX(event_id) AS last_event_id
                FROM session_events
                GROUP BY session_id
                ORDER BY last_event_id DESC
                """
            ).fetchall()
        return [str(row["session_id"]) for row in rows]

    def _summarize(self, events: list[SessionEvent]) -> str:
        if not events:
            return ""
        snippets = [f"[{event.role}] {event.content}" for event in events[:3]]
        return " | ".join(snippets)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_layout(self) -> None:
        self.hermes_root.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS session_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS session_events_fts
                USING fts5(
                    session_id UNINDEXED,
                    content,
                    content='session_events',
                    content_rowid='event_id'
                )
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS session_events_ai
                AFTER INSERT ON session_events
                BEGIN
                    INSERT INTO session_events_fts(rowid, session_id, content)
                    VALUES (new.event_id, new.session_id, new.content);
                END
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS session_events_ad
                AFTER DELETE ON session_events
                BEGIN
                    INSERT INTO session_events_fts(session_events_fts, rowid, session_id, content)
                    VALUES ('delete', old.event_id, old.session_id, old.content);
                END
                """
            )
            conn.execute(
                """
                CREATE TRIGGER IF NOT EXISTS session_events_au
                AFTER UPDATE ON session_events
                BEGIN
                    INSERT INTO session_events_fts(session_events_fts, rowid, session_id, content)
                    VALUES ('delete', old.event_id, old.session_id, old.content);
                    INSERT INTO session_events_fts(rowid, session_id, content)
                    VALUES (new.event_id, new.session_id, new.content);
                END
                """
            )

    def _row_to_event(self, row: sqlite3.Row) -> SessionEvent:
        score = row["score"] if "score" in row.keys() else None
        normalized_score = round(-float(score), 4) if score is not None else None
        return SessionEvent(
            event_id=int(row["event_id"]),
            session_id=str(row["session_id"]),
            role=str(row["role"]),
            content=str(row["content"]),
            created_at=str(row["created_at"]),
            score=normalized_score,
        )
