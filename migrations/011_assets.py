import sqlite3

VERSION = 11
NAME = "assets"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS asset_categories (
            name TEXT PRIMARY KEY,
            asset_account TEXT NOT NULL REFERENCES accounts(name),
            accumulated_depreciation_account TEXT NOT NULL REFERENCES accounts(name),
            depreciation_expense_account TEXT NOT NULL REFERENCES accounts(name),
            default_useful_life_months INTEGER NOT NULL CHECK (default_useful_life_months > 0),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS assets (
            name TEXT PRIMARY KEY,
            category TEXT NOT NULL REFERENCES asset_categories(name),
            asset_name TEXT NOT NULL,
            acquisition_date TEXT NOT NULL,
            acquisition_cost_minor INTEGER NOT NULL CHECK (acquisition_cost_minor > 0),
            accumulated_depreciation_minor INTEGER NOT NULL DEFAULT 0 CHECK (accumulated_depreciation_minor >= 0),
            location TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('Draft', 'Capitalized', 'Disposed')),
            docstatus INTEGER NOT NULL DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
            owner_identity TEXT NOT NULL,
            disposal_date TEXT,
            disposal_proceeds_minor INTEGER
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS asset_depreciation_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_name TEXT NOT NULL REFERENCES assets(name),
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            amount_minor INTEGER NOT NULL CHECK (amount_minor >= 0),
            status TEXT NOT NULL CHECK (status IN ('Planned', 'Posted', 'Cancelled')),
            UNIQUE (asset_name, period_start, period_end)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS asset_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_name TEXT NOT NULL REFERENCES assets(name),
            event_type TEXT NOT NULL CHECK (event_type IN ('Capitalized', 'Depreciated', 'Transferred', 'Disposed')),
            event_date TEXT NOT NULL,
            from_location TEXT,
            to_location TEXT,
            amount_minor INTEGER,
            actor_identity TEXT NOT NULL,
            journal_entry TEXT REFERENCES journal_entries(name)
        )
        """
    )
