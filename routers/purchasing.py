from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from database import Database
from dependencies import get_actor, get_database
from repositories.purchasing import PurchasingRepository
from services.authorization import Actor
from services.purchasing import (
    PurchasingError,
    approve_purchase_order,
    create_material_request,
    create_purchase_invoice,
    create_purchase_order,
    create_purchase_receipt,
    submit_purchase_invoice,
    submit_purchase_receipt,
)

router = APIRouter(prefix="/api/resource")


def _error(exc: PurchasingError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


@router.get("/Material Request")
async def list_material_requests(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return {"data": PurchasingRepository(database).list_material_requests()}


@router.post("/Material Request", status_code=201)
async def create_material_request_route(
    data: dict[str, Any], database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        request = create_material_request(
            database,
            actor,
            posting_date=str(data.get("posting_date", "")),
            items=data.get("items") or [],
        )
    except PurchasingError as exc:
        raise _error(exc) from exc
    return {"data": {"name": request.name, "status": request.status}}


@router.get("/Purchase Order")
async def list_purchase_orders(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return {"data": PurchasingRepository(database).list_purchase_orders()}


@router.post("/Purchase Order", status_code=201)
async def create_purchase_order_route(
    data: dict[str, Any], database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        order = create_purchase_order(
            database,
            actor,
            material_request_name=str(data.get("material_request", "")),
            supplier=str(data.get("supplier", "")),
            transaction_date=str(data.get("transaction_date", "")),
            items=data.get("items") or [],
        )
    except PurchasingError as exc:
        raise _error(exc) from exc
    return {"data": {"name": order.name, "status": order.status, "grand_total": order.total}}


@router.post("/Purchase Order/{name}/approve")
async def approve_purchase_order_route(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        order = approve_purchase_order(database, actor, name)
    except PurchasingError as exc:
        raise _error(exc) from exc
    return {"data": {"name": order.name, "status": order.status, "grand_total": order.total}}


@router.get("/Purchase Receipt")
async def list_purchase_receipts(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return {"data": PurchasingRepository(database).list_purchase_receipts()}


@router.post("/Purchase Receipt", status_code=201)
async def create_purchase_receipt_route(
    data: dict[str, Any], database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        receipt = create_purchase_receipt(
            database,
            actor,
            purchase_order_name=str(data.get("purchase_order", "")),
            items=data.get("items") or [],
        )
    except PurchasingError as exc:
        raise _error(exc) from exc
    return {"data": {"name": receipt.name, "status": receipt.status}}


@router.post("/Purchase Receipt/{name}/submit")
async def submit_purchase_receipt_route(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        receipt = submit_purchase_receipt(database, actor, name)
    except PurchasingError as exc:
        raise _error(exc) from exc
    return {"data": {"name": receipt.name, "status": receipt.status}}


@router.get("/Purchase Invoice")
async def list_purchase_invoices(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return {"data": PurchasingRepository(database).list_purchase_invoices()}


@router.get("/Purchase Invoice/{name}")
async def get_purchase_invoice(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    invoice = PurchasingRepository(database).get_purchase_invoice(name)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Purchase Invoice not found")
    return {"data": invoice}


@router.post("/Purchase Invoice", status_code=201)
async def create_purchase_invoice_route(
    data: dict[str, Any], database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        invoice = create_purchase_invoice(
            database,
            actor,
            purchase_receipt_name=str(data.get("purchase_receipt", "")),
            items=data.get("items") or [],
        )
    except PurchasingError as exc:
        raise _error(exc) from exc
    return {"data": {"name": invoice.name, "status": invoice.status, "grand_total": invoice.total}}


@router.post("/Purchase Invoice/{name}/submit")
async def submit_purchase_invoice_route(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        invoice = submit_purchase_invoice(database, actor, name)
    except PurchasingError as exc:
        raise _error(exc) from exc
    return {"data": {"name": invoice.name, "status": invoice.status, "outstanding_amount": invoice.outstanding}}
