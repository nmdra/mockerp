from __future__ import annotations

from database import Database
from services.accounting import minor_to_money


class MastersRepository:
    def __init__(self, database: Database):
        self.database = database

    def list_customers(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            rows = connection.execute("SELECT * FROM customers ORDER BY rowid").fetchall()
            return [dict(row) for row in rows]

    def list_suppliers(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            rows = connection.execute("SELECT * FROM suppliers ORDER BY rowid").fetchall()
            return [dict(row) for row in rows]

    def list_items(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            rows = connection.execute("SELECT * FROM items ORDER BY rowid").fetchall()
            return [self._item(connection, row) for row in rows]

    def get_item(self, name: str) -> dict[str, object] | None:
        with self.database.connection() as connection:
            row = connection.execute("SELECT * FROM items WHERE name = ?", (name,)).fetchone()
            return self._item(connection, row) if row else None

    def list_item_groups(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM item_groups ORDER BY rowid")]

    def list_uoms(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM uoms ORDER BY rowid")]

    def list_warehouses(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM warehouses ORDER BY rowid")]

    def _item(self, connection, row) -> dict[str, object]:
        source = connection.execute(
            "SELECT warehouse FROM item_warehouse_eligibility WHERE item_code = ? AND direction = 'source' ORDER BY warehouse",
            (row["name"],),
        ).fetchall()
        target = connection.execute(
            "SELECT warehouse FROM item_warehouse_eligibility WHERE item_code = ? AND direction = 'target' ORDER BY warehouse",
            (row["name"],),
        ).fetchall()
        return {
            "name": row["name"],
            "doctype": "Item",
            "item_code": row["name"],
            "item_name": row["item_name"],
            "description": row["description"],
            "item_group": row["item_group"],
            "stock_uom": row["stock_uom"],
            "standard_rate": float(minor_to_money(row["standard_rate_minor"])),
            "valuation_method": row["valuation_method"],
            "valuation_account": row["valuation_account"],
            "is_stock_item": row["is_stock_item"],
            "is_purchase_item": row["is_purchase_item"],
            "is_sales_item": row["is_sales_item"],
            "has_batch_no": row["has_batch_no"],
            "reorder_level": row["reorder_level"],
            "reorder_qty": row["reorder_qty"],
            "source_warehouses": [warehouse[0] for warehouse in source],
            "target_warehouses": [warehouse[0] for warehouse in target],
        }
