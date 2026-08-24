from __future__ import annotations

from database import Database


class HRRepository:
    def __init__(self, database: Database):
        self.database = database

    def list_employees(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM employees ORDER BY name"
            ).fetchall()
            return [self._employee(row) for row in rows]

    def get_employee(self, name: str) -> dict[str, object] | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM employees WHERE name = ?", (name,)
            ).fetchone()
            return self._employee(row) if row else None

    def get_employee_by_identity(self, identity: str):
        with self.database.connection() as connection:
            return connection.execute(
                "SELECT * FROM employees WHERE user_identity = ?", (identity,)
            ).fetchone()

    def list_attendance(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM attendance ORDER BY attendance_date, employee_name"
            ).fetchall()
            return [
                {
                    "name": f"ATT-{row['id']:05d}",
                    "employee": row["employee_name"],
                    "attendance_date": row["attendance_date"],
                    "status": row["status"],
                }
                for row in rows
            ]

    def list_leave_types(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM leave_types ORDER BY name"
            ).fetchall()
            return [dict(row) for row in rows]

    def list_leave_allocations(self, employee: str | None = None) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            if employee:
                rows = connection.execute(
                    "SELECT * FROM leave_allocations WHERE employee_name = ? ORDER BY id",
                    (employee,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM leave_allocations ORDER BY id"
                ).fetchall()
            return [
                {
                    "name": f"LEAVE-ALLOC-{row['id']:05d}",
                    "employee": row["employee_name"],
                    "leave_type": row["leave_type"],
                    "from_date": row["from_date"],
                    "to_date": row["to_date"],
                    "total_days": row["total_days"],
                    "used_days": row["used_days"],
                    "remaining_days": row["total_days"] - row["used_days"],
                }
                for row in rows
            ]

    def list_leave_applications(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM leave_applications ORDER BY posting_date, name"
            ).fetchall()
            return [self._leave_application(row) for row in rows]

    def get_leave_application(self, name: str) -> dict[str, object] | None:
        with self.database.connection() as connection:
            row = connection.execute(
                "SELECT * FROM leave_applications WHERE name = ?", (name,)
            ).fetchone()
            return self._leave_application(row) if row else None

    def _employee(self, row) -> dict[str, object]:
        return {
            "name": row["name"],
            "doctype": "Employee",
            "employee_name": row["employee_name"],
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "company": row["company_name"],
            "branch": row["branch_name"],
            "department": row["department_name"],
            "designation": row["designation"],
            "employment_type": row["employment_type"],
            "user_id": row["user_identity"],
            "supervisor": row["supervisor_identity"],
            "date_of_birth": row["date_of_birth"],
            "date_of_joining": row["date_of_joining"],
            "status": row["status"],
            "resignation_date": row["resignation_date"],
        }

    def _leave_application(self, row) -> dict[str, object]:
        return {
            "name": row["name"],
            "doctype": "Leave Application",
            "employee": row["employee_name"],
            "leave_type": row["leave_type"],
            "from_date": row["from_date"],
            "to_date": row["to_date"],
            "total_leave_days": row["total_days"],
            "half_day": row["half_day"],
            "status": row["status"],
            "docstatus": row["docstatus"],
            "description": row["description"],
            "posting_date": row["posting_date"],
            "approval_request": row["approval_request_id"],
        }
