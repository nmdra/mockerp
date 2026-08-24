from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import sqlite3
from typing import Any

from database import Database
from services.accounting import AccountingError, create_journal_entry, minor_to_money, money_to_minor, submit_journal_entry
from services.audit import record_audit
from services.authorization import Actor
from services.inventory import InventoryError, create_stock_entry, submit_stock_entry


class SalesError(ValueError):
    """Raised when an order-to-cash document cannot advance."""


@dataclass(frozen=True)
class SalesDocument:
    name: str
    status: str
    total: float = 0
    outstanding: float = 0


def create_sales_order(
    database: Database,
    actor: Actor,
    *,
    customer: str,
    transaction_date: str,
    items: list[dict[str, Any]],
) -> SalesDocument:
    if not items:
        raise SalesError("sales order requires items")
    name = database.next_document_name("SCP-SO")
    normalized = []
    total = 0
    with database.transaction() as connection:
        customer_row = connection.execute("SELECT * FROM customers WHERE name = ?", (customer,)).fetchone()
        if customer_row is None:
            raise SalesError("customer was not found")
        for item in items:
            code = str(item.get("item_code", ""))
            warehouse = str(item.get("warehouse", ""))
            qty = float(item.get("qty", 0))
            rate = money_to_minor(item.get("rate", 0))
            if qty <= 0 or rate < 0:
                raise SalesError("sales order quantity and rate are invalid")
            if connection.execute("SELECT 1 FROM items WHERE name = ?", (code,)).fetchone() is None:
                raise SalesError("item was not found")
            if connection.execute("SELECT 1 FROM warehouses WHERE name = ?", (warehouse,)).fetchone() is None:
                raise SalesError("warehouse was not found")
            if connection.execute("SELECT 1 FROM item_warehouse_eligibility WHERE item_code = ? AND warehouse = ? AND direction = 'source'", (code, warehouse)).fetchone() is None:
                raise SalesError("source warehouse is not eligible for this item")
            normalized.append((code, qty, warehouse, rate))
            total += int(round(qty * rate))
        if total > customer_row["credit_limit_minor"]:
            raise SalesError("customer credit limit would be exceeded")
        connection.execute(
            """
            INSERT INTO sales_orders (name, customer, transaction_date, status, docstatus, total_minor, owner_identity)
            VALUES (?, ?, ?, 'Approved', 1, ?, ?)
            """,
            (name, customer, transaction_date, total, actor.identity),
        )
        connection.executemany(
            """
            INSERT INTO sales_order_items (sales_order_name, item_code, qty, warehouse, rate_minor)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(name, *line) for line in normalized],
        )
        record_audit(database, actor, "create", "Sales Order", name, after={"status": "Approved", "total_minor": total}, connection=connection)
    return SalesDocument(name, "Approved", float(minor_to_money(total)))


def create_delivery_note(
    database: Database,
    actor: Actor,
    *,
    sales_order_name: str,
    items: list[dict[str, Any]],
) -> SalesDocument:
    if not items:
        raise SalesError("delivery note requires items")
    name = database.next_document_name("SCP-DN")
    with database.transaction() as connection:
        order = connection.execute("SELECT * FROM sales_orders WHERE name = ?", (sales_order_name,)).fetchone()
        if order is None or order["status"] not in {"Approved", "Partially Delivered"}:
            raise SalesError("sales order is not deliverable")
        order_items = connection.execute("SELECT * FROM sales_order_items WHERE sales_order_name = ?", (sales_order_name,)).fetchall()
        normalized = []
        for item in items:
            code = str(item.get("item_code", ""))
            order_item = next((row for row in order_items if row["item_code"] == code), None)
            qty = float(item.get("qty", 0))
            warehouse = str(item.get("warehouse", ""))
            rate = money_to_minor(item.get("rate", 0))
            if order_item is None or qty <= 0:
                raise SalesError("delivery item is invalid")
            if order_item["delivered_qty"] + qty > order_item["qty"]:
                raise SalesError("delivery quantity would exceed sales order")
            if warehouse != order_item["warehouse"]:
                raise SalesError("delivery warehouse does not match sales order")
            normalized.append((order_item["id"], code, qty, warehouse, rate))
        connection.execute(
            """
            INSERT INTO delivery_notes (name, customer, posting_date, status, docstatus, sales_order_name, owner_identity)
            VALUES (?, ?, ?, 'Draft', 0, ?, ?)
            """,
            (name, order["customer"], date.today().isoformat(), sales_order_name, actor.identity),
        )
        connection.executemany(
            """
            INSERT INTO delivery_note_items (delivery_note_name, sales_order_item_id, item_code, qty, warehouse, rate_minor)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [(name, *line) for line in normalized],
        )
    return SalesDocument(name, "Draft")


