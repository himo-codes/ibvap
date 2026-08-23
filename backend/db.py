"""SQLite storage for IBVAP events."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Any

from backend.config import get_settings

_DB_LOCK = threading.Lock()


def init_db(db_path: Path | None = None) -> None:
    """Create the SQLite database and events table if needed."""
    path = _resolve_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _DB_LOCK, sqlite3.connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                camera_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                object_type TEXT NOT NULL,
                track_id INTEGER NOT NULL,
                confidence REAL NOT NULL,
                evidence_path TEXT NOT NULL,
                ack_status TEXT NOT NULL DEFAULT 'pending'
            )
            """
        )
        _ensure_ack_status_column(connection)
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_camera_id ON events(camera_id)"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type)"
        )


def insert_event(event: dict[str, Any], db_path: Path | None = None) -> None:
    """Insert a structured event into SQLite."""
    path = _resolve_db_path(db_path)
    with _DB_LOCK, sqlite3.connect(path) as connection:
        connection.execute(
            """
            INSERT INTO events (
                event_id,
                camera_id,
                timestamp,
                event_type,
                object_type,
                track_id,
                confidence,
                evidence_path,
                ack_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["event_id"],
                event["camera_id"],
                event["timestamp"],
                event["event_type"],
                event["object_type"],
                event["track_id"],
                event["confidence"],
                event["evidence_path"],
                event.get("ack_status", "pending"),
            ),
        )


def list_events(
    camera_id: str | None = None,
    event_type: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    limit: int | None = None,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Return events newest first with optional filters."""
    query = "SELECT * FROM events"
    clauses: list[str] = []
    params: list[Any] = []

    if camera_id is not None:
        clauses.append("camera_id = ?")
        params.append(camera_id)
    if event_type is not None:
        clauses.append("event_type = ?")
        params.append(event_type)
    if start_time is not None:
        clauses.append("timestamp >= ?")
        params.append(start_time)
    if end_time is not None:
        clauses.append("timestamp <= ?")
        params.append(end_time)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY timestamp DESC"
    if limit is not None:
        query += " LIMIT ?"
        params.append(limit)

    return _fetch_all(query, params, db_path)


def get_event(event_id: str, db_path: Path | None = None) -> dict[str, Any] | None:
    """Return one event by ID, or None when not found."""
    rows = _fetch_all(
        "SELECT * FROM events WHERE event_id = ?",
        [event_id],
        db_path,
    )
    if not rows:
        return None
    return rows[0]


def update_event_ack(
    event_id: str,
    ack_status: str,
    db_path: Path | None = None,
) -> dict[str, Any] | None:
    """Update an event acknowledgement status and return the updated event."""
    path = _resolve_db_path(db_path)
    with _DB_LOCK, sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        cursor = connection.execute(
            "UPDATE events SET ack_status = ? WHERE event_id = ?",
            (ack_status, event_id),
        )
        if cursor.rowcount == 0:
            return None
        row = connection.execute(
            "SELECT * FROM events WHERE event_id = ?",
            (event_id,),
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def _ensure_ack_status_column(connection: sqlite3.Connection) -> None:
    """Add ack_status to existing Phase 4 databases."""
    columns = {
        row[1]
        for row in connection.execute("PRAGMA table_info(events)").fetchall()
    }
    if "ack_status" not in columns:
        connection.execute(
            "ALTER TABLE events ADD COLUMN ack_status TEXT NOT NULL DEFAULT 'pending'"
        )


def _fetch_all(
    query: str,
    params: list[Any],
    db_path: Path | None,
) -> list[dict[str, Any]]:
    """Run a SELECT query and return rows as dictionaries."""
    path = _resolve_db_path(db_path)
    with _DB_LOCK, sqlite3.connect(path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def _resolve_db_path(db_path: Path | None) -> Path:
    """Resolve a database path from argument or settings."""
    if db_path is not None:
        return db_path
    return get_settings().database_path
