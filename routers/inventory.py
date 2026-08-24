from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

from database import Database
from dependencies import get_actor, get_database, get_role, raise_erpnext_error
from repositories.masters import MastersRepository
from services.authorization import Actor
from services.inventory import InventoryError, cancel_stock_entry, create_stock_entry, submit_stock_entry

router = APIRouter(prefix="/api/resource")

items = [
    {
        "name": "ITEM-001",
        "doctype": "Item",
        "item_code": "ITEM-001",
        "item_name": "Office Chair",
        "description": "Ergonomic Office Chair",
        "item_group": "Finished Good",
        "stock_uom": "Nos",
        "is_stock_item": 1,
        "is_purchase_item": 1,
        "is_sales_item": 1,
        "disabled": 0,
        "standard_rate": 2500.00,
        "valuation_rate": 2200.00,
        "reorder_level": 10,
        "reorder_qty": 50,
        "image": None
    },
    {
        "name": "ITEM-002",
        "doctype": "Item",
        "item_code": "ITEM-002",
        "item_name": "Wireless Mouse",
        "description": "Optical wireless mouse",
        "item_group": "Finished Good",
        "stock_uom": "Nos",
        "is_stock_item": 1,
        "is_purchase_item": 1,
        "is_sales_item": 1,
        "disabled": 0,
        "standard_rate": 4500.00,
        "valuation_rate": 4500.00,
        "reorder_level": 50,
        "reorder_qty": 200,
        "image": None
    }
]

bins = [
    {
        "name": "ITEM-001 - Main Warehouse - C",
        "item_code": "ITEM-001",
        "warehouse": "Main Warehouse - C",
        "actual_qty": 145.0,
        "reserved_qty": 20.0,
        "ordered_qty": 50.0,
        "projected_qty": 175.0,
        "valuation_rate": 2200.00,
        "stock_value": 319000.00
    },
    {
        "name": "ITEM-002 - Main Warehouse - C",
        "item_code": "ITEM-002",
        "warehouse": "Main Warehouse - C",
        "actual_qty": 32.0,
        "reserved_qty": 5.0,
        "ordered_qty": 0.0,
        "projected_qty": 27.0,
        "valuation_rate": 4500.00,
        "stock_value": 144000.00
    }
]

purchase_orders = [
    {
        "name": "PUR-ORD-2026-00008",
        "doctype": "Purchase Order",
        "docstatus": 1,
        "naming_series": "PUR-ORD-.YYYY.-",
        "supplier": "SUP-00001",
        "supplier_name": "Acme Supplies Ltd",
        "transaction_date": "2026-05-01",
        "schedule_date": "2026-05-15",
        "currency": "LKR",
        "net_total": 110000.00,
        "grand_total": 126500.00,
        "status": "To Receive and Bill",
        "per_received": 0.0,
        "per_billed": 0.0,
        "company": "Acme Corp",
        "items": [
            {
                "item_code": "ITEM-001",
                "item_name": "Office Chair",
                "qty": 50,
                "uom": "Nos",
                "rate": 2200.00,
                "amount": 110000.00,
                "warehouse": "Main Warehouse - C",
                "received_qty": 0,
                "billed_qty": 0
            }
        ]
    }
]

@router.get("/Item")
async def list_items(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return {"data": MastersRepository(database).list_items()}


@router.get("/Item/{name}")
async def get_item(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    item = MastersRepository(database).get_item(name)
    if item is None:
        raise_erpnext_error("DoesNotExistError", f"Item {name} not found", 404)
    return {"data": item}


@router.get("/Customer")
async def list_customers(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return {"data": MastersRepository(database).list_customers()}


@router.get("/Supplier")
async def list_suppliers(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return {"data": MastersRepository(database).list_suppliers()}


@router.get("/Item Group")
async def list_item_groups(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return {"data": MastersRepository(database).list_item_groups()}


@router.get("/UOM")
async def list_uoms(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return {"data": MastersRepository(database).list_uoms()}


@router.get("/Warehouse")
async def list_warehouses(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return {"data": MastersRepository(database).list_warehouses()}

@router.get("/Bin")
async def list_bins(
    request: Request,
    database: Database = Depends(get_database),
    actor: Actor = Depends(get_actor),
) -> dict[str, list[dict[str, object]]]:
    item_code = None
    filters = request.query_params.get("filters")
    if filters:
        try:
            filter_list = json.loads(filters)
            if filter_list and len(filter_list) > 0:
                condition = filter_list[0]
                if len(condition) >= 4 and condition[1] == "item_code" and condition[2] == "=":
                    item_code = condition[3]
        except (TypeError, ValueError):
            pass
    with database.connection() as connection:
        if item_code:
            rows = connection.execute(
                "SELECT * FROM bins WHERE item_code = ? ORDER BY warehouse", (item_code,)
            ).fetchall()
        else:
            rows = connection.execute("SELECT * FROM bins ORDER BY item_code, warehouse").fetchall()
    return {
        "data": [
            {
                "name": f"{row['item_code']} - {row['warehouse']}",
                "item_code": row["item_code"],
                "warehouse": row["warehouse"],
                "actual_qty": row["actual_qty"],
                "reserved_qty": row["reserved_qty"],
                "ordered_qty": row["ordered_qty"],
                "projected_qty": row["actual_qty"] - row["reserved_qty"] + row["ordered_qty"],
                "valuation_rate": row["valuation_rate_minor"] / 100,
                "stock_value": row["stock_value_minor"] / 100,
            }
            for row in rows
        ]
    }


@router.get("/Stock Entry")
async def list_stock_entries(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    with database.connection() as connection:
        entries = connection.execute("SELECT * FROM stock_entries ORDER BY posting_date, name").fetchall()
    return {"data": [{"name": row["name"], "stock_entry_type": row["entry_type"], "posting_date": row["posting_date"], "status": row["status"]} for row in entries]}


@router.post("/Stock Entry", status_code=201)
async def create_stock_entry_route(
    data: dict[str, Any],
    database: Database = Depends(get_database),
    actor: Actor = Depends(get_actor),
) -> dict[str, dict[str, object]]:
    try:
        entry = create_stock_entry(
            database,
            actor,
            entry_type=str(data.get("stock_entry_type", "")),
            posting_date=str(data.get("posting_date", "")),
            items=data.get("items") or [],
        )
    except InventoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"data": entry.as_dict()}


@router.post("/Stock Entry/{name}/submit")
async def submit_stock_entry_route(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        entry = submit_stock_entry(database, actor, name)
    except InventoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"data": entry.as_dict()}


@router.post("/Stock Entry/{name}/cancel")
async def cancel_stock_entry_route(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        entry = cancel_stock_entry(database, actor, name)
    except InventoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"data": entry.as_dict()}

@router.get("/Purchase Order")
async def list_purchase_orders(role: str = Depends(get_role)):
    return {"data": purchase_orders}
