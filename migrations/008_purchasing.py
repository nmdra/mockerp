import sqlite3

VERSION = 8
NAME = "purchasing"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS material_requests (
            name TEXT PRIMARY KEY,
            posting_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('Draft', 'Approved', 'Cancelled')),
            docstatus INTEGER NOT NULL DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
            requester_identity TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS material_request_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_name TEXT NOT NULL REFERENCES material_requests(name),
            item_code TEXT NOT NULL REFERENCES items(name),
            qty REAL NOT NULL CHECK (qty > 0),
            warehouse TEXT NOT NULL REFERENCES warehouses(name),
            ordered_qty REAL NOT NULL DEFAULT 0 CHECK (ordered_qty >= 0)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS purchase_orders (
            name TEXT PRIMARY KEY,
            supplier TEXT NOT NULL REFERENCES suppliers(name),
            transaction_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('Draft', 'Pending Approval', 'Approved', 'Cancelled', 'Closed')),
            docstatus INTEGER NOT NULL DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
            total_minor INTEGER NOT NULL CHECK (total_minor >= 0),
            requester_identity TEXT NOT NULL,
            approval_request_id TEXT UNIQUE REFERENCES approval_requests(id),
            material_request_name TEXT REFERENCES material_requests(name)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS purchase_order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_order_name TEXT NOT NULL REFERENCES purchase_orders(name),
            material_request_item_id INTEGER REFERENCES material_request_items(id),
            item_code TEXT NOT NULL REFERENCES items(name),
            qty REAL NOT NULL CHECK (qty > 0),
            received_qty REAL NOT NULL DEFAULT 0 CHECK (received_qty >= 0),
            billed_qty REAL NOT NULL DEFAULT 0 CHECK (billed_qty >= 0),
            warehouse TEXT NOT NULL REFERENCES warehouses(name),
            rate_minor INTEGER NOT NULL CHECK (rate_minor >= 0)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS purchase_receipts (
            name TEXT PRIMARY KEY,
            supplier TEXT NOT NULL REFERENCES suppliers(name),
            posting_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('Draft', 'Submitted', 'Cancelled')),
            docstatus INTEGER NOT NULL DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
            purchase_order_name TEXT NOT NULL REFERENCES purchase_orders(name),
            owner_identity TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS purchase_receipt_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_name TEXT NOT NULL REFERENCES purchase_receipts(name),
            purchase_order_item_id INTEGER NOT NULL REFERENCES purchase_order_items(id),
            item_code TEXT NOT NULL REFERENCES items(name),
            qty REAL NOT NULL CHECK (qty > 0),
            warehouse TEXT NOT NULL REFERENCES warehouses(name),
            rate_minor INTEGER NOT NULL CHECK (rate_minor >= 0)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS purchase_invoices (
            name TEXT PRIMARY KEY,
            supplier TEXT NOT NULL REFERENCES suppliers(name),
            posting_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('Draft', 'Submitted', 'Paid', 'Cancelled')),
            docstatus INTEGER NOT NULL DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
            total_minor INTEGER NOT NULL CHECK (total_minor >= 0),
            outstanding_minor INTEGER NOT NULL CHECK (outstanding_minor >= 0),
            purchase_receipt_name TEXT REFERENCES purchase_receipts(name),
            owner_identity TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS purchase_invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_name TEXT NOT NULL REFERENCES purchase_invoices(name),
            purchase_order_item_id INTEGER REFERENCES purchase_order_items(id),
            item_code TEXT NOT NULL REFERENCES items(name),
            qty REAL NOT NULL CHECK (qty > 0),
            rate_minor INTEGER NOT NULL CHECK (rate_minor >= 0)
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_po_supplier ON purchase_orders(supplier, status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_pi_outstanding ON purchase_invoices(outstanding_minor, status)")
