from __future__ import annotations

from database import Database
from services.accounting import minor_to_money


class SalesRepository:
    def __init__(self, database: Database):
        self.database = database

    def list_sales_orders(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            rows = connection.execute("SELECT * FROM sales_orders ORDER BY transaction_date, name").fetchall()
            result = []
            for row in rows:
                lines = connection.execute("SELECT * FROM sales_order_items WHERE sales_order_name = ? ORDER BY id", (row["name"],)).fetchall()
                result.append({
                    "name": row["name"], "doctype": "Sales Order", "customer": row["customer"],
                    "transaction_date": row["transaction_date"], "status": row["status"], "docstatus": row["docstatus"],
                    "grand_total": float(minor_to_money(row["total_minor"])),
                    "items": [dict(line) for line in lines],
                })
            return result

    def list_delivery_notes(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            return [dict(row) for row in connection.execute("SELECT * FROM delivery_notes ORDER BY posting_date, name")]

    def list_sales_invoices(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            rows = connection.execute("SELECT * FROM sales_invoices ORDER BY posting_date, name").fetchall()
            return [
                {
                    "name": row["name"], "doctype": "Sales Invoice", "customer": row["customer"],
                    "posting_date": row["posting_date"], "status": row["status"], "docstatus": row["docstatus"],
                    "grand_total": float(minor_to_money(row["total_minor"])),
                    "outstanding_amount": float(minor_to_money(row["outstanding_minor"])),
                }
                for row in rows
            ]
