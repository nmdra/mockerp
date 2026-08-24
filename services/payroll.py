from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import sqlite3

from database import Database
from services.accounting import (
    AccountingError,
    create_journal_entry,
    minor_to_money,
    submit_journal_entry,
)
from services.audit import record_audit
from services.authorization import Actor


class PayrollError(ValueError):
    """Raised when a payroll document cannot be calculated or posted."""


@dataclass(frozen=True)
class EmployeeAdvance:
    name: str
    employee: str
    amount: Decimal
    outstanding: Decimal
    status: str

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "doctype": "Employee Advance",
            "employee": self.employee,
            "advance_amount": float(self.amount),
            "outstanding_amount": float(self.outstanding),
            "status": self.status,
        }


@dataclass(frozen=True)
class SalarySlip:
    name: str
    employee: str
    start_date: str
    end_date: str
    gross_pay: Decimal
    total_deduction: Decimal
    net_pay: Decimal
    status: str
    journal_entry: str | None
    lines: tuple[dict[str, object], ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "doctype": "Salary Slip",
            "employee": self.employee,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "gross_pay": float(self.gross_pay),
            "total_deduction": float(self.total_deduction),
            "net_pay": float(self.net_pay),
            "status": self.status,
            "docstatus": 1 if self.status == "Submitted" else 2 if self.status == "Cancelled" else 0,
            "journal_entry": self.journal_entry,
            "earnings": [line for line in self.lines if line["component_type"] == "Earning"],
            "deductions": [line for line in self.lines if line["component_type"] == "Deduction"],
        }