def submit_delivery_note(database: Database, actor: Actor, name: str) -> SalesDocument:
    with database.connection() as connection:
        note = connection.execute("SELECT * FROM delivery_notes WHERE name = ?", (name,)).fetchone()
        if note is None or note["status"] != "Draft":
            raise SalesError("delivery note is not draft")
        lines = connection.execute("SELECT * FROM delivery_note_items WHERE delivery_note_name = ?", (name,)).fetchall()
    try:
        stock = create_stock_entry(
            database,
            actor,
            entry_type="Material Issue",
            posting_date=note["posting_date"],
            items=[{"item_code": line["item_code"], "source_warehouse": line["warehouse"], "qty": line["qty"], "rate": minor_to_money(line["rate_minor"])} for line in lines],
        )
        submit_stock_entry(database, actor, stock.name)
    except InventoryError as exc:
        raise SalesError(str(exc)) from exc
    with database.transaction() as connection:
        for line in lines:
            connection.execute("UPDATE sales_order_items SET delivered_qty = delivered_qty + ? WHERE id = ?", (line["qty"], line["sales_order_item_id"]))
        connection.execute("UPDATE delivery_notes SET status = 'Submitted', docstatus = 1 WHERE name = ?", (name,))
        record_audit(database, actor, "submit", "Delivery Note", name, before={"status": "Draft"}, after={"status": "Submitted"}, connection=connection)
    return SalesDocument(name, "Submitted")


def create_sales_invoice(
    database: Database,
    actor: Actor,
    *,
    delivery_note_name: str,
    items: list[dict[str, Any]],
) -> SalesDocument:
    if not items:
        raise SalesError("sales invoice requires items")
    name = database.next_document_name("SCP-SINV")
    with database.transaction() as connection:
        note = connection.execute("SELECT * FROM delivery_notes WHERE name = ?", (delivery_note_name,)).fetchone()
        if note is None or note["status"] != "Submitted":
            raise SalesError("delivery note is not submitted")
        delivery_items = connection.execute("SELECT * FROM delivery_note_items WHERE delivery_note_name = ?", (delivery_note_name,)).fetchall()
        normalized = []
        total = 0
        for item in items:
            code = str(item.get("item_code", ""))
            delivery_item = next((row for row in delivery_items if row["item_code"] == code), None)
            qty = float(item.get("qty", 0))
            rate = money_to_minor(item.get("rate", 0))
            if delivery_item is None or qty <= 0 or qty > delivery_item["qty"]:
                raise SalesError("invoice quantity would exceed delivery")
            normalized.append((delivery_item["sales_order_item_id"], code, qty, rate))
            total += int(round(qty * rate))
        connection.execute(
            """
            INSERT INTO sales_invoices
                (name, customer, posting_date, status, docstatus, total_minor,
                 outstanding_minor, delivery_note_name, owner_identity)
            VALUES (?, ?, ?, 'Draft', 0, ?, 0, ?, ?)
            """,
            (name, note["customer"], date.today().isoformat(), total, delivery_note_name, actor.identity),
        )
        connection.executemany(
            """
            INSERT INTO sales_invoice_items (sales_invoice_name, sales_order_item_id, item_code, qty, rate_minor)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(name, *line) for line in normalized],
        )
    return SalesDocument(name, "Draft", float(minor_to_money(total)), 0)


def submit_sales_invoice(database: Database, actor: Actor, name: str) -> SalesDocument:
    with database.connection() as connection:
        invoice = connection.execute("SELECT * FROM sales_invoices WHERE name = ?", (name,)).fetchone()
        if invoice is None or invoice["status"] != "Draft":
            raise SalesError("sales invoice is not draft")
    try:
        journal = create_journal_entry(
            database,
            actor,
            posting_date=invoice["posting_date"],
            remark=f"Sales Invoice {name}",
            accounts=[
                {"account": "1300 - Debtors - SCP", "debit": float(minor_to_money(invoice["total_minor"])), "credit": 0},
                {"account": "4100 - Sales - SCP", "debit": 0, "credit": float(minor_to_money(invoice["total_minor"]))},
            ],
        )
        submit_journal_entry(database, actor, journal.name)
    except AccountingError as exc:
        raise SalesError(str(exc)) from exc
    with database.transaction() as connection:
        connection.execute("UPDATE sales_invoices SET status = 'Submitted', docstatus = 1, outstanding_minor = total_minor WHERE name = ?", (name,))
        connection.execute(
            """
            INSERT OR IGNORE INTO open_items
                (reference_doctype, reference_name, party_type, party, total_minor, outstanding_minor, account)
            VALUES ('Sales Invoice', ?, 'Customer', ?, ?, ?, '1300 - Debtors - SCP')
            """,
            (name, invoice["customer"], invoice["total_minor"], invoice["total_minor"]),
        )
        for line in connection.execute("SELECT * FROM sales_invoice_items WHERE sales_invoice_name = ?", (name,)).fetchall():
            connection.execute("UPDATE sales_order_items SET billed_qty = billed_qty + ? WHERE id = ?", (line["qty"], line["sales_order_item_id"]))
        record_audit(database, actor, "submit", "Sales Invoice", name, before={"status": "Draft"}, after={"status": "Submitted"}, connection=connection)
        updated = connection.execute("SELECT * FROM sales_invoices WHERE name = ?", (name,)).fetchone()
    return SalesDocument(updated["name"], updated["status"], float(minor_to_money(updated["total_minor"])), float(minor_to_money(updated["outstanding_minor"])))
