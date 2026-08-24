from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import sqlite3
from typing import Any

from database import Database
from services.accounting import money_to_minor, minor_to_money
from services.audit import record_audit
from services.authorization import Actor


class InventoryError(ValueError):
    """Raised when a stock transaction violates inventory policy."""


_ENTRY_TYPES = {
    "Material Receipt",
    "Material Issue",
    "Material Transfer",
    "Manufacturing Consumption",
    "Manufacturing Receipt",
    "Stock Adjustment",
}


@dataclass(frozen=True)
class StockEntry:
    name: str
    entry_type: str
    posting_date: str
    status: str
    items: tuple[dict[str, object], ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "doctype": "Stock Entry",
            "stock_entry_type": self.entry_type,
            "posting_date": self.posting_date,
            "status": self.status,
            "docstatus": 1 if self.status == "Submitted" else 2 if self.status == "Cancelled" else 0,
            "items": list(self.items),
        }


def _from_row(connection: sqlite3.Connection, row: sqlite3.Row) -> StockEntry:
    lines = connection.execute(
        """
        SELECT item_code, source_warehouse, target_warehouse, qty, rate_minor, batch_no
        FROM stock_entry_items WHERE stock_entry_name = ? ORDER BY id
        """,
        (row["name"],),
    ).fetchall()
    return StockEntry(
        row["name"],
        row["entry_type"],
        row["posting_date"],
        row["status"],
        tuple(
            {
                "item_code": line["item_code"],
                "source_warehouse": line["source_warehouse"],
                "target_warehouse": line["target_warehouse"],
                "qty": line["qty"],
                "rate": float(minor_to_money(line["rate_minor"])),
                "batch_no": line["batch_no"],
            }
            for line in lines
        ),
    )


def _warehouse_ok(
    connection: sqlite3.Connection, item: str, warehouse: str, direction: str
) -> bool:
    return connection.execute(
        """
        SELECT 1 FROM item_warehouse_eligibility
        WHERE item_code = ? AND warehouse = ? AND direction = ?
        """,
        (item, warehouse, direction),
    ).fetchone() is not None


def create_stock_entry(
    database: Database,
    actor: Actor,
    *,
    entry_type: str,
    posting_date: str,
    items: list[dict[str, Any]],
) -> StockEntry:
    if entry_type not in _ENTRY_TYPES:
        raise InventoryError("unsupported stock entry type")
    if not items:
        raise InventoryError("stock entry requires items")
    try:
        date.fromisoformat(posting_date)
    except ValueError as exc:
        raise InventoryError("posting_date must be an ISO date") from exc
    name = database.next_document_name("SCP-STE")
    normalized: list[tuple[str, str | None, str | None, float, int, str | None]] = []
    with database.transaction() as connection:
        for item in items:
            item_code = str(item.get("item_code", ""))
            source = item.get("source_warehouse")
            target = item.get("target_warehouse")
            source_name = str(source) if source else None
            target_name = str(target) if target else None
            try:
                qty = float(item.get("qty", 0))
                rate_minor = money_to_minor(item.get("rate", 0))
            except (TypeError, ValueError) as exc:
                raise InventoryError("stock quantity and rate must be numeric") from exc
            if qty <= 0 or rate_minor < 0:
                raise InventoryError("stock quantity must be positive")
            if connection.execute("SELECT 1 FROM items WHERE name = ?", (item_code,)).fetchone() is None:
                raise InventoryError("item was not found")
            if source_name and connection.execute("SELECT 1 FROM warehouses WHERE name = ?", (source_name,)).fetchone() is None:
                raise InventoryError("source warehouse was not found")
            if target_name and connection.execute("SELECT 1 FROM warehouses WHERE name = ?", (target_name,)).fetchone() is None:
                raise InventoryError("target warehouse was not found")
            if entry_type in {"Material Receipt", "Manufacturing Receipt"} and not target_name:
                raise InventoryError("receipt requires a target warehouse")
            if entry_type in {"Material Issue", "Manufacturing Consumption"} and not source_name:
                raise InventoryError("issue requires a source warehouse")
            if entry_type == "Material Transfer" and (not source_name or not target_name):
                raise InventoryError("transfer requires source and target warehouses")
            if source_name and entry_type != "Material Receipt" and not _warehouse_ok(connection, item_code, source_name, "source"):
                raise InventoryError("source warehouse is not eligible for this item")
            if target_name and entry_type != "Material Issue" and not _warehouse_ok(connection, item_code, target_name, "target"):
                raise InventoryError("target warehouse is not eligible for this item")
            normalized.append((item_code, source_name, target_name, qty, rate_minor, item.get("batch_no")))
        connection.execute(
            """
            INSERT INTO stock_entries (name, entry_type, posting_date, status, docstatus, owner_identity)
            VALUES (?, ?, ?, 'Draft', 0, ?)
            """,
            (name, entry_type, posting_date, actor.identity),
        )
        connection.executemany(
            """
            INSERT INTO stock_entry_items
                (stock_entry_name, item_code, source_warehouse, target_warehouse, qty, rate_minor, batch_no)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [(name, *line) for line in normalized],
        )
        return _from_row(connection, connection.execute("SELECT * FROM stock_entries WHERE name = ?", (name,)).fetchone())


def _apply_delta(
    connection: sqlite3.Connection,
    *,
    entry_name: str,
    item_code: str,
    warehouse: str,
    delta: float,
    rate_minor: int,
    posting_date: str,
    is_reversal: int,
) -> None:
    bin_row = connection.execute(
        "SELECT * FROM bins WHERE item_code = ? AND warehouse = ?",
        (item_code, warehouse),
    ).fetchone()
    current = float(bin_row["actual_qty"]) if bin_row else 0.0
    updated = round(current + delta, 6)
    if updated < -1e-9:
        raise InventoryError("stock transaction would create negative stock")
    stock_delta = int(round(delta * rate_minor))
    if bin_row:
        connection.execute(
            """
            UPDATE bins SET actual_qty = ?, valuation_rate_minor = ?, stock_value_minor = ?
            WHERE item_code = ? AND warehouse = ?
            """,
            (
                max(updated, 0),
                rate_minor,
                max(0, int(round((max(updated, 0)) * rate_minor))),
                item_code,
                warehouse,
            ),
        )
    else:
        connection.execute(
            """
            INSERT INTO bins
                (item_code, warehouse, actual_qty, reserved_qty, ordered_qty,
                 valuation_rate_minor, stock_value_minor)
            VALUES (?, ?, ?, 0, 0, ?, ?)
            """,
            (item_code, warehouse, max(updated, 0), rate_minor, max(0, int(round(updated * rate_minor)))),
        )
    connection.execute(
        """
        INSERT INTO stock_ledger_entries
            (stock_entry_name, item_code, warehouse, posting_date,
             actual_qty_delta, qty_after_transaction, valuation_rate_minor,
             stock_value_delta_minor, is_reversal)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (entry_name, item_code, warehouse, posting_date, delta, max(updated, 0), rate_minor, stock_delta, is_reversal),
    )


