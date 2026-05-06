from fastapi import APIRouter, Depends
from typing import List, Optional, Any
from dependencies import get_role, check_role, raise_erpnext_error

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
                "expense_account": "Cost of Goods Sold - C"
            }
        ],
        "owner": "admin@company.com",
        "creation": "2026-05-01T09:00:00.000000",
        "modified": "2026-05-01T09:00:00.000000",
        "modified_by": "admin@company.com"
    }
]

payment_entries = [
    {
        "name": "ACC-PAY-2026-00015",
        "doctype": "Payment Entry",
        "docstatus": 1,
        "payment_type": "Pay",
        "mode_of_payment": "Bank Transfer",
        "party_type": "Supplier",
        "party": "SUP-00001",
        "party_name": "Acme Supplies Ltd",
        "posting_date": "2026-05-01",
        "paid_amount": 125000.00,
        "received_amount": 125000.00,
        "reference_no": "CHQ-2026-0012",
        "reference_date": "2026-05-01",
        "paid_from": "Creditors - C",
        "paid_to": "Bank - C",
        "paid_to_account_currency": "LKR",
        "status": "Submitted",
        "references": [
            {
                "reference_doctype": "Purchase Invoice",
                "reference_name": "ACC-PINV-2026-00001",
                "allocated_amount": 125000.00
            }
        ]
    }
]

journal_entries = [
    {
        "name": "ACC-JV-2026-00007",
        "doctype": "Journal Entry",
        "docstatus": 1,
        "voucher_type": "Journal Entry",
        "posting_date": "2026-05-01",
        "total_debit": 50000.00,
        "total_credit": 50000.00,
        "remark": "Mock JV",
        "accounts": [
            {
                "account": "Cash - C",
                "debit_in_account_currency": 50000.00,
                "credit_in_account_currency": 0.0,
                "cost_center": "Main - C"
            },
            {
                "account": "Bank - C",
                "debit_in_account_currency": 0.0,
                "credit_in_account_currency": 50000.00,
                "cost_center": "Main - C"
            }
        ]
    }
]

@router.get("/Purchase Invoice")
async def list_purchase_invoices(role: str = Depends(get_role)):
    return {"data": purchase_invoices}

@router.get("/Purchase Invoice/{name}")
async def get_purchase_invoice(name: str, role: str = Depends(get_role)):
    for inv in purchase_invoices:
        if inv["name"] == name:
            return {"data": inv}
    raise_erpnext_error("DoesNotExistError", f"Purchase Invoice {name} not found", 404)

@router.post("/Purchase Invoice")
async def create_purchase_invoice(data: dict, role: str = Depends(get_role)):
    check_role(["finance_editor"], role)
    data["name"] = "ACC-PINV-2026-NEW"
    data["doctype"] = "Purchase Invoice"
    data["docstatus"] = 0
    return {"data": data}

@router.get("/Payment Entry")
async def list_payment_entries(role: str = Depends(get_role)):
    return {"data": payment_entries}

@router.get("/Journal Entry")
async def list_journal_entries(role: str = Depends(get_role)):
    return {"data": journal_entries}
