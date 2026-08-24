import sqlite3

VERSION = 7
NAME = "inventory"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_entries (
            name TEXT PRIMARY KEY,
            entry_type TEXT NOT NULL CHECK (
                entry_type IN ('Material Receipt', 'Material Issue', 'Material Transfer',
                               'Manufacturing Consumption', 'Manufacturing Receipt', 'Stock Adjustment')
            ),
            posting_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('Draft', 'Submitted', 'Cancelled')),
            docstatus INTEGER NOT NULL DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
            owner_identity TEXT NOT NULL,
            cancellation_of TEXT REFERENCES stock_entries(name)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_entry_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_entry_name TEXT NOT NULL REFERENCES stock_entries(name),
            item_code TEXT NOT NULL REFERENCES items(name),
            source_warehouse TEXT REFERENCES warehouses(name),
            target_warehouse TEXT REFERENCES warehouses(name),
            qty REAL NOT NULL CHECK (qty > 0),
            rate_minor INTEGER NOT NULL CHECK (rate_minor >= 0),
            batch_no TEXT
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS bins (
            item_code TEXT NOT NULL REFERENCES items(name),
            warehouse TEXT NOT NULL REFERENCES warehouses(name),
            actual_qty REAL NOT NULL DEFAULT 0,
            reserved_qty REAL NOT NULL DEFAULT 0 CHECK (reserved_qty >= 0),
            ordered_qty REAL NOT NULL DEFAULT 0 CHECK (ordered_qty >= 0),
            valuation_rate_minor INTEGER NOT NULL DEFAULT 0,
            stock_value_minor INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (item_code, warehouse),
            CHECK (actual_qty >= 0)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_ledger_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stock_entry_name TEXT NOT NULL REFERENCES stock_entries(name),
            item_code TEXT NOT NULL REFERENCES items(name),
            warehouse TEXT NOT NULL REFERENCES warehouses(name),
            posting_date TEXT NOT NULL,
            actual_qty_delta REAL NOT NULL,
            qty_after_transaction REAL NOT NULL CHECK (qty_after_transaction >= 0),
            valuation_rate_minor INTEGER NOT NULL,
            stock_value_delta_minor INTEGER NOT NULL,
            is_reversal INTEGER NOT NULL DEFAULT 0 CHECK (is_reversal IN (0, 1))
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_stock_ledger_item_warehouse "
        "ON stock_ledger_entries(item_code, warehouse, id)"
    )
    connection.execute(
        """
        CREATE TRIGGER IF NOT EXISTS stock_ledger_no_update
        BEFORE UPDATE ON stock_ledger_entries
        BEGIN
            SELECT RAISE(ABORT, 'stock ledger entries are immutable');
        END
        """
    )
    connection.execute(
        """
        CREATE TRIGGER IF NOT EXISTS stock_ledger_no_delete
        BEFORE DELETE ON stock_ledger_entries
        BEGIN
            SELECT RAISE(ABORT, 'stock ledger entries are immutable');
        END
        """
    )
