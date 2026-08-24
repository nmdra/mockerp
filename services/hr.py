from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import sqlite3

from database import Database
from services.audit import record_audit
from services.authorization import Actor, AuthorizationService
from services.workflow import (
    ApprovalRequest,
    WorkflowError,
    approve_request,
    create_approval_request,
    reject_request,
)


class HRServiceError(ValueError):
    """Raised when an HR record violates a lifecycle or policy rule."""


@dataclass(frozen=True)
class AttendanceRecord:
    name: str
    employee: str
    attendance_date: str
    status: str


@dataclass(frozen=True)
class LeaveApplication:
    name: str
    employee: str
    leave_type: str
    from_date: str
    to_date: str
    total_days: float
    status: str
    docstatus: int
    approval_request_id: str | None

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "doctype": "Leave Application",
            "employee": self.employee,
            "leave_type": self.leave_type,
            "from_date": self.from_date,
            "to_date": self.to_date,
            "total_leave_days": self.total_days,
            "status": self.status,
            "docstatus": self.docstatus,
            "approval_request": self.approval_request_id,
        }


def _parse_date(value: str, field: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HRServiceError(f"{field} must be an ISO date") from exc


def calculate_leave_days(from_date: str, to_date: str, half_day: bool = False) -> float:
    start = _parse_date(from_date, "from_date")
    end = _parse_date(to_date, "to_date")
    if end < start:
        raise HRServiceError("to_date cannot be before from_date")
    days = float((end - start).days + 1)
    return days - 0.5 if half_day else days


def _employee_row(database: Database, name: str) -> sqlite3.Row:
    with database.connection() as connection:
        row = connection.execute(
            "SELECT * FROM employees WHERE name = ?", (name,)
        ).fetchone()
    if row is None:
        raise HRServiceError("employee was not found")
    return row


def create_attendance(
    database: Database,
    actor: Actor,
    employee_name: str,
    attendance_date: str,
    status: str,
) -> AttendanceRecord:
    if status not in {"Present", "Absent", "Half Day", "Work From Home"}:
        raise HRServiceError("attendance status is invalid")
    parsed_date = _parse_date(attendance_date, "attendance_date")
    if parsed_date > date.today():
        raise HRServiceError("future attendance is not allowed")
    employee = _employee_row(database, employee_name)
    AuthorizationService(database).require_employee_access(actor, employee["user_identity"])
    try:
        with database.transaction() as connection:
            cursor = connection.execute(
                """
                INSERT INTO attendance
                    (employee_name, attendance_date, status, owner_identity, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    employee_name,
                    attendance_date,
                    status,
                    actor.identity,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            record_audit(
                database,
                actor,
                "create",
                "Attendance",
                f"ATT-{cursor.lastrowid:05d}",
                after={
                    "employee": employee_name,
                    "attendance_date": attendance_date,
                    "status": status,
                },
                connection=connection,
            )
            return AttendanceRecord(
                f"ATT-{cursor.lastrowid:05d}", employee_name, attendance_date, status
            )
    except sqlite3.IntegrityError as exc:
        raise HRServiceError("duplicate attendance record") from exc


def _leave_from_row(row: sqlite3.Row) -> LeaveApplication:
    return LeaveApplication(
        name=row["name"],
        employee=row["employee_name"],
        leave_type=row["leave_type"],
        from_date=row["from_date"],
        to_date=row["to_date"],
        total_days=float(row["total_days"]),
        status=row["status"],
        docstatus=row["docstatus"],
        approval_request_id=row["approval_request_id"],
    )


def _leave_row(database: Database, name: str) -> sqlite3.Row:
    with database.connection() as connection:
        row = connection.execute(
            "SELECT * FROM leave_applications WHERE name = ?", (name,)
        ).fetchone()
    if row is None:
        raise HRServiceError("leave application was not found")
    return row


def create_leave_application(
    database: Database,
    actor: Actor,
    *,
    employee_name: str,
    leave_type: str,
    from_date: str,
    to_date: str,
    half_day: bool,
    description: str,
) -> LeaveApplication:
    employee = _employee_row(database, employee_name)
    AuthorizationService(database).require_employee_access(actor, employee["user_identity"])
    total_days = calculate_leave_days(from_date, to_date, half_day)
    with database.connection() as connection:
        leave = connection.execute(
            "SELECT * FROM leave_types WHERE name = ? AND is_active = 1", (leave_type,)
        ).fetchone()
        allocation = connection.execute(
            """
            SELECT * FROM leave_allocations
            WHERE employee_name = ? AND leave_type = ?
              AND from_date <= ? AND to_date >= ?
            ORDER BY id LIMIT 1
            """,
            (employee_name, leave_type, from_date, to_date),
        ).fetchone()
    if leave is None:
        raise HRServiceError("leave type was not found")
    if allocation is None or allocation["total_days"] - allocation["used_days"] < total_days:
        raise HRServiceError("leave balance is insufficient")

    try:
        approval = create_approval_request(
            database,
            actor,
            document_type="Leave Application",
            reference_name=database.next_document_name("SCP-LA-REF"),
            amount=0,
        )
        name = database.next_document_name("SCP-LA")
        with database.transaction() as connection:
            connection.execute(
                """
                INSERT INTO leave_applications
                    (name, employee_name, leave_type, from_date, to_date,
                     total_days, half_day, status, docstatus, description,
                     posting_date, approval_request_id, owner_identity)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending Approval', 0, ?, ?, ?, ?)
                """,
                (
                    name,
                    employee_name,
                    leave_type,
                    from_date,
                    to_date,
                    total_days,
                    int(half_day),
                    description,
                    date.today().isoformat(),
                    approval.id,
                    actor.identity,
                ),
            )
            record_audit(
                database,
                actor,
                "create",
                "Leave Application",
                name,
                after={
                    "employee": employee_name,
                    "leave_type": leave_type,
                    "from_date": from_date,
                    "to_date": to_date,
                    "total_days": total_days,
                    "status": "Pending Approval",
                },
                connection=connection,
            )
            return LeaveApplication(
                name,
                employee_name,
                leave_type,
                from_date,
                to_date,
                total_days,
                "Pending Approval",
                0,
                approval.id,
            )
    except sqlite3.IntegrityError as exc:
        raise HRServiceError("leave application already exists") from exc
    except WorkflowError as exc:
        raise HRServiceError(str(exc)) from exc


def _set_leave_status(
    database: Database,
    actor: Actor,
    name: str,
    status: str,
    docstatus: int,
) -> LeaveApplication:
    row = _leave_row(database, name)
    with database.transaction() as connection:
        connection.execute(
            "UPDATE leave_applications SET status = ?, docstatus = ? WHERE name = ?",
            (status, docstatus, name),
        )
        record_audit(
            database,
            actor,
            status.lower().replace(" ", "_"),
            "Leave Application",
            name,
            before={"status": row["status"]},
            after={"status": status},
            connection=connection,
        )
        return _leave_from_row(
            connection.execute("SELECT * FROM leave_applications WHERE name = ?", (name,)).fetchone()
        )


def approve_leave_application(
    database: Database, actor: Actor, name: str
) -> LeaveApplication:
    row = _leave_row(database, name)
    if row["status"] != "Pending Approval":
        raise HRServiceError("leave application is not pending")
    if row["approval_request_id"] is None:
        raise HRServiceError("leave application has no approval request")
    try:
        approval = approve_request(database, actor, row["approval_request_id"])
    except WorkflowError as exc:
        raise HRServiceError(str(exc)) from exc
    if approval.status != "APPROVED":
        return _leave_from_row(_leave_row(database, name))
    with database.transaction() as connection:
        allocation = connection.execute(
            """
            SELECT * FROM leave_allocations
            WHERE employee_name = ? AND leave_type = ?
              AND from_date <= ? AND to_date >= ?
            ORDER BY id LIMIT 1
            """,
            (row["employee_name"], row["leave_type"], row["from_date"], row["to_date"]),
        ).fetchone()
        if allocation is None or allocation["total_days"] - allocation["used_days"] < row["total_days"]:
            raise HRServiceError("leave balance is insufficient")
        connection.execute(
            "UPDATE leave_allocations SET used_days = used_days + ? WHERE id = ?",
            (row["total_days"], allocation["id"]),
        )
        connection.execute(
            "UPDATE leave_applications SET status = 'Approved', docstatus = 1 WHERE name = ?",
            (name,),
        )
        record_audit(
            database,
            actor,
            "approve",
            "Leave Application",
            name,
            before={"status": "Pending Approval"},
            after={"status": "Approved", "total_days": row["total_days"]},
            connection=connection,
        )
        return _leave_from_row(
            connection.execute("SELECT * FROM leave_applications WHERE name = ?", (name,)).fetchone()
        )


def reject_leave_application(
    database: Database, actor: Actor, name: str
) -> LeaveApplication:
    row = _leave_row(database, name)
    if row["status"] != "Pending Approval":
        raise HRServiceError("leave application is not pending")
    try:
        reject_request(database, actor, row["approval_request_id"])
    except WorkflowError as exc:
        raise HRServiceError(str(exc)) from exc
    return _set_leave_status(database, actor, name, "Rejected", 0)


def cancel_leave_application(
    database: Database, actor: Actor, name: str
) -> LeaveApplication:
    row = _leave_row(database, name)
    employee = _employee_row(database, row["employee_name"])
    AuthorizationService(database).require_employee_access(actor, employee["user_identity"])
    if row["status"] == "Cancelled":
        raise HRServiceError("leave application is already cancelled")
    with database.transaction() as connection:
        if row["status"] == "Approved":
            connection.execute(
                """
                UPDATE leave_allocations SET used_days = used_days - ?
                WHERE employee_name = ? AND leave_type = ?
                """,
                (row["total_days"], row["employee_name"], row["leave_type"]),
            )
        connection.execute(
            "UPDATE leave_applications SET status = 'Cancelled', docstatus = 2 WHERE name = ?",
            (name,),
        )
        record_audit(
            database,
            actor,
            "cancel",
            "Leave Application",
            name,
            before={"status": row["status"]},
            after={"status": "Cancelled"},
            connection=connection,
        )
        return _leave_from_row(
            connection.execute("SELECT * FROM leave_applications WHERE name = ?", (name,)).fetchone()
        )
