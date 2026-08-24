import sqlite3

VERSION = 6
NAME = "masters"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS customers (
            name TEXT PRIMARY KEY,
            customer_name TEXT NOT NULL,
            customer_group TEXT NOT NULL,
            territory TEXT NOT NULL,
            company_name TEXT NOT NULL REFERENCES companies(name),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS suppliers (
            name TEXT PRIMARY KEY,
            supplier_name TEXT NOT NULL,
            supplier_group TEXT NOT NULL,
            country TEXT NOT NULL,
            company_name TEXT NOT NULL REFERENCES companies(name),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS party_contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            party_type TEXT NOT NULL CHECK (party_type IN ('Customer', 'Supplier')),
            party_name TEXT NOT NULL,
            contact_name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            is_primary INTEGER NOT NULL DEFAULT 1 CHECK (is_primary IN (0, 1)),
            UNIQUE (party_type, party_name, email)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS item_groups (
            name TEXT PRIMARY KEY,
            parent_group TEXT REFERENCES item_groups(name),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS uoms (
            name TEXT PRIMARY KEY,
            must_be_whole_number INTEGER NOT NULL DEFAULT 0 CHECK (must_be_whole_number IN (0, 1)),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS items (
            name TEXT PRIMARY KEY,
            item_name TEXT NOT NULL,
            description TEXT NOT NULL,
            item_group TEXT NOT NULL REFERENCES item_groups(name),
            stock_uom TEXT NOT NULL REFERENCES uoms(name),
            standard_rate_minor INTEGER NOT NULL DEFAULT 0 CHECK (standard_rate_minor >= 0),
            valuation_method TEXT NOT NULL CHECK (valuation_method IN ('Moving Average', 'FIFO')),
            valuation_account TEXT NOT NULL REFERENCES accounts(name),
            is_stock_item INTEGER NOT NULL DEFAULT 1 CHECK (is_stock_item IN (0, 1)),
            is_purchase_item INTEGER NOT NULL DEFAULT 1 CHECK (is_purchase_item IN (0, 1)),
            is_sales_item INTEGER NOT NULL DEFAULT 1 CHECK (is_sales_item IN (0, 1)),
            has_batch_no INTEGER NOT NULL DEFAULT 0 CHECK (has_batch_no IN (0, 1)),
            reorder_level REAL NOT NULL DEFAULT 0 CHECK (reorder_level >= 0),
            reorder_qty REAL NOT NULL DEFAULT 0 CHECK (reorder_qty >= 0),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS warehouses (
            name TEXT PRIMARY KEY,
            parent_warehouse TEXT REFERENCES warehouses(name),
            company_name TEXT NOT NULL REFERENCES companies(name),
            warehouse_type TEXT NOT NULL,
            is_group INTEGER NOT NULL DEFAULT 0 CHECK (is_group IN (0, 1)),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS item_warehouse_eligibility (
            item_code TEXT NOT NULL REFERENCES items(name),
            warehouse TEXT NOT NULL REFERENCES warehouses(name),
            direction TEXT NOT NULL CHECK (direction IN ('source', 'target')),
            PRIMARY KEY (item_code, warehouse, direction)
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_items_group ON items(item_group)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_warehouse_parent ON warehouses(parent_warehouse)"
    )
