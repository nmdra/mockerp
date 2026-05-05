from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from dependencies import get_role, check_role

router = APIRouter(prefix="/api/v1/hr")

employees = [
    {"id": "emp-001", "name": "Nimendra Anuradha", "role": "Software Engineer", "department": "Engineering", "email": "nimendra@example.com"},
    {"id": "emp-002", "name": "Jane Doe", "role": "HR Manager", "department": "HR", "email": "jane@example.com"},
]

@router.get("/employees")
async def list_employees(role: str = Depends(get_role)):
    return {
        "data": employees,
        "total": len(employees),
    }

@router.get("/employees/{employee_id}")
async def get_employee(employee_id: str, role: str = Depends(get_role)):
    for emp in employees:
        if emp["id"] == employee_id:
            return emp
    raise HTTPException(status_code=404, detail="not found")

@router.get("/departments")
async def list_departments(role: str = Depends(get_role)):
    return {
        "data": [{"id": "dept-001", "name": "Engineering"}, {"id": "dept-002", "name": "HR"}],
        "total": 2
    }
