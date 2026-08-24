from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from database import Database
from services.audit import record_audit
from services.authorization import Actor
from services.inventory import InventoryError, create_stock_entry, submit_stock_entry


class ManufacturingError(ValueError):
    """Raised when a production order violates its active BOM."""


@dataclass(frozen=True)
class ProductionOrder:
    name: str
    item_code: str
    qty: float
    status: str



def create_production_order(
    database: Database,
    actor: Actor,
    *,
    item_code: str,
    qty: float,
    source_warehouse: str,
    target_warehouse: str,
) -> ProductionOrder:
    if qty <= 0:
        raise ManufacturingError("production quantity must be positive")
    name = database.next_document_name("SCP-PROD")
    with database.transaction() as connection:
        bom = connection.execute(
            "SELECT * FROM boms WHERE item_code = ? AND is_active = 1", (item_code,)
        ).fetchone()
        if bom is None:
            raise ManufacturingError("active BOM was not found")
        if connection.execute("SELECT 1 FROM warehouses WHERE name = ?", (source_warehouse,)).fetchone() is None:
            raise ManufacturingError("source warehouse was not found")
        if connection.execute("SELECT 1 FROM warehouses WHERE name = ?", (target_warehouse,)).fetchone() is None:
            raise ManufacturingError("target warehouse was not found")
        bom_items = connection.execute("SELECT * FROM bom_items WHERE bom_name = ?", (bom["name"],)).fetchall()
        if not bom_items:
            raise ManufacturingError("BOM has no components")
        connection.execute(
            """
            INSERT INTO production_orders
                (name, item_code, bom_name, qty, source_warehouse,
                 target_warehouse, status, docstatus, owner_identity)
            VALUES (?, ?, ?, ?, ?, ?, 'Draft', 0, ?)
            """,
            (name, item_code, bom["name"], qty, source_warehouse, target_warehouse, actor.identity),
        )
        connection.executemany(
            """
            INSERT INTO production_order_items
                (production_order_name, item_code, qty)
            VALUES (?, ?, ?)
            """,
            [(name, component["item_code"], component["qty"] * qty / bom["quantity"]) for component in bom_items],
        )
        record_audit(database, actor, "create", "Production Order", name, after={"status": "Draft", "item": item_code, "qty": qty}, connection=connection)
    return ProductionOrder(name, item_code, qty, "Draft")


def submit_production_order(
    database: Database, actor: Actor, name: str
) -> ProductionOrder:
    with database.connection() as connection:
        order = connection.execute("SELECT * FROM production_orders WHERE name = ?", (name,)).fetchone()
        if order is None or order["status"] != "Draft":
            raise ManufacturingError("production order is not draft")
        components = connection.execute("SELECT * FROM production_order_items WHERE production_order_name = ?", (name,)).fetchall()
    try:
        consumption = create_stock_entry(
            database,
            actor,
            entry_type="Manufacturing Consumption",
            posting_date=date.today().isoformat(),
            items=[{"item_code": component["item_code"], "source_warehouse": order["source_warehouse"], "qty": component["qty"], "rate": "1.00"} for component in components],
        )
        submit_stock_entry(database, actor, consumption.name)
        receipt = create_stock_entry(
            database,
            actor,
            entry_type="Manufacturing Receipt",
            posting_date=date.today().isoformat(),
            items=[{"item_code": order["item_code"], "target_warehouse": order["target_warehouse"], "qty": order["qty"], "rate": "1.00"}],
        )
        submit_stock_entry(database, actor, receipt.name)
    except InventoryError as exc:
        raise ManufacturingError(str(exc)) from exc
    with database.transaction() as connection:
        connection.execute("UPDATE production_orders SET status = 'Completed', docstatus = 1 WHERE name = ?", (name,))
        connection.execute("UPDATE production_order_items SET consumed_qty = qty, produced_qty = ? WHERE production_order_name = ?", (order["qty"], name))
        record_audit(database, actor, "complete", "Production Order", name, before={"status": "Draft"}, after={"status": "Completed"}, connection=connection)
    return ProductionOrder(order["name"], order["item_code"], order["qty"], "Completed")
