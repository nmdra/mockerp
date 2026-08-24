from __future__ import annotations

from database import Database
from services.accounting import minor_to_money


class PurchasingRepository:
    def __init__(self, database: Database):
        self.database = database

    def list_material_requests(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            rows = connection.execute("SELECT * FROM material_requests ORDER BY posting_date, name").fetchall()
            return [dict(row) for row in rows]

    def list_purchase_orders(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            rows = connection.execute("SELECT * FROM purchase_orders ORDER BY transaction_date, name").fetchall()
            result = []
            for row in rows:
                lines = connection.execute("SELECT * FROM purchase_order_items WHERE purchase_order_name = ? ORDER BY id", (row["name"],)).fetchall()
                result.append({
                    "name": row["name"],
                    "doctype": "Purchase Order",
                    "supplier": row["supplier"],
                    "transaction_date": row["transaction_date"],
                    "status": row["status"],
                    "docstatus": row["docstatus"],
                    "grand_total": float(minor_to_money(row["total_minor"])),
                    "items": [
                        {"item_code": line["item_code"], "qty": line["qty"], "received_qty": line["received_qty"], "billed_qty": line["billed_qty"], "warehouse": line["warehouse"], "rate": float(minor_to_money(line["rate_minor"]))}
                        for line in lines
                    ],
                })
            return result

    def list_purchase_receipts(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            rows = connection.execute("SELECT * FROM purchase_receipts ORDER BY posting_date, name").fetchall()
            return [dict(row) for row in rows]

    def list_purchase_invoices(self) -> list[dict[str, object]]:
        with self.database.connection() as connection:
            rows = connection.execute("SELECT * FROM purchase_invoices ORDER BY posting_date, name").fetchall()
            result = []
            for row in rows:
                lines = connection.execute("SELECT * FROM purchase_invoice_items WHERE invoice_name = ? ORDER BY id", (row["name"],)).fetchall()
                result.append({
                    "name": row["name"],
                    "doctype": "Purchase Invoice",
                    "supplier": row["supplier"],
                    "posting_date": row["posting_date"],
                    "company": "Serendib Consumer Products (Pvt) Ltd",
                    "currency": "LKR",
                    "status": row["status"],
                    "docstatus": row["docstatus"],
                    "grand_total": float(minor_to_money(row["total_minor"])),
                    "outstanding_amount": float(minor_to_money(row["outstanding_minor"])),
                    "items": [
                        {"item_code": line["item_code"], "qty": line["qty"], "rate": float(minor_to_money(line["rate_minor"]))}
                        for line in lines
                    ],
                })
            return result

    def get_purchase_invoice(self, name: str) -> dict[str, object] | None:
        return next((invoice for invoice in self.list_purchase_invoices() if invoice["name"] == name), None)
