from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import sqlite3
from threading import RLock
from collections.abc import Iterator

from migrations import MIGRATIONS


class Database:
    """Own one SQLite connection and apply migrations atomically."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._connection: sqlite3.Connection | None = None
        self._lock = RLock()

    def initialize(self) -> None:
        with self._lock:
            if self._connection is None:
                self._open()
            self._apply_migrations()

    def _open(self) -> None:
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            str(self.path),
            check_same_thread=False,
            isolation_level=None,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA busy_timeout = 5000")

    def _require_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("database is not initialized")
        return self._connection

    def _apply_migrations(self) -> None:
        connection = self._require_connection()
        with self._lock:
            connection.execute("BEGIN")
            try:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        name TEXT NOT NULL,
                        applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                applied = {
                    row[0]
                    for row in connection.execute(
                        "SELECT version FROM schema_migrations"
                    ).fetchall()
                }
                for version, name, migration in MIGRATIONS:
                    if version in applied:
                        continue
                    migration(connection)
                    connection.execute(
                        "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                        (version, name),
                    )
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._require_connection()
        with self._lock:
            connection.execute("BEGIN")
            try:
                yield connection
            except BaseException:
                connection.rollback()
                raise
            else:
                connection.commit()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._require_connection()
        with self._lock:
            yield connection

    def close(self) -> None:
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    def reset(self) -> None:
        """Drop the local schema and recreate it; callers must gate this operation."""
        connection = self._require_connection()
        with self._lock:
            connection.execute("PRAGMA foreign_keys = OFF")
            connection.execute("BEGIN")
            try:
                tables = connection.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type = 'table' AND name != 'sqlite_sequence'
                    ORDER BY name DESC
                    """
                ).fetchall()
                for (name,) in tables:
                    connection.execute(f'DROP TABLE "{name.replace(chr(34), chr(34) * 2)}"')
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
            finally:
                connection.execute("PRAGMA foreign_keys = ON")
            self._apply_migrations()

    def table_names(self) -> list[str]:
        with self.connection() as connection:
            return [
                row[0]
                for row in connection.execute(
                    """
                    SELECT name FROM sqlite_master
                    WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                    """
                ).fetchall()
            ]

    def foreign_keys_enabled(self) -> bool:
        with self.connection() as connection:
            return connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    def next_document_name(self, series: str, width: int = 5) -> str:
        if not series or width < 1:
            raise ValueError("series must be non-empty and width must be positive")
        with self.transaction() as connection:
            row = connection.execute(
                "SELECT next_value FROM document_sequences WHERE series = ?",
                (series,),
            ).fetchone()
            if row is None:
                value = 1
                connection.execute(
                    "INSERT INTO document_sequences (series, next_value) VALUES (?, ?)",
                    (series, value + 1),
                )
            else:
                value = row[0]
                connection.execute(
                    "UPDATE document_sequences SET next_value = ? WHERE series = ?",
                    (value + 1, series),
                )
        return f"{series}-{value:0{width}d}"
