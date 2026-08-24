import sqlite3

VERSION = 9
NAME = "sales"


def upgrade(connection: sqlite3.Connection) -> None:
    columns = {row[1] for row in connection.execute("PRAGMA table_info(customers)")}
    if "credit_limit_minor" not in columns:
        connection.execute(
            "ALTER TABLE customers ADD COLUMN credit_limit_minor INTEGER NOT NULL DEFAULT 100000000"
        )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS sales_orders (
            name TEXT PRIMARY KEY,
            customer TEXT NOT NULL REFERENCES customers(name),
            transaction_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('Draft', 'Approved', 'Partially Delivered', 'Closed', 'Cancelled')),
            docstatus INTEGER NOT NULL DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
            total_minor INTEGER NOT NULL CHECK (total_minor >= 0),
            owner_identity TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS sales_order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sales_order_name TEXT NOT NULL REFERENCES sales_orders(name),
            item_code TEXT NOT NULL REFERENCES items(name),
            qty REAL NOT NULL CHECK (qty > 0),
            delivered_qty REAL NOT NULL DEFAULT 0 CHECK (delivered_qty >= 0),
            billed_qty REAL NOT NULL DEFAULT 0 CHECK (billed_qty >= 0),
            warehouse TEXT NOT NULL REFERENCES warehouses(name),
            rate_minor INTEGER NOT NULL CHECK (rate_minor >= 0)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS delivery_notes (
            name TEXT PRIMARY KEY,
            customer TEXT NOT NULL REFERENCES customers(name),
            posting_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('Draft', 'Submitted', 'Cancelled')),
            docstatus INTEGER NOT NULL DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
            sales_order_name TEXT NOT NULL REFERENCES sales_orders(name),
            owner_identity TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS delivery_note_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            delivery_note_name TEXT NOT NULL REFERENCES delivery_notes(name),
            sales_order_item_id INTEGER NOT NULL REFERENCES sales_order_items(id),
            item_code TEXT NOT NULL REFERENCES items(name),
            qty REAL NOT NULL CHECK (qty > 0),
            warehouse TEXT NOT NULL REFERENCES warehouses(name),
            rate_minor INTEGER NOT NULL CHECK (rate_minor >= 0)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS sales_invoices (
            name TEXT PRIMARY KEY,
            customer TEXT NOT NULL REFERENCES customers(name),
            posting_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('Draft', 'Submitted', 'Paid', 'Cancelled')),
            docstatus INTEGER NOT NULL DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
            total_minor INTEGER NOT NULL CHECK (total_minor >= 0),
            outstanding_minor INTEGER NOT NULL CHECK (outstanding_minor >= 0),
            delivery_note_name TEXT NOT NULL REFERENCES delivery_notes(name),
            owner_identity TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS sales_invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sales_invoice_name TEXT NOT NULL REFERENCES sales_invoices(name),
            sales_order_item_id INTEGER REFERENCES sales_order_items(id),
            item_code TEXT NOT NULL REFERENCES items(name),
            qty REAL NOT NULL CHECK (qty > 0),
            rate_minor INTEGER NOT NULL CHECK (rate_minor >= 0)
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_sales_order_customer ON sales_orders(customer, status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_sales_invoice_outstanding ON sales_invoices(outstanding_minor, status)")
