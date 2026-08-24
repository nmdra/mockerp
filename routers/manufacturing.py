from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from database import Database
from dependencies import get_actor, get_database
from services.authorization import Actor
from services.manufacturing import ManufacturingError, create_production_order, submit_production_order

router = APIRouter(prefix="/api/resource")


def _error(exc: ManufacturingError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


@router.get("/BOM")
async def list_boms(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    with database.connection() as connection:
        rows = connection.execute("SELECT * FROM boms ORDER BY name").fetchall()
        return {"data": [{"name": row["name"], "item": row["item_code"], "quantity": row["quantity"], "is_active": row["is_active"]} for row in rows]}


@router.get("/Production Order")
async def list_production_orders(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    with database.connection() as connection:
        rows = connection.execute("SELECT * FROM production_orders ORDER BY name").fetchall()
        return {"data": [dict(row) for row in rows]}


@router.post("/Production Order", status_code=201)
async def create_production_order_route(
    data: dict[str, Any], database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        order = create_production_order(
            database,
            actor,
            item_code=str(data.get("item_code", "")),
            qty=float(data.get("qty", 0)),
            source_warehouse=str(data.get("source_warehouse", "")),
            target_warehouse=str(data.get("target_warehouse", "")),
        )
    except ManufacturingError as exc:
        raise _error(exc) from exc
    return {"data": {"name": order.name, "item_code": order.item_code, "qty": order.qty, "status": order.status}}


@router.post("/Production Order/{name}/submit")
async def submit_production_order_route(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        order = submit_production_order(database, actor, name)
    except ManufacturingError as exc:
        raise _error(exc) from exc
    return {"data": {"name": order.name, "item_code": order.item_code, "qty": order.qty, "status": order.status}}
