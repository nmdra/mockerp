import sqlite3

VERSION = 2
NAME = "organization"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS branches (
            name TEXT PRIMARY KEY,
            company_name TEXT NOT NULL REFERENCES companies(name),
            address TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS departments (
            name TEXT PRIMARY KEY,
            company_name TEXT NOT NULL REFERENCES companies(name),
            parent_department TEXT REFERENCES departments(name),
            branch_name TEXT REFERENCES branches(name),
            is_group INTEGER NOT NULL DEFAULT 0 CHECK (is_group IN (0, 1)),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS designations (
            name TEXT PRIMARY KEY,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS employment_types (
            name TEXT PRIMARY KEY,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            identity TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS roles (
            name TEXT PRIMARY KEY,
            description TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS user_roles (
            identity TEXT NOT NULL REFERENCES users(identity),
            role TEXT NOT NULL REFERENCES roles(name),
            PRIMARY KEY (identity, role)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS approval_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_type TEXT NOT NULL,
            sequence_no INTEGER NOT NULL CHECK (sequence_no > 0),
            role TEXT NOT NULL REFERENCES roles(name),
            minimum_amount REAL NOT NULL DEFAULT 0 CHECK (minimum_amount >= 0),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            UNIQUE (document_type, sequence_no)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS approval_requests (
            id TEXT PRIMARY KEY,
            document_type TEXT NOT NULL,
            reference_name TEXT NOT NULL,
            amount REAL NOT NULL DEFAULT 0 CHECK (amount >= 0),
            status TEXT NOT NULL CHECK (
                status IN ('PENDING_APPROVAL', 'APPROVED', 'REJECTED', 'CANCELLED')
            ),
            requester_identity TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (document_type, reference_name)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS approval_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL REFERENCES approval_requests(id),
            sequence_no INTEGER NOT NULL CHECK (sequence_no > 0),
            actor_identity TEXT NOT NULL,
            action TEXT NOT NULL CHECK (action IN ('approve', 'reject')),
            comment TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            UNIQUE (request_id, sequence_no)
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_approval_rules_document "
        "ON approval_rules(document_type, minimum_amount, sequence_no)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_approval_requests_status "
        "ON approval_requests(status, created_at)"
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_identity TEXT NOT NULL,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            before_json TEXT,
            after_json TEXT,
            created_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TRIGGER IF NOT EXISTS audit_events_no_update
        BEFORE UPDATE ON audit_events
        BEGIN
            SELECT RAISE(ABORT, 'audit events are immutable');
        END
        """
    )
    connection.execute(
        """
        CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
        BEFORE DELETE ON audit_events
        BEGIN
            SELECT RAISE(ABORT, 'audit events are immutable');
        END
        """
    )
