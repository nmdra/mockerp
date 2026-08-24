from __future__ import annotations

from typing import Any

from database import Database


def trial_balance(database: Database) -> list[dict[str, object]]:
    with database.connection() as connection:
        rows = connection.execute(
            """
            SELECT accounts.name,
                   COALESCE(SUM(gl_entries.debit_minor), 0) AS debit_minor,
                   COALESCE(SUM(gl_entries.credit_minor), 0) AS credit_minor
            FROM accounts
            LEFT JOIN gl_entries ON gl_entries.account = accounts.name
            GROUP BY accounts.name
            ORDER BY accounts.name
            """
        ).fetchall()
    return [
        {
            "account": row["name"],
            "debit": row["debit_minor"] / 100,
            "credit": row["credit_minor"] / 100,
            "balance": (row["debit_minor"] - row["credit_minor"]) / 100,
        }
        for row in rows
    ]


def stock_summary(database: Database) -> list[dict[str, object]]:
    with database.connection() as connection:
        rows = connection.execute(
            """
            SELECT item_code, warehouse, actual_qty, reserved_qty, ordered_qty,
                   valuation_rate_minor, stock_value_minor
            FROM bins ORDER BY item_code, warehouse
            """
        ).fetchall()
    return [
        {
            "item_code": row["item_code"],
            "warehouse": row["warehouse"],
            "actual_qty": row["actual_qty"],
            "reserved_qty": row["reserved_qty"],
            "ordered_qty": row["ordered_qty"],
            "stock_value": row["stock_value_minor"] / 100,
        }
        for row in rows
    ]


def ar_ap_summary(database: Database) -> list[dict[str, object]]:
    with database.connection() as connection:
        rows = connection.execute(
            """
            SELECT party_type, party,
                   SUM(total_minor) AS total_minor,
                   SUM(outstanding_minor) AS outstanding_minor
            FROM open_items
            GROUP BY party_type, party
            ORDER BY party_type, party
            """
        ).fetchall()
    return [
        {
            "party_type": row["party_type"],
            "party": row["party"],
            "total": row["total_minor"] / 100,
            "outstanding": row["outstanding_minor"] / 100,
        }
        for row in rows
    ]


def attendance_leave_summary(database: Database) -> dict[str, object]:
    with database.connection() as connection:
        attendance = connection.execute(
            "SELECT status, COUNT(*) AS count FROM attendance GROUP BY status ORDER BY status"
        ).fetchall()
        leaves = connection.execute(
            "SELECT status, COUNT(*) AS count FROM leave_applications GROUP BY status ORDER BY status"
        ).fetchall()
    return {
        "attendance": {row["status"]: row["count"] for row in attendance},
        "leave_applications": {row["status"]: row["count"] for row in leaves},
    }


def sales_fulfillment(database: Database) -> list[dict[str, object]]:
    with database.connection() as connection:
        rows = connection.execute(
            """
            SELECT sales_orders.name, sales_orders.customer, sales_orders.status,
                   sales_order_items.item_code, sales_order_items.qty,
                   sales_order_items.delivered_qty, sales_order_items.billed_qty
            FROM sales_orders JOIN sales_order_items
              ON sales_order_items.sales_order_name = sales_orders.name
            ORDER BY sales_orders.name, sales_order_items.id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def purchasing_status(database: Database) -> list[dict[str, object]]:
    with database.connection() as connection:
        rows = connection.execute(
            "SELECT name, supplier, status, total_minor FROM purchase_orders ORDER BY name"
        ).fetchall()
    return [
        {"name": row["name"], "supplier": row["supplier"], "status": row["status"], "total": row["total_minor"] / 100}
        for row in rows
    ]


def production_consumption(database: Database) -> list[dict[str, object]]:
    with database.connection() as connection:
        rows = connection.execute(
            """
            SELECT production_orders.name, production_orders.item_code,
                   production_orders.qty, production_orders.status,
                   production_order_items.item_code AS component,
                   production_order_items.qty AS component_qty,
                   production_order_items.consumed_qty,
                   production_order_items.produced_qty
            FROM production_orders JOIN production_order_items
              ON production_order_items.production_order_name = production_orders.name
            ORDER BY production_orders.name, production_order_items.id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def asset_summary(database: Database) -> list[dict[str, object]]:
    with database.connection() as connection:
        rows = connection.execute(
            """
            SELECT category, status, COUNT(*) AS count,
                   SUM(acquisition_cost_minor) AS cost_minor,
                   SUM(accumulated_depreciation_minor) AS depreciation_minor
            FROM assets GROUP BY category, status ORDER BY category, status
            """
        ).fetchall()
    return [
        {
            "category": row["category"],
            "status": row["status"],
            "count": row["count"],
            "acquisition_cost": row["cost_minor"] / 100,
            "accumulated_depreciation": row["depreciation_minor"] / 100,
        }
        for row in rows
    ]


def audit_events(
    database: Database,
    *,
    limit: int = 50,
    offset: int = 0,
    action: str | None = None,
    resource_type: str | None = None,
) -> tuple[list[dict[str, object]], int]:
    safe_limit = max(1, min(limit, 100))
    safe_offset = max(offset, 0)
    clauses: list[str] = []
    parameters: list[Any] = []
    if action:
        clauses.append("action = ?")
        parameters.append(action)
    if resource_type:
        clauses.append("resource_type = ?")
        parameters.append(resource_type)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with database.connection() as connection:
        total = connection.execute(f"SELECT COUNT(*) FROM audit_events {where}", parameters).fetchone()[0]
        rows = connection.execute(
            f"""
            SELECT id, actor_identity, action, resource_type, resource_id,
                   before_json, after_json, created_at
            FROM audit_events {where} ORDER BY id LIMIT ? OFFSET ?
            """,
            [*parameters, safe_limit, safe_offset],
        ).fetchall()
    import json

    return [
        {
            "name": f"AUDIT-{row['id']:05d}",
            "actor_identity": row["actor_identity"],
            "action": row["action"],
            "resource_type": row["resource_type"],
            "resource_id": row["resource_id"],
            "before": json.loads(row["before_json"]) if row["before_json"] else None,
            "after": json.loads(row["after_json"]) if row["after_json"] else None,
            "created_at": row["created_at"],
        }
        for row in rows
    ], total
