from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from database import Database
from dependencies import get_actor, get_database
from repositories.sales import SalesRepository
from services.authorization import Actor
from services.sales import (
    SalesError,
    create_delivery_note,
    create_sales_invoice,
    create_sales_order,
    submit_delivery_note,
    submit_sales_invoice,
)

router = APIRouter(prefix="/api/resource")


def _error(exc: SalesError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


@router.get("/Sales Order")
async def list_sales_orders(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return {"data": SalesRepository(database).list_sales_orders()}


@router.post("/Sales Order", status_code=201)
async def create_sales_order_route(
    data: dict[str, Any], database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        order = create_sales_order(
            database,
            actor,
            customer=str(data.get("customer", "")),
            transaction_date=str(data.get("transaction_date", "")),
            items=data.get("items") or [],
        )
    except SalesError as exc:
        raise _error(exc) from exc
    return {"data": {"name": order.name, "status": order.status, "grand_total": order.total}}


@router.get("/Delivery Note")
async def list_delivery_notes(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return {"data": SalesRepository(database).list_delivery_notes()}


@router.post("/Delivery Note", status_code=201)
async def create_delivery_note_route(
    data: dict[str, Any], database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        note = create_delivery_note(
            database,
            actor,
            sales_order_name=str(data.get("sales_order", "")),
            items=data.get("items") or [],
        )
    except SalesError as exc:
        raise _error(exc) from exc
    return {"data": {"name": note.name, "status": note.status}}


@router.post("/Delivery Note/{name}/submit")
async def submit_delivery_note_route(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        note = submit_delivery_note(database, actor, name)
    except SalesError as exc:
        raise _error(exc) from exc
    return {"data": {"name": note.name, "status": note.status}}


@router.get("/Sales Invoice")
async def list_sales_invoices(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return {"data": SalesRepository(database).list_sales_invoices()}


@router.post("/Sales Invoice", status_code=201)
async def create_sales_invoice_route(
    data: dict[str, Any], database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        invoice = create_sales_invoice(
            database,
            actor,
            delivery_note_name=str(data.get("delivery_note", "")),
            items=data.get("items") or [],
        )
    except SalesError as exc:
        raise _error(exc) from exc
    return {"data": {"name": invoice.name, "status": invoice.status, "grand_total": invoice.total}}


@router.post("/Sales Invoice/{name}/submit")
async def submit_sales_invoice_route(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        invoice = submit_sales_invoice(database, actor, name)
    except SalesError as exc:
        raise _error(exc) from exc
    return {"data": {"name": invoice.name, "status": invoice.status, "outstanding_amount": invoice.outstanding}}
