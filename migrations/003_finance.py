import sqlite3

VERSION = 3
NAME = "finance"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            name TEXT PRIMARY KEY,
            account_number TEXT NOT NULL UNIQUE,
            root_type TEXT NOT NULL CHECK (root_type IN ('Asset', 'Liability', 'Equity', 'Income', 'Expense')),
            parent_account TEXT REFERENCES accounts(name),
            account_currency TEXT NOT NULL,
            company_name TEXT NOT NULL REFERENCES companies(name),
            is_group INTEGER NOT NULL DEFAULT 0 CHECK (is_group IN (0, 1)),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS journal_entries (
            name TEXT PRIMARY KEY,
            posting_date TEXT NOT NULL,
            voucher_type TEXT NOT NULL DEFAULT 'Journal Entry',
            remark TEXT NOT NULL DEFAULT '',
            docstatus INTEGER NOT NULL DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
            status TEXT NOT NULL CHECK (status IN ('Draft', 'Submitted', 'Cancelled')),
            total_debit_minor INTEGER NOT NULL DEFAULT 0,
            total_credit_minor INTEGER NOT NULL DEFAULT 0,
            owner_identity TEXT NOT NULL,
            reversal_of TEXT REFERENCES journal_entries(name)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS journal_entry_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            journal_entry_name TEXT NOT NULL REFERENCES journal_entries(name),
            account TEXT NOT NULL REFERENCES accounts(name),
            debit_minor INTEGER NOT NULL DEFAULT 0 CHECK (debit_minor >= 0),
            credit_minor INTEGER NOT NULL DEFAULT 0 CHECK (credit_minor >= 0),
            CHECK (NOT (debit_minor > 0 AND credit_minor > 0)),
            CHECK (debit_minor > 0 OR credit_minor > 0)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS gl_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voucher_type TEXT NOT NULL,
            voucher_no TEXT NOT NULL,
            account TEXT NOT NULL REFERENCES accounts(name),
            posting_date TEXT NOT NULL,
            debit_minor INTEGER NOT NULL DEFAULT 0 CHECK (debit_minor >= 0),
            credit_minor INTEGER NOT NULL DEFAULT 0 CHECK (credit_minor >= 0),
            is_reversal INTEGER NOT NULL DEFAULT 0 CHECK (is_reversal IN (0, 1)),
            CHECK (NOT (debit_minor > 0 AND credit_minor > 0)),
            CHECK (debit_minor > 0 OR credit_minor > 0)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_entries (
            name TEXT PRIMARY KEY,
            payment_type TEXT NOT NULL CHECK (payment_type IN ('Pay', 'Receive', 'Internal Transfer')),
            posting_date TEXT NOT NULL,
            party_type TEXT,
            party TEXT,
            paid_from TEXT NOT NULL REFERENCES accounts(name),
            paid_to TEXT NOT NULL REFERENCES accounts(name),
            paid_amount_minor INTEGER NOT NULL CHECK (paid_amount_minor > 0),
            received_amount_minor INTEGER NOT NULL CHECK (received_amount_minor > 0),
            docstatus INTEGER NOT NULL DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
            status TEXT NOT NULL CHECK (status IN ('Draft', 'Submitted', 'Cancelled')),
            owner_identity TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_entry_name TEXT NOT NULL REFERENCES payment_entries(name),
            reference_doctype TEXT NOT NULL,
            reference_name TEXT NOT NULL,
            allocated_minor INTEGER NOT NULL CHECK (allocated_minor > 0)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS open_items (
            reference_doctype TEXT NOT NULL,
            reference_name TEXT PRIMARY KEY,
            party_type TEXT NOT NULL,
            party TEXT NOT NULL,
            total_minor INTEGER NOT NULL CHECK (total_minor > 0),
            outstanding_minor INTEGER NOT NULL CHECK (outstanding_minor >= 0),
            account TEXT NOT NULL REFERENCES accounts(name),
            CHECK (outstanding_minor <= total_minor)
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_gl_entries_voucher ON gl_entries(voucher_no)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_open_items_party ON open_items(party_type, party)"
    )
