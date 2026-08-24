import sqlite3

VERSION = 10
NAME = "manufacturing"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS boms (
            name TEXT PRIMARY KEY,
            item_code TEXT NOT NULL REFERENCES items(name),
            quantity REAL NOT NULL CHECK (quantity > 0),
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
            UNIQUE (item_code, is_active)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS bom_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bom_name TEXT NOT NULL REFERENCES boms(name),
            item_code TEXT NOT NULL REFERENCES items(name),
            qty REAL NOT NULL CHECK (qty > 0),
            uom TEXT NOT NULL REFERENCES uoms(name)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS production_orders (
            name TEXT PRIMARY KEY,
            item_code TEXT NOT NULL REFERENCES items(name),
            bom_name TEXT NOT NULL REFERENCES boms(name),
            qty REAL NOT NULL CHECK (qty > 0),
            source_warehouse TEXT NOT NULL REFERENCES warehouses(name),
            target_warehouse TEXT NOT NULL REFERENCES warehouses(name),
            status TEXT NOT NULL CHECK (status IN ('Draft', 'In Process', 'Completed', 'Cancelled')),
            docstatus INTEGER NOT NULL DEFAULT 0 CHECK (docstatus IN (0, 1, 2)),
            owner_identity TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS production_order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            production_order_name TEXT NOT NULL REFERENCES production_orders(name),
            item_code TEXT NOT NULL REFERENCES items(name),
            qty REAL NOT NULL CHECK (qty > 0),
            consumed_qty REAL NOT NULL DEFAULT 0,
            produced_qty REAL NOT NULL DEFAULT 0
        )
        """
    )
