from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import sqlite3
from typing import Any

from database import Database
from services.accounting import (
    AccountingError,
    create_journal_entry,
    minor_to_money,
    money_to_minor,
    submit_journal_entry,
)
from services.audit import record_audit
from services.authorization import Actor
from services.inventory import InventoryError, create_stock_entry, submit_stock_entry
from services.workflow import WorkflowError, approve_request, create_approval_request


class PurchasingError(ValueError):
    """Raised when a source document cannot advance through procure-to-pay."""


@dataclass(frozen=True)
class MaterialRequest:
    name: str
    status: str


@dataclass(frozen=True)
class PurchaseOrder:
    name: str
    status: str
    total: float


@dataclass(frozen=True)
class PurchaseReceipt:
    name: str
    status: str


@dataclass(frozen=True)
class PurchaseInvoice:
    name: str
    status: str
    total: float
    outstanding: float


def _require_item(connection: sqlite3.Connection, item: str, warehouse: str) -> None:
    if connection.execute("SELECT 1 FROM items WHERE name = ?", (item,)).fetchone() is None:
        raise PurchasingError("item was not found")
    if connection.execute("SELECT 1 FROM warehouses WHERE name = ?", (warehouse,)).fetchone() is None:
        raise PurchasingError("warehouse was not found")


def create_material_request(
    database: Database,
    actor: Actor,
    *,
    posting_date: str,
    items: list[dict[str, Any]],
) -> MaterialRequest:
    if not items:
        raise PurchasingError("material request requires items")
    name = database.next_document_name("SCP-MR")
    with database.transaction() as connection:
        normalized = []
        for item in items:
            code = str(item.get("item_code", ""))
            warehouse = str(item.get("warehouse", ""))
            qty = float(item.get("qty", 0))
            if qty <= 0:
                raise PurchasingError("material request quantity must be positive")
            _require_item(connection, code, warehouse)
            normalized.append((code, qty, warehouse))
        connection.execute(
            """
            INSERT INTO material_requests
                (name, posting_date, status, docstatus, requester_identity)
            VALUES (?, ?, 'Draft', 0, ?)
            """,
            (name, posting_date, actor.identity),
        )
        connection.executemany(
            """
            INSERT INTO material_request_items (request_name, item_code, qty, warehouse)
            VALUES (?, ?, ?, ?)
            """,
            [(name, code, qty, warehouse) for code, qty, warehouse in normalized],
        )
        record_audit(database, actor, "create", "Material Request", name, after={"status": "Draft"}, connection=connection)
    return MaterialRequest(name, "Draft")


def create_purchase_order(
    database: Database,
    actor: Actor,
    *,
    material_request_name: str,
    supplier: str,
    transaction_date: str,
    items: list[dict[str, Any]],
) -> PurchaseOrder:
    if not items:
        raise PurchasingError("purchase order requires items")
    with database.connection() as connection:
        request = connection.execute("SELECT * FROM material_requests WHERE name = ?", (material_request_name,)).fetchone()
        supplier_row = connection.execute("SELECT 1 FROM suppliers WHERE name = ?", (supplier,)).fetchone()
    if request is None:
        raise PurchasingError("material request was not found")
    if supplier_row is None:
        raise PurchasingError("supplier was not found")
    name = database.next_document_name("SCP-PO")
    normalized = []
    total = 0
    with database.connection() as connection:
        request_items = connection.execute(
            "SELECT * FROM material_request_items WHERE request_name = ?",
            (material_request_name,),
        ).fetchall()
        for item in items:
            code = str(item.get("item_code", ""))
            qty = float(item.get("qty", 0))
            warehouse = str(item.get("warehouse", ""))
            rate = money_to_minor(item.get("rate", 0))
            if qty <= 0 or rate < 0:
                raise PurchasingError("purchase order quantity and rate are invalid")
            _require_item(connection, code, warehouse)
            request_item = next((row for row in request_items if row["item_code"] == code), None)
            if request_item is None or qty > request_item["qty"]:
                raise PurchasingError("purchase order exceeds material request")
            normalized.append((request_item["id"], code, qty, warehouse, rate))
            total += int(round(qty * rate))
    try:
        approval = create_approval_request(
            database,
            actor,
            document_type="Purchase Order",
            reference_name=name,
            amount=minor_to_money(total),
        )
    except WorkflowError as exc:
        raise PurchasingError(str(exc)) from exc
    status = "Pending Approval" if approval.status == "PENDING_APPROVAL" else "Approved"
    with database.transaction() as connection:
        connection.execute(
            """
            INSERT INTO purchase_orders
                (name, supplier, transaction_date, status, docstatus,
                 total_minor, requester_identity, approval_request_id, material_request_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (name, supplier, transaction_date, status, 1 if status == "Approved" else 0, total, actor.identity, approval.id, material_request_name),
        )
        connection.executemany(
            """
            INSERT INTO purchase_order_items
                (purchase_order_name, material_request_item_id, item_code, qty, warehouse, rate_minor)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [(name, *line) for line in normalized],
        )
        connection.execute("UPDATE material_requests SET status = 'Approved', docstatus = 1 WHERE name = ?", (material_request_name,))
        record_audit(database, actor, "create", "Purchase Order", name, after={"status": status, "total_minor": total}, connection=connection)
    return PurchaseOrder(name, status, float(minor_to_money(total)))


