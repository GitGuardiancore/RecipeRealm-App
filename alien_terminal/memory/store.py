"""MemoryStore: persistent storage for the alien's observations.

The memory is the agent's continuity. Without it, every signal
interpretation starts from scratch and the alien never develops running
theories, callbacks to earlier observations, or evolving opinions about
human behavior.

Schema:
  observations(id, signal_source, signal_headline, category, confidence,
               field_note, posted, created_at)

The `posted` flag tracks whether the observation has been broadcast.
The publisher marks observations as posted after successful delivery.
The dashboard queries both posted and unposted observations.

Design choice: SQLite for the reference implementation, same as the live
deployment. The agent runs on a single machine with a cron schedule.
There is no concurrent-write pressure. SQLite is the right tool.
"""
from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import uuid4

log = logging.getLogger(__name__)


SCHEMA = """
CREATE TABLE IF NOT EXISTS observations (
    id TEXT PRIMARY KEY,
    signal_source TEXT NOT NULL DEFAULT '',
    signal_headline TEXT NOT NULL DEFAULT '',
    category TEXT NOT NULL DEFAULT 'pattern-seeking',
    confidence REAL NOT NULL DEFAULT 0.5,
    field_note TEXT NOT NULL DEFAULT '',
    posted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS observations_created_idx
    ON observations(created_at DESC);

CREATE INDEX IF NOT EXISTS observations_category_idx
    ON observations(category);

CREATE INDEX IF NOT EXISTS observations_posted_idx
    ON observations(posted, created_at DESC);
"""


@dataclass
class Observation:
    """A single stored observation."""

    id: str
    signal_source: str
    signal_headline: str
    category: str
    confidence: float
    field_note: str
    posted: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)


class MemoryStore:
    """SQLite-backed observation store."""

    def __init__(self, path: Path | str = "alien_terminal.db"):
        self.path = Path(path)
        self._init_schema()

    def _init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def store(self, observation: Observation) -> None:
        """Insert a new observation."""
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO observations "
                "(id, signal_source, signal_headline, category, confidence, "
                "field_note, posted, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    observation.id,
                    observation.signal_source,
                    observation.signal_headline,
                    observation.category,
                    observation.confidence,
                    observation.field_note,
                    int(observation.posted),
                    observation.created_at.isoformat(),
                ),
            )

    def mark_posted(self, observation_id: str) -> None:
        """Mark an observation as successfully broadcast."""
        with self.connect() as conn:
            conn.execute(
                "UPDATE observations SET posted = 1 WHERE id = ?",
                (observation_id,),
            )

    def recent(self, limit: int = 10) -> list[Observation]:
        """Return the most recent observations, newest first."""
        limit = max(1, min(limit, 100))
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM observations ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_observation(r) for r in rows]

    def unposted(self, limit: int = 5) -> list[Observation]:
        """Return observations that have not been broadcast yet."""
        limit = max(1, min(limit, 50))
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM observations WHERE posted = 0 "
                "ORDER BY created_at ASC LIMIT ?",
                (limit,),
            ).fetchall()
        return [self._row_to_observation(r) for r in rows]

    def by_category(self, category: str, limit: int = 20) -> list[Observation]:
        """Return observations filtered by cognitive category."""
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM observations WHERE category = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (category, limit),
            ).fetchall()
        return [self._row_to_observation(r) for r in rows]

    def count(self) -> int:
        with self.connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM observations").fetchone()
        return row[0]

    @staticmethod
    def _row_to_observation(row: sqlite3.Row) -> Observation:
        return Observation(
            id=row["id"],
            signal_source=row["signal_source"],
            signal_headline=row["signal_headline"],
            category=row["category"],
            confidence=row["confidence"],
            field_note=row["field_note"],
            posted=bool(row["posted"]),
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    @staticmethod
    def new_id() -> str:
        return str(uuid4())
