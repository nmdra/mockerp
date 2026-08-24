from __future__ import annotations

from database import Database
from services.accounting import (
    _journal_from_row,
    _payment_from_row,
)


class FinanceRepository:
    def __init__(self, database: Database):
        self.database = database

    def list_journal_entries(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM journal_entries ORDER BY posting_date, name"
            ).fetchall()
            return [_journal_from_row(connection, row).as_dict() for row in rows]

    def get_journal_entry(self, name: str) -> dict[str, object] | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM journal_entries WHERE name = ?", (name,)
            ).fetchone()
            return _journal_from_row(connection, row).as_dict() if row else None

    def list_payment_entries(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM payment_entries ORDER BY posting_date, name"
            ).fetchall()
            return [_payment_from_row(connection, row).as_dict() for row in rows]

    def get_payment_entry(self, name: str) -> dict[str, object] | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM payment_entries WHERE name = ?", (name,)
            ).fetchone()
            return _payment_from_row(connection, row).as_dict() if row else None

    def list_accounts(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM accounts ORDER BY account_number"
            ).fetchall()
            return [dict(row) for row in rows]
