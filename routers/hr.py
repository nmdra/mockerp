from fastapi import APIRouter, Depends
from typing import List, Optional, Any
from dependencies import get_role, check_role, raise_erpnext_error

router = APIRouter(prefix="/api/resource")

employees = [
    {
        "name": "EMP-00001",
        "doctype": "Employee",
        "docstatus": 0,
        "employee_name": "Nimal Dharmasiri",
        "first_name": "Nimal",
        "last_name": "Dharmasiri",
        "gender": "Male",
        "date_of_birth": "1992-03-15",
        "date_of_joining": "2021-06-01",
        "status": "Active",
        "employment_type": "Full-time",
        "designation": "Software Engineer",
        "department": "Engineering",
        "branch": "Head Office",
        "company": "Acme Corp",
        "user_id": "nimal@company.com",
        "cell_number": "+94771234567",
        "personal_email": "nimal.dharmasiri@gmail.com",
        "salary_mode": "Bank",
        "bank_name": "Commercial Bank",
        "bank_ac_no": "1234567890",
        "relieving_date": None,
        "image": None
    }
]

departments = [
    {
        "name": "Engineering",
        "department_name": "Engineering",
        "company": "Acme Corp",
        "is_group": 0,
        "parent_department": None
    },
    {
        "name": "HR",
        "department_name": "HR",
        "company": "Acme Corp",
        "is_group": 0,
        "parent_department": None
    }
]

leave_applications = [
    {
        "name": "HR-LAP-2026-00003",
        "doctype": "Leave Application",
        "docstatus": 1,
        "employee": "EMP-00001",
        "employee_name": "Nimal Dharmasiri",
        "leave_type": "Annual Leave",
        "from_date": "2026-06-10",
        "to_date": "2026-06-12",
        "total_leave_days": 3.0,
        "half_day": 0,
        "status": "Approved",
        "description": "Family vacation",
        "posting_date": "2026-05-15"
    }
]

salary_slips = [
    {
        "name": "SAL-SLIP-2026-05-001",
        "doctype": "Salary Slip",
        "employee": "EMP-00001",
        "employee_name": "Nimal Dharmasiri",
        "posting_date": "2026-05-31",
        "start_date": "2026-05-01",
        "end_date": "2026-05-31",
        "salary_structure": "Engineer Grade A",
        "gross_pay": 85000.00,
        "total_deduction": 12750.00,
        "net_pay": 72250.00,
        "status": "Submitted"
    }
]

@router.get("/Employee")
async def list_employees(role: str = Depends(get_role)):
    return {"data": employees}

@router.get("/Employee/{name}")
async def get_employee(name: str, role: str = Depends(get_role)):
    for emp in employees:
        if emp["name"] == name:
            return {"data": emp}
    raise_erpnext_error("DoesNotExistError", f"Employee {name} not found", 404)

@router.get("/Department")
async def list_departments(role: str = Depends(get_role)):
    return {"data": departments}

@router.get("/Leave Application")
async def list_leave_applications(role: str = Depends(get_role)):
    return {"data": leave_applications}

@router.get("/Salary Slip")
async def list_salary_slips(role: str = Depends(get_role)):
    return {"data": salary_slips}