def approve_purchase_order(
    database: Database, actor: Actor, name: str
) -> PurchaseOrder:
    with database.connection() as connection:
        row = connection.execute("SELECT * FROM purchase_orders WHERE name = ?", (name,)).fetchone()
    if row is None or row["status"] != "Pending Approval":
        raise PurchasingError("purchase order is not pending approval")
    try:
        approval = approve_request(database, actor, row["approval_request_id"])
    except WorkflowError as exc:
        raise PurchasingError(str(exc)) from exc
    status = "Approved" if approval.status == "APPROVED" else "Pending Approval"
    with database.transaction() as connection:
        connection.execute("UPDATE purchase_orders SET status = ?, docstatus = ? WHERE name = ?", (status, 1 if status == "Approved" else 0, name))
        record_audit(database, actor, "approve", "Purchase Order", name, before={"status": row["status"]}, after={"status": status}, connection=connection)
        updated = connection.execute("SELECT * FROM purchase_orders WHERE name = ?", (name,)).fetchone()
    return PurchaseOrder(updated["name"], updated["status"], float(minor_to_money(updated["total_minor"])))


def create_purchase_receipt(
    database: Database,
    actor: Actor,
    *,
    purchase_order_name: str,
    items: list[dict[str, Any]],
) -> PurchaseReceipt:
    if not items:
        raise PurchasingError("purchase receipt requires items")
    name = database.next_document_name("SCP-PR")
    with database.transaction() as connection:
        order = connection.execute("SELECT * FROM purchase_orders WHERE name = ?", (purchase_order_name,)).fetchone()
        if order is None or order["status"] != "Approved":
            raise PurchasingError("purchase order is not approved")
        order_items = connection.execute("SELECT * FROM purchase_order_items WHERE purchase_order_name = ?", (purchase_order_name,)).fetchall()
        normalized = []
        for item in items:
            code = str(item.get("item_code", ""))
            order_item = next((row for row in order_items if row["item_code"] == code), None)
            qty = float(item.get("qty", 0))
            warehouse = str(item.get("warehouse", ""))
            rate = money_to_minor(item.get("rate", 0))
            if order_item is None or qty <= 0:
                raise PurchasingError("purchase receipt item is invalid")
            if order_item["received_qty"] + qty > order_item["qty"]:
                raise PurchasingError("receipt quantity would exceed purchase order")
            if warehouse != order_item["warehouse"]:
                raise PurchasingError("receipt warehouse does not match purchase order")
            normalized.append((order_item["id"], code, qty, warehouse, rate))
        connection.execute(
            """
            INSERT INTO purchase_receipts
                (name, supplier, posting_date, status, docstatus, purchase_order_name, owner_identity)
            VALUES (?, ?, ?, 'Draft', 0, ?, ?)
            """,
            (name, order["supplier"], date.today().isoformat(), purchase_order_name, actor.identity),
        )
        connection.executemany(
            """
            INSERT INTO purchase_receipt_items
                (receipt_name, purchase_order_item_id, item_code, qty, warehouse, rate_minor)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [(name, *line) for line in normalized],
        )
    return PurchaseReceipt(name, "Draft")


def submit_purchase_receipt(
    database: Database, actor: Actor, name: str
) -> PurchaseReceipt:
    with database.connection() as connection:
        receipt = connection.execute("SELECT * FROM purchase_receipts WHERE name = ?", (name,)).fetchone()
        if receipt is None or receipt["status"] != "Draft":
            raise PurchasingError("purchase receipt is not draft")
        lines = connection.execute("SELECT * FROM purchase_receipt_items WHERE receipt_name = ?", (name,)).fetchall()
    try:
        stock = create_stock_entry(
            database,
            actor,
            entry_type="Material Receipt",
            posting_date=receipt["posting_date"],
            items=[{"item_code": line["item_code"], "target_warehouse": line["warehouse"], "qty": line["qty"], "rate": minor_to_money(line["rate_minor"])} for line in lines],
        )
        submit_stock_entry(database, actor, stock.name)
    except InventoryError as exc:
        raise PurchasingError(str(exc)) from exc
    with database.transaction() as connection:
        for line in lines:
            connection.execute("UPDATE purchase_order_items SET received_qty = received_qty + ? WHERE id = ?", (line["qty"], line["purchase_order_item_id"]))
        connection.execute("UPDATE purchase_receipts SET status = 'Submitted', docstatus = 1 WHERE name = ?", (name,))
        record_audit(database, actor, "submit", "Purchase Receipt", name, before={"status": "Draft"}, after={"status": "Submitted"}, connection=connection)
    return PurchaseReceipt(name, "Submitted")


def create_purchase_invoice(
    database: Database,
    actor: Actor,
    *,
    purchase_receipt_name: str,
    items: list[dict[str, Any]],
) -> PurchaseInvoice:
    if not items:
        raise PurchasingError("purchase invoice requires items")
    name = database.next_document_name("SCP-PINV")
    with database.transaction() as connection:
        receipt = connection.execute("SELECT * FROM purchase_receipts WHERE name = ?", (purchase_receipt_name,)).fetchone()
        if receipt is None or receipt["status"] != "Submitted":
            raise PurchasingError("purchase receipt is not submitted")
        receipt_items = connection.execute("SELECT * FROM purchase_receipt_items WHERE receipt_name = ?", (purchase_receipt_name,)).fetchall()
        normalized = []
        total = 0
        for item in items:
            code = str(item.get("item_code", ""))
            receipt_item = next((row for row in receipt_items if row["item_code"] == code), None)
            qty = float(item.get("qty", 0))
            rate = money_to_minor(item.get("rate", 0))
            if receipt_item is None or qty <= 0 or qty > receipt_item["qty"]:
                raise PurchasingError("invoice quantity would exceed receipt")
            normalized.append((receipt_item["purchase_order_item_id"], code, qty, rate))
            total += int(round(qty * rate))
        connection.execute(
            """
            INSERT INTO purchase_invoices
                (name, supplier, posting_date, status, docstatus,
                 total_minor, outstanding_minor, purchase_receipt_name, owner_identity)
            VALUES (?, ?, ?, 'Draft', 0, ?, 0, ?, ?)
            """,
            (name, receipt["supplier"], date.today().isoformat(), total, purchase_receipt_name, actor.identity),
        )
        connection.executemany(
            """
            INSERT INTO purchase_invoice_items
                (invoice_name, purchase_order_item_id, item_code, qty, rate_minor)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(name, *line) for line in normalized],
        )
    return PurchaseInvoice(name, "Draft", float(minor_to_money(total)), 0)


