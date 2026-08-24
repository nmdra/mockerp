from __future__ import annotations

from database import Database
from services.payroll import _advance_from_row, _row_to_slip
from services.expenses import _from_row as expense_from_row


class PayrollRepository:
    def __init__(self, database: Database):
        self.database = database

    def list_salary_slips(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM salary_slips ORDER BY posting_date, name"
            ).fetchall()
            return [_row_to_slip(connection, row).as_dict() for row in rows]

    def get_salary_slip(self, name: str) -> dict[str, object] | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM salary_slips WHERE name = ?", (name,)
            ).fetchone()
            return _row_to_slip(connection, row).as_dict() if row else None

    def list_employee_advances(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM employee_advances ORDER BY posting_date, name"
            ).fetchall()
            return [_advance_from_row(row).as_dict() for row in rows]

    def list_expense_claims(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM expense_claims ORDER BY posting_date, name"
            ).fetchall()
            return [expense_from_row(row).as_dict() for row in rows]

    def get_expense_claim(self, name: str) -> dict[str, object] | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM expense_claims WHERE name = ?", (name,)
            ).fetchone()
            return expense_from_row(row).as_dict() if row else None