def submit_stock_entry(
    database: Database, actor: Actor, name: str
) -> StockEntry:
    with database.transaction() as connection:
        row = connection.execute("SELECT * FROM stock_entries WHERE name = ?", (name,)).fetchone()
        if row is None or row["status"] != "Draft":
            raise InventoryError("only draft stock entries can be submitted")
        lines = connection.execute("SELECT * FROM stock_entry_items WHERE stock_entry_name = ? ORDER BY id", (name,)).fetchall()
        for line in lines:
            if line["source_warehouse"]:
                _apply_delta(
                    connection,
                    entry_name=name,
                    item_code=line["item_code"],
                    warehouse=line["source_warehouse"],
                    delta=-line["qty"],
                    rate_minor=line["rate_minor"],
                    posting_date=row["posting_date"],
                    is_reversal=0,
                )
            if line["target_warehouse"]:
                _apply_delta(
                    connection,
                    entry_name=name,
                    item_code=line["item_code"],
                    warehouse=line["target_warehouse"],
                    delta=line["qty"],
                    rate_minor=line["rate_minor"],
                    posting_date=row["posting_date"],
                    is_reversal=0,
                )
        connection.execute("UPDATE stock_entries SET status = 'Submitted', docstatus = 1 WHERE name = ?", (name,))
        record_audit(database, actor, "submit", "Stock Entry", name, before={"status": "Draft"}, after={"status": "Submitted"}, connection=connection)
        return _from_row(connection, connection.execute("SELECT * FROM stock_entries WHERE name = ?", (name,)).fetchone())


def cancel_stock_entry(
    database: Database, actor: Actor, name: str
) -> StockEntry:
    with database.transaction() as connection:
        row = connection.execute("SELECT * FROM stock_entries WHERE name = ?", (name,)).fetchone()
        if row is None or row["status"] != "Submitted":
            raise InventoryError("only submitted stock entries can be cancelled")
        ledger = connection.execute(
            "SELECT * FROM stock_ledger_entries WHERE stock_entry_name = ? AND is_reversal = 0 ORDER BY id DESC",
            (name,),
        ).fetchall()
        for entry in ledger:
            _apply_delta(
                connection,
                entry_name=name,
                item_code=entry["item_code"],
                warehouse=entry["warehouse"],
                delta=-entry["actual_qty_delta"],
                rate_minor=entry["valuation_rate_minor"],
                posting_date=row["posting_date"],
                is_reversal=1,
            )
        connection.execute("UPDATE stock_entries SET status = 'Cancelled', docstatus = 2 WHERE name = ?", (name,))
        record_audit(database, actor, "cancel", "Stock Entry", name, before={"status": "Submitted"}, after={"status": "Cancelled"}, connection=connection)
        return _from_row(connection, connection.execute("SELECT * FROM stock_entries WHERE name = ?", (name,)).fetchone())
