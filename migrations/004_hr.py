import sqlite3

VERSION = 4
NAME = "hr"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS employees (
            name TEXT PRIMARY KEY,
            employee_name TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            company_name TEXT NOT NULL REFERENCES companies(name),
            branch_name TEXT NOT NULL REFERENCES branches(name),
            department_name TEXT NOT NULL REFERENCES departments(name),
            designation TEXT NOT NULL REFERENCES designations(name),
            employment_type TEXT NOT NULL REFERENCES employment_types(name),
            user_identity TEXT NOT NULL UNIQUE REFERENCES users(identity),
            supervisor_identity TEXT REFERENCES users(identity),
            date_of_birth TEXT NOT NULL,
            date_of_joining TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('Active', 'Inactive', 'Left')),
            resignation_date TEXT,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS employee_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL REFERENCES employees(name),
            document_type TEXT NOT NULL,
            file_name TEXT NOT NULL,
            storage_reference TEXT NOT NULL,
            checksum TEXT NOT NULL,
            UNIQUE (employee_name, document_type, file_name)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS employee_transfers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL REFERENCES employees(name),
            from_branch TEXT NOT NULL,
            to_branch TEXT NOT NULL,
            from_department TEXT NOT NULL,
            to_department TEXT NOT NULL,
            effective_date TEXT NOT NULL,
            actor_identity TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL REFERENCES employees(name),
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN ('Present', 'Absent', 'Half Day', 'Work From Home')
            ),
            owner_identity TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (employee_name, attendance_date)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS leave_types (
            name TEXT PRIMARY KEY,
            max_days REAL NOT NULL CHECK (max_days >= 0),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS leave_allocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL REFERENCES employees(name),
            leave_type TEXT NOT NULL REFERENCES leave_types(name),
            from_date TEXT NOT NULL,
            to_date TEXT NOT NULL,
            total_days REAL NOT NULL CHECK (total_days >= 0),
            used_days REAL NOT NULL DEFAULT 0 CHECK (used_days >= 0),
            UNIQUE (employee_name, leave_type, from_date, to_date)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS leave_applications (
            name TEXT PRIMARY KEY,
            employee_name TEXT NOT NULL REFERENCES employees(name),
            leave_type TEXT NOT NULL REFERENCES leave_types(name),
            from_date TEXT NOT NULL,
            to_date TEXT NOT NULL,
            total_days REAL NOT NULL CHECK (total_days > 0),
            half_day INTEGER NOT NULL DEFAULT 0 CHECK (half_day IN (0, 1)),
            status TEXT NOT NULL CHECK (
                status IN ('Open', 'Pending Approval', 'Approved', 'Rejected', 'Cancelled')
            ),
            docstatus INTEGER NOT NULL DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
            description TEXT NOT NULL DEFAULT '',
            posting_date TEXT NOT NULL,
            approval_request_id TEXT UNIQUE REFERENCES approval_requests(id),
            owner_identity TEXT NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_attendance_employee_date "
        "ON attendance(employee_name, attendance_date)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_leave_application_employee "
        "ON leave_applications(employee_name, status)"
    )