def submit_purchase_invoice(
    database: Database, actor: Actor, name: str
) -> PurchaseInvoice:
    with database.connection() as connection:
        invoice = connection.execute("SELECT * FROM purchase_invoices WHERE name = ?", (name,)).fetchone()
        if invoice is None or invoice["status"] != "Draft":
            raise PurchasingError("purchase invoice is not draft")
    try:
        journal = create_journal_entry(
            database,
            actor,
            posting_date=invoice["posting_date"],
            remark=f"Purchase Invoice {name}",
            accounts=[
                {"account": "5100 - COGS - SCP", "debit": float(minor_to_money(invoice["total_minor"])), "credit": 0},
                {"account": "2100 - Creditors - SCP", "debit": 0, "credit": float(minor_to_money(invoice["total_minor"]))},
            ],
        )
        submit_journal_entry(database, actor, journal.name)
    except AccountingError as exc:
        raise PurchasingError(str(exc)) from exc
    with database.transaction() as connection:
        connection.execute("UPDATE purchase_invoices SET status = 'Submitted', docstatus = 1, outstanding_minor = total_minor WHERE name = ?", (name,))
        connection.execute(
            """
            INSERT OR IGNORE INTO open_items
                (reference_doctype, reference_name, party_type, party,
                 total_minor, outstanding_minor, account)
            VALUES ('Purchase Invoice', ?, 'Supplier', ?, ?, ?, '2100 - Creditors - SCP')
            """,
            (name, invoice["supplier"], invoice["total_minor"], invoice["total_minor"]),
        )
        for line in connection.execute("SELECT * FROM purchase_invoice_items WHERE invoice_name = ?", (name,)).fetchall():
            connection.execute("UPDATE purchase_order_items SET billed_qty = billed_qty + ? WHERE id = ?", (line["qty"], line["purchase_order_item_id"]))
        record_audit(database, actor, "submit", "Purchase Invoice", name, before={"status": "Draft"}, after={"status": "Submitted"}, connection=connection)
        updated = connection.execute("SELECT * FROM purchase_invoices WHERE name = ?", (name,)).fetchone()
    return PurchaseInvoice(updated["name"], updated["status"], float(minor_to_money(updated["total_minor"])), float(minor_to_money(updated["outstanding_minor"])))
