from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from dependencies import get_role, check_role

router = APIRouter(prefix="/api/v1/inventory")

items = [
    {"id": "item-001", "name": "Laptop", "sku": "LAP-001", "price": 1500.00, "stock_level": 50, "reorder_point": 10},
    {"id": "item-002", "name": "Mouse", "sku": "MOU-001", "price": 25.00, "stock_level": 200, "reorder_point": 50},
]

@router.get("/items")
async def list_items(role: str = Depends(get_role)):
    return {
        "data": items,
        "total": len(items),
    }

@router.get("/items/{item_id}")
async def get_item(item_id: str, role: str = Depends(get_role)):
    for item in items:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail="not found")
