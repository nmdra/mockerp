import sqlite3

VERSION = 5
NAME = "payroll"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS salary_components (
            name TEXT PRIMARY KEY,
            component_type TEXT NOT NULL CHECK (component_type IN ('Earning', 'Deduction')),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS salary_structures (
            name TEXT PRIMARY KEY,
            company_name TEXT NOT NULL REFERENCES companies(name),
            currency TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS salary_structure_components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            structure_name TEXT NOT NULL REFERENCES salary_structures(name),
            component_name TEXT NOT NULL REFERENCES salary_components(name),
            amount_minor INTEGER NOT NULL DEFAULT 0 CHECK (amount_minor >= 0),
            percentage REAL,
            UNIQUE (structure_name, component_name)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS salary_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_name TEXT NOT NULL REFERENCES employees(name),
            structure_name TEXT NOT NULL REFERENCES salary_structures(name),
            base_amount_minor INTEGER NOT NULL CHECK (base_amount_minor > 0),
            from_date TEXT NOT NULL,
            to_date TEXT,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            UNIQUE (employee_name, structure_name, from_date)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS salary_slips (
            name TEXT PRIMARY KEY,
            employee_name TEXT NOT NULL REFERENCES employees(name),
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            posting_date TEXT NOT NULL,
            gross_pay_minor INTEGER NOT NULL DEFAULT 0,
            total_deduction_minor INTEGER NOT NULL DEFAULT 0,
            net_pay_minor INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL CHECK (status IN ('Draft', 'Submitted', 'Cancelled')),
            docstatus INTEGER NOT NULL DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
            owner_identity TEXT NOT NULL,
            journal_entry TEXT REFERENCES journal_entries(name),
            UNIQUE (employee_name, start_date, end_date)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS salary_slip_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            salary_slip_name TEXT NOT NULL REFERENCES salary_slips(name),
            component_name TEXT NOT NULL REFERENCES salary_components(name),
            component_type TEXT NOT NULL CHECK (component_type IN ('Earning', 'Deduction')),
            amount_minor INTEGER NOT NULL CHECK (amount_minor >= 0)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS employee_advances (
            name TEXT PRIMARY KEY,
            employee_name TEXT NOT NULL REFERENCES employees(name),
            posting_date TEXT NOT NULL,
            amount_minor INTEGER NOT NULL CHECK (amount_minor > 0),
            outstanding_minor INTEGER NOT NULL CHECK (outstanding_minor >= 0),
            status TEXT NOT NULL CHECK (status IN ('Draft', 'Approved', 'Settled', 'Cancelled')),
            owner_identity TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS expense_claims (
            name TEXT PRIMARY KEY,
            employee_name TEXT NOT NULL REFERENCES employees(name),
            posting_date TEXT NOT NULL,
            description TEXT NOT NULL,
            total_minor INTEGER NOT NULL CHECK (total_minor > 0),
            status TEXT NOT NULL CHECK (
                status IN ('Draft', 'Pending Approval', 'Approved', 'Rejected', 'Reimbursed', 'Cancelled')
            ),
            docstatus INTEGER NOT NULL DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
            owner_identity TEXT NOT NULL,
            payment_entry TEXT REFERENCES payment_entries(name)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS expense_claim_lines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_name TEXT NOT NULL REFERENCES expense_claims(name),
            expense_type TEXT NOT NULL,
            amount_minor INTEGER NOT NULL CHECK (amount_minor > 0)
        )
        """
    )
