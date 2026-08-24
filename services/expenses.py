from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import sqlite3

from database import Database
from services.accounting import (
    AccountingError,
    create_payment_entry,
    money_to_minor,
    minor_to_money,
    submit_payment_entry,
)
from services.audit import record_audit
from services.authorization import Actor, AuthorizationService


class ExpenseError(ValueError):
    """Raised when an expense claim violates policy."""


@dataclass(frozen=True)
class ExpenseClaim:
    name: str
    employee: str
    total: float
    status: str
    payment_entry: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "doctype": "Expense Claim",
            "employee": self.employee,
            "total_claimed_amount": self.total,
            "status": self.status,
            "payment_entry": self.payment_entry,
        }


def _from_row(row: sqlite3.Row) -> ExpenseClaim:
    return ExpenseClaim(
        row["name"],
        row["employee_name"],
        float(minor_to_money(row["total_minor"])),
        row["status"],
        row["payment_entry"],
    )


def _row(database: Database, name: str) -> sqlite3.Row:
    with database.connection() as connection:
        row = connection.execute(
            "SELECT * FROM expense_claims WHERE name = ?", (name,)
        ).fetchone()
    if row is None:
        raise ExpenseError("expense claim was not found")
    return row


def create_expense_claim(
    database: Database,
    actor: Actor,
    *,
    employee_name: str,
    posting_date: str,
    description: str,
    lines: list[dict[str, object]],
) -> ExpenseClaim:
    with database.connection() as connection:
        employee = connection.execute(
            "SELECT * FROM employees WHERE name = ?", (employee_name,)
        ).fetchone()
    if employee is None:
        raise ExpenseError("employee was not found")
    try:
        AuthorizationService(database).require_employee_access(actor, employee["user_identity"])
    except PermissionError as exc:
        raise ExpenseError(str(exc)) from exc
    normalized = [
        (str(line.get("expense_type", "")), money_to_minor(line.get("amount", 0)))
        for line in lines
    ]
    if not normalized or any(not kind or amount <= 0 for kind, amount in normalized):
        raise ExpenseError("expense claim requires positive lines")
    total = sum(amount for _, amount in normalized)
    name = database.next_document_name("SCP-EXP")
    try:
        with database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO expense_claims
                    (name, employee_name, posting_date, description,
                     total_minor, status, docstatus, owner_identity)
                VALUES (?, ?, ?, ?, ?, 'Pending Approval', 0, ?)
                """,
                (name, employee_name, posting_date, description, total, actor.identity),
            )
            connection.executemany(
                """
                INSERT INTO expense_claim_lines (claim_name, expense_type, amount_minor)
                VALUES (?, ?, ?)
                """,
                [(name, kind, amount) for kind, amount in normalized],
            )
            record_audit(
                database,
                actor,
                "create",
                "Expense Claim",
                name,
                after={"employee": employee_name, "total_minor": total},
                connection=connection,
            )
            return _from_row(
                connection.execute("SELECT * FROM expense_claims WHERE name = ?", (name,)).fetchone()
            )
    except sqlite3.IntegrityError as exc:
        raise ExpenseError("expense claim already exists") from exc


def approve_expense_claim(
    database: Database, actor: Actor, name: str
) -> ExpenseClaim:
    row = _row(database, name)
    if actor.role not in {"admin", "department_manager", "hr_manager", "finance_manager"}:
        raise ExpenseError("expense claim requires an approving manager")
    if row["status"] != "Pending Approval":
        raise ExpenseError("expense claim is not pending")
    with database.transaction() as connection:
        connection.execute(
            "UPDATE expense_claims SET status = 'Approved', docstatus = 1 WHERE name = ?",
            (name,),
        )
        record_audit(
            database,
            actor,
            "approve",
            "Expense Claim",
            name,
            before={"status": "Pending Approval"},
            after={"status": "Approved"},
            connection=connection,
        )
        return _from_row(
            connection.execute("SELECT * FROM expense_claims WHERE name = ?", (name,)).fetchone()
        )


def reimburse_expense_claim(
    database: Database, actor: Actor, name: str
) -> ExpenseClaim:
    row = _row(database, name)
    if row["status"] != "Approved":
        raise ExpenseError("expense claim must be approved before reimbursement")
    try:
        payment = create_payment_entry(
            database,
            actor,
            posting_date=date.today().isoformat(),
            party_type="Employee",
            party=row["employee_name"],
            paid_from="2100 - Creditors - SCP",
            paid_to="1200 - Bank - SCP",
            paid_amount=minor_to_money(row["total_minor"]),
            references=[],
        )
        submit_payment_entry(database, actor, payment.name)
    except AccountingError as exc:
        raise ExpenseError(str(exc)) from exc
    with database.transaction() as connection:
        connection.execute(
            "UPDATE expense_claims SET status = 'Reimbursed', payment_entry = ? WHERE name = ?",
            (payment.name, name),
        )
        record_audit(
            database,
            actor,
            "reimburse",
            "Expense Claim",
            name,
            before={"status": "Approved"},
            after={"status": "Reimbursed", "payment_entry": payment.name},
            connection=connection,
        )
        return _from_row(
            connection.execute("SELECT * FROM expense_claims WHERE name = ?", (name,)).fetchone()
        )
