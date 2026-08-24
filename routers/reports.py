from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from database import Database
from dependencies import get_actor, get_database
from services.authorization import Actor
from services.reports import (
    ar_ap_summary,
    asset_summary,
    attendance_leave_summary,
    audit_events,
    production_consumption,
    purchasing_status,
    sales_fulfillment,
    stock_summary,
    trial_balance,
)

router = APIRouter(prefix="/api/report")


def _require(actor: Actor, *roles: str) -> None:
    if actor.role != "admin" and actor.role not in roles:
        raise HTTPException(status_code=403, detail="report access is restricted")


@router.get("/trial-balance")
async def report_trial_balance(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, object]:
    _require(actor, "finance_viewer", "finance_editor", "finance_manager")
    return {"data": trial_balance(database)}


@router.get("/stock")
async def report_stock(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, object]:
    _require(actor, "inv_editor", "inventory_manager", "finance_manager")
    return {"data": stock_summary(database)}


@router.get("/ar-ap")
async def report_ar_ap(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, object]:
    _require(actor, "finance_viewer", "finance_editor", "finance_manager")
    return {"data": ar_ap_summary(database)}


@router.get("/attendance-leave")
async def report_attendance_leave(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, object]:
    _require(actor, "hr_manager", "department_manager")
    return {"data": attendance_leave_summary(database)}


@router.get("/sales-fulfillment")
async def report_sales_fulfillment(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, object]:
    _require(actor, "finance_viewer", "finance_manager", "inventory_manager")
    return {"data": sales_fulfillment(database)}


@router.get("/purchasing-status")
async def report_purchasing_status(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, object]:
    _require(actor, "finance_viewer", "finance_manager", "procurement_manager")
    return {"data": purchasing_status(database)}


@router.get("/production-consumption")
async def report_production_consumption(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, object]:
    _require(actor, "inventory_manager", "production_manager", "finance_manager")
    return {"data": production_consumption(database)}


@router.get("/assets")
async def report_assets(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, object]:
    _require(actor, "finance_viewer", "finance_manager")
    return {"data": asset_summary(database)}


@router.get("/audit")
async def report_audit(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    action: str | None = None,
    resource_type: str | None = None,
    database: Database = Depends(get_database),
    actor: Actor = Depends(get_actor),
) -> dict[str, object]:
    _require(actor, "admin")
    rows, total = audit_events(database, limit=limit, offset=offset, action=action, resource_type=resource_type)
    return {"data": rows, "total": total, "limit": limit, "offset": offset}
