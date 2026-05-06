from fastapi import APIRouter, Depends, Request
from typing import List, Optional, Any
from dependencies import get_role, check_role, raise_erpnext_error
import json

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
async def list_items(role: str = Depends(get_role)):
    return {"data": items}

@router.get("/Item/{name}")
async def get_item(name: str, role: str = Depends(get_role)):
    for item in items:
        if item["name"] == name:
            return {"data": item}
    raise_erpnext_error("DoesNotExistError", f"Item {name} not found", 404)

@router.get("/Bin")
async def list_bins(request: Request, role: str = Depends(get_role)):
    filters = request.query_params.get("filters")
    if filters:
        try:
            filter_list = json.loads(filters)
            if filter_list and len(filter_list) > 0:
                f = filter_list[0]
                if len(f) >= 4 and f[1] == "item_code" and f[2] == "=":
                    val = f[3]
                    return {"data": [b for b in bins if b["item_code"] == val]}
        except:
            pass
    return {"data": bins}

@router.get("/Purchase Order")
async def list_purchase_orders(role: str = Depends(get_role)):
    return {"data": purchase_orders}
