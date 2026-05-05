from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from dependencies import get_role, check_role

router = APIRouter(prefix="/api/v1/finance")

class Invoice(BaseModel):
    id: Optional[str] = None
    number: str
    vendor_id: str
    vendor_name: str
    amount: float
    currency: str
    status: str
    due_date: str
    created_at: str

invoices = [
    {
        "id": "inv-001", "number": "INV-2026-001",
        "vendor_id": "v-001", "vendor_name": "Acme Supplies Ltd",
        "amount": 125000.00, "currency": "LKR",
        "status": "pending", "due_date": "2026-06-01T00:00:00Z",
        "created_at": "2026-05-01T09:00:00Z",
    },
    {
        "id": "inv-002", "number": "INV-2026-002",
        "vendor_id": "v-002", "vendor_name": "TechParts PVT",
        "amount": 48750.50, "currency": "LKR",
        "status": "paid", "due_date": "2026-05-15T00:00:00Z",
        "created_at": "2026-04-20T14:30:00Z",
    },
]

@router.get("/invoices")
async def list_invoices(role: str = Depends(get_role)):
    return {
        "data": invoices,
        "total": len(invoices),
        "page": 1,
    }

@router.post("/invoices", status_code=201)
async def create_invoice(invoice: Invoice, role: str = Depends(get_role)):
    check_role(["finance_editor"], role)
    invoice.id = "inv-new"
    return invoice

@router.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: str, role: str = Depends(get_role)):
    for inv in invoices:
        if inv["id"] == invoice_id:
            return inv
    raise HTTPException(status_code=404, detail="not found")