def _row_to_slip(connection: sqlite3.Connection, row: sqlite3.Row) -> SalarySlip:
    lines = connection.execute(
        """
        SELECT component_name, component_type, amount_minor
        FROM salary_slip_lines WHERE salary_slip_name = ? ORDER BY id
        """,
        (row["name"],),
    ).fetchall()
    return SalarySlip(
        name=row["name"],
        employee=row["employee_name"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        gross_pay=minor_to_money(row["gross_pay_minor"]),
        total_deduction=minor_to_money(row["total_deduction_minor"]),
        net_pay=minor_to_money(row["net_pay_minor"]),
        status=row["status"],
        journal_entry=row["journal_entry"],
        lines=tuple(
            {
                "component": line["component_name"],
                "component_type": line["component_type"],
                "amount": float(minor_to_money(line["amount_minor"])),
            }
            for line in lines
        ),
    )


def _advance_from_row(row: sqlite3.Row) -> EmployeeAdvance:
    return EmployeeAdvance(
        row["name"],
        row["employee_name"],
        minor_to_money(row["amount_minor"]),
        minor_to_money(row["outstanding_minor"]),
        row["status"],
    )


def create_employee_advance(
    database: Database,
    actor: Actor,
    *,
    employee_name: str,
    posting_date: str,
    amount: Decimal | int | float | str,
) -> EmployeeAdvance:
    from services.accounting import money_to_minor

    with database.connection() as connection:
        employee = connection.execute(
            "SELECT * FROM employees WHERE name = ?", (employee_name,)
        ).fetchone()
    if employee is None:
        raise PayrollError("employee was not found")
    try:
        amount_minor = money_to_minor(amount)
    except AccountingError as exc:
        raise PayrollError(str(exc)) from exc
    if amount_minor <= 0:
        raise PayrollError("advance amount must be positive")
    name = database.next_document_name("SCP-ADV")
    with database.transaction() as connection:
        connection.execute(
            """
            INSERT INTO employee_advances
                (name, employee_name, posting_date, amount_minor,
                 outstanding_minor, status, owner_identity)
            VALUES (?, ?, ?, ?, ?, 'Draft', ?)
            """,
            (name, employee_name, posting_date, amount_minor, amount_minor, actor.identity),
        )
        record_audit(
            database, actor, "create", "Employee Advance", name,
            after={"employee": employee_name, "amount_minor": amount_minor},
            connection=connection,
        )
        return _advance_from_row(connection.execute("SELECT * FROM employee_advances WHERE name = ?", (name,)).fetchone())


def approve_employee_advance(
    database: Database, actor: Actor, name: str
) -> EmployeeAdvance:
    if actor.role not in {"admin", "finance_manager", "hr_manager", "department_manager"}:
        raise PayrollError("employee advance requires an approving manager")
    with database.transaction() as connection:
        row = connection.execute("SELECT * FROM employee_advances WHERE name = ?", (name,)).fetchone()
        if row is None or row["status"] != "Draft":
            raise PayrollError("employee advance is not a draft")
        connection.execute("UPDATE employee_advances SET status = 'Approved' WHERE name = ?", (name,))
        record_audit(
            database, actor, "approve", "Employee Advance", name,
            before={"status": "Draft"}, after={"status": "Approved"}, connection=connection,
        )
        return _advance_from_row(connection.execute("SELECT * FROM employee_advances WHERE name = ?", (name,)).fetchone())


def settle_employee_advance(
    database: Database, actor: Actor, name: str
) -> EmployeeAdvance:
    with database.transaction() as connection:
        row = connection.execute("SELECT * FROM employee_advances WHERE name = ?", (name,)).fetchone()
        if row is None or row["status"] != "Approved":
            raise PayrollError("employee advance is not approved")
        connection.execute(
            "UPDATE employee_advances SET outstanding_minor = 0, status = 'Settled' WHERE name = ?",
            (name,),
        )
        record_audit(
            database, actor, "settle", "Employee Advance", name,
            before={"status": "Approved", "outstanding_minor": row["outstanding_minor"]},
            after={"status": "Settled", "outstanding_minor": 0}, connection=connection,
        )
        return _advance_from_row(connection.execute("SELECT * FROM employee_advances WHERE name = ?", (name,)).fetchone())


def create_salary_slip(
    database: Database,
    actor: Actor,
    *,
    employee_name: str,
    start_date: str,
    end_date: str,
) -> SalarySlip:
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError as exc:
        raise PayrollError("salary period must use ISO dates") from exc
    if end < start:
        raise PayrollError("salary period is invalid")
    with database.connection() as connection:
        employee = connection.execute(
            "SELECT 1 FROM employees WHERE name = ?", (employee_name,)
        ).fetchone()
        assignment = connection.execute(
            """
            SELECT * FROM salary_assignments
            WHERE employee_name = ? AND is_active = 1
              AND from_date <= ? AND (to_date IS NULL OR to_date >= ?)
            ORDER BY from_date DESC LIMIT 1
            """,
            (employee_name, end_date, start_date),
        ).fetchone()
        if employee is None:
            raise PayrollError("employee or active salary assignment was not found")
        if assignment is None:
            raise PayrollError("active salary assignment was not found")
        components = connection.execute(
            """
            SELECT structure_components.component_name,
                   salary_components.component_type,
                   structure_components.amount_minor
            FROM salary_structure_components AS structure_components
            JOIN salary_components
              ON salary_components.name = structure_components.component_name
            WHERE structure_components.structure_name = ? ORDER BY structure_components.id
            """,
            (assignment["structure_name"],),
        ).fetchall()
    lines: list[tuple[str, str, int]] = []
    for component in components:
        amount = assignment["base_amount_minor"] if component["component_name"] == "Basic Salary" else component["amount_minor"]
        lines.append((component["component_name"], component["component_type"], amount))
    gross = sum(amount for _, kind, amount in lines if kind == "Earning")
    deduction = sum(amount for _, kind, amount in lines if kind == "Deduction")
    name = database.next_document_name("SCP-SAL")
    try:
        with database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO salary_slips
                    (name, employee_name, start_date, end_date, posting_date,
                     gross_pay_minor, total_deduction_minor, net_pay_minor,
                     status, docstatus, owner_identity)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Draft', 0, ?)
                """,
                (
                    name,
                    employee_name,
                    start_date,
                    end_date,
                    end_date,
                    gross,
                    deduction,
                    gross - deduction,
                    actor.identity,
                ),
            )
            connection.executemany(
                """
                INSERT INTO salary_slip_lines
                    (salary_slip_name, component_name, component_type, amount_minor)
                VALUES (?, ?, ?, ?)
                """,
                [(name, component, kind, amount) for component, kind, amount in lines],
            )
            record_audit(
                database,
                actor,
                "create",
                "Salary Slip",
                name,
                after={"employee": employee_name, "gross_pay_minor": gross},
                connection=connection,
            )
            return _row_to_slip(
                connection,
                connection.execute("SELECT * FROM salary_slips WHERE name = ?", (name,)).fetchone(),
            )
    except sqlite3.IntegrityError as exc:
        raise PayrollError("salary slip already exists") from exc


def submit_salary_slip(
    database: Database, actor: Actor, name: str
) -> SalarySlip:
    with database.connection() as connection:
        row = connection.execute(
            "SELECT * FROM salary_slips WHERE name = ?", (name,)
        ).fetchone()
    if row is None:
        raise PayrollError("salary slip was not found")
    if row["status"] != "Draft":
        raise PayrollError("only draft salary slips can be submitted")
    try:
        journal = create_journal_entry(
            database,
            actor,
            posting_date=row["posting_date"],
            remark=f"Payroll {name}",
            accounts=[
                {
                    "account": "5100 - COGS - SCP",
                    "debit": float(minor_to_money(row["gross_pay_minor"])),
                    "credit": 0,
                },
                {
                    "account": "2100 - Creditors - SCP",
                    "debit": 0,
                    "credit": float(minor_to_money(row["gross_pay_minor"])),
                },
            ],
        )
        submit_journal_entry(database, actor, journal.name)
    except AccountingError as exc:
        raise PayrollError(str(exc)) from exc
    with database.transaction() as connection:
        connection.execute(
            "UPDATE salary_slips SET status = 'Submitted', docstatus = 1, journal_entry = ? WHERE name = ?",
            (journal.name, name),
        )
        record_audit(
            database,
            actor,
            "submit",
            "Salary Slip",
            name,
            before={"status": "Draft"},
            after={"status": "Submitted", "journal_entry": journal.name},
            connection=connection,
        )
        return _row_to_slip(
            connection,
            connection.execute("SELECT * FROM salary_slips WHERE name = ?", (name,)).fetchone(),
        )
