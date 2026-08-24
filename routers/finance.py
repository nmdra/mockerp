from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from dependencies import check_role, get_actor, get_database, get_role, raise_erpnext_error
from repositories.finance import FinanceRepository
from services.accounting import (
    AccountingError,
    cancel_journal_entry,
    cancel_payment_entry,
    create_journal_entry,
    create_payment_entry,
    submit_journal_entry,
    submit_payment_entry,
)
from services.authorization import Actor
from database import Database

router = APIRouter(prefix="/api/resource")

purchase_invoices = [
    {
        "name": "ACC-PINV-2026-00001",
        "doctype": "Purchase Invoice",
        "docstatus": 1,
        "naming_series": "ACC-PINV-.YYYY.-",
        "supplier": "SUP-00001",
        "supplier_name": "Acme Supplies Ltd",
        "posting_date": "2026-05-01",
        "due_date": "2026-06-01",
        "bill_no": "INV-EXT-4521",
        "bill_date": "2026-04-28",
        "currency": "LKR",
        "conversion_rate": 1.0,
        "net_total": 112500.00,
        "total_taxes_and_charges": 12500.00,
        "grand_total": 125000.00,
        "outstanding_amount": 125000.00,
        "status": "Unpaid",
        "is_paid": 0,
        "cost_center": "Main - C",
        "company": "Acme Corp",
        "items": [
            {
                "item_code": "ITEM-001",
                "item_name": "Office Chair",
                "qty": 5,
                "uom": "Nos",
                "rate": 22500.00,
                "amount": 112500.00,
                "expense_account": "Cost of Goods Sold - C",
            }
        ],
        "owner": "admin@company.com",
        "creation": "2026-05-01T09:00:00.000000",
        "modified": "2026-05-01T09:00:00.000000",
        "modified_by": "admin@company.com",
    }
]


def _require_finance(actor: Actor) -> None:
    if actor.role not in {
        "admin",
        "finance_viewer",
        "finance_editor",
        "finance_manager",
    }:
        raise HTTPException(status_code=403, detail="finance role is required")


def _accounting_error(exc: AccountingError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


@router.get("/Purchase Invoice")
async def list_purchase_invoices(role: str = Depends(get_role)) -> dict[str, list[dict[str, Any]]]:
    return {"data": purchase_invoices}


@router.get("/Purchase Invoice/{name}")
async def get_purchase_invoice(name: str, role: str = Depends(get_role)) -> dict[str, dict[str, Any]]:
    for inv in purchase_invoices:
        if inv["name"] == name:
            return {"data": inv}
    raise_erpnext_error("DoesNotExistError", f"Purchase Invoice {name} not found", 404)


@router.post("/Purchase Invoice")
async def create_purchase_invoice(data: dict[str, Any], role: str = Depends(get_role)) -> dict[str, dict[str, Any]]:
    check_role(["finance_editor"], role)
    data["name"] = "ACC-PINV-2026-NEW"
    data["doctype"] = "Purchase Invoice"
    data["docstatus"] = 0
    return {"data": data}


@router.get("/Account")
async def list_accounts(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    _require_finance(actor)
    return {"data": FinanceRepository(database).list_accounts()}


@router.get("/Payment Entry")
async def list_payment_entries(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    _require_finance(actor)
    return {"data": FinanceRepository(database).list_payment_entries()}


@router.get("/Payment Entry/{name}")
async def get_payment_entry(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    _require_finance(actor)
    result = FinanceRepository(database).get_payment_entry(name)
    if result is None:
        raise HTTPException(status_code=404, detail="Payment Entry not found")
    return {"data": result}


@router.post("/Payment Entry", status_code=201)
async def create_payment_entry_route(
    data: dict[str, Any],
    database: Database = Depends(get_database),
    actor: Actor = Depends(get_actor),
) -> dict[str, dict[str, object]]:
    _require_finance(actor)
    try:
        entry = create_payment_entry(
            database,
            actor,
            posting_date=str(data.get("posting_date", "")),
            party_type=data.get("party_type"),
            party=data.get("party"),
            paid_from=str(data.get("paid_from", "")),
            paid_to=str(data.get("paid_to", "")),
            paid_amount=data.get("paid_amount", 0),
            references=data.get("references") or [],
            payment_type=str(data.get("payment_type", "Pay")),
        )
    except AccountingError as exc:
        raise _accounting_error(exc) from exc
    return {"data": entry.as_dict()}


@router.post("/Payment Entry/{name}/submit")
async def submit_payment_entry_route(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    _require_finance(actor)
    try:
        entry = submit_payment_entry(database, actor, name)
    except AccountingError as exc:
        raise _accounting_error(exc) from exc
    return {"data": entry.as_dict()}


@router.post("/Payment Entry/{name}/cancel")
async def cancel_payment_entry_route(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    _require_finance(actor)
    try:
        entry = cancel_payment_entry(database, actor, name)
    except AccountingError as exc:
        raise _accounting_error(exc) from exc
    return {"data": entry.as_dict()}


@router.get("/Journal Entry")
async def list_journal_entries(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    _require_finance(actor)
    return {"data": FinanceRepository(database).list_journal_entries()}


@router.get("/Journal Entry/{name}")
async def get_journal_entry(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    _require_finance(actor)
    result = FinanceRepository(database).get_journal_entry(name)
    if result is None:
        raise HTTPException(status_code=404, detail="Journal Entry not found")
    return {"data": result}


@router.post("/Journal Entry", status_code=201)
async def create_journal_entry_route(
    data: dict[str, Any],
    database: Database = Depends(get_database),
    actor: Actor = Depends(get_actor),
) -> dict[str, dict[str, object]]:
    _require_finance(actor)
    try:
        entry = create_journal_entry(
            database,
            actor,
            posting_date=str(data.get("posting_date", "")),
            remark=str(data.get("remark", "")),
            accounts=data.get("accounts") or [],
        )
    except AccountingError as exc:
        raise _accounting_error(exc) from exc
    return {"data": entry.as_dict()}


@router.post("/Journal Entry/{name}/submit")
async def submit_journal_entry_route(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    _require_finance(actor)
    try:
        entry = submit_journal_entry(database, actor, name)
    except AccountingError as exc:
        raise _accounting_error(exc) from exc
    return {"data": entry.as_dict()}


@router.post("/Journal Entry/{name}/cancel")
async def cancel_journal_entry_route(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    _require_finance(actor)
    try:
        entry = cancel_journal_entry(database, actor, name)
    except AccountingError as exc:
        raise _accounting_error(exc) from exc
    return {"data": entry.as_dict()}
