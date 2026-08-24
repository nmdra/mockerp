from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from database import Database
from dependencies import get_actor, get_database, get_role
from repositories.hr import HRRepository
from services.authorization import Actor
from services.hr import (
    HRServiceError,
    approve_leave_application,
    cancel_leave_application,
    create_attendance,
    create_leave_application,
    reject_leave_application,
)

router = APIRouter(prefix="/api/resource")

salary_slips = [
    {
        "name": "SAL-SLIP-2026-05-001",
        "doctype": "Salary Slip",
        "employee": "EMP-SCP-00001",
        "employee_name": "Kavindu Jayasekara",
        "posting_date": "2026-05-31",
        "start_date": "2026-05-01",
        "end_date": "2026-05-31",
        "salary_structure": "Officer Grade A",
        "gross_pay": 85000.00,
        "total_deduction": 12750.00,
        "net_pay": 72250.00,
        "status": "Submitted",
    }
]


def _repository(database: Database) -> HRRepository:
    return HRRepository(database)


def _can_view_all(actor: Actor) -> bool:
    return actor.role in {"admin", "hr_manager", "department_manager"}


def _error(exc: HRServiceError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


@router.get("/Employee")
async def list_employees(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    employees = _repository(database).list_employees()
    if _can_view_all(actor):
        return {"data": employees}
    return {
        "data": [employee for employee in employees if employee["user_id"] == actor.identity]
    }


@router.get("/Employee/{name}")
async def get_employee(
    name: str,
    database: Database = Depends(get_database),
    actor: Actor = Depends(get_actor),
) -> dict[str, dict[str, object]]:
    employee = _repository(database).get_employee(name)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")
    if not _can_view_all(actor) and employee["user_id"] != actor.identity:
        raise HTTPException(status_code=403, detail="employee access is restricted")
    return {"data": employee}


@router.get("/Attendance")
async def list_attendance(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    attendance = _repository(database).list_attendance()
    if _can_view_all(actor):
        return {"data": attendance}
    employee = _repository(database).get_employee_by_identity(actor.identity)
    if employee is None:
        return {"data": []}
    return {"data": [row for row in attendance if row["employee"] == employee["name"]]}


@router.post("/Attendance", status_code=201)
async def create_attendance_route(
    data: dict[str, Any],
    database: Database = Depends(get_database),
    actor: Actor = Depends(get_actor),
) -> dict[str, dict[str, object]]:
    try:
        record = create_attendance(
            database,
            actor,
            str(data.get("employee", "")),
            str(data.get("attendance_date", date.today().isoformat())),
            str(data.get("status", "")),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except HRServiceError as exc:
        raise _error(exc) from exc
    return {
        "data": {
            "name": record.name,
            "employee": record.employee,
            "attendance_date": record.attendance_date,
            "status": record.status,
        }
    }


@router.get("/Leave Type")
async def list_leave_types(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return {"data": _repository(database).list_leave_types()}


@router.get("/Leave Allocation")
async def list_leave_allocations(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    employee = None if _can_view_all(actor) else _repository(database).get_employee_by_identity(actor.identity)
    employee_name = employee["name"] if employee else None
    return {"data": _repository(database).list_leave_allocations(employee_name)}


@router.get("/Leave Application")
async def list_leave_applications(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    applications = _repository(database).list_leave_applications()
    if _can_view_all(actor):
        return {"data": applications}
    employee = _repository(database).get_employee_by_identity(actor.identity)
    return {
        "data": [row for row in applications if employee and row["employee"] == employee["name"]]
    }


@router.get("/Leave Application/{name}")
async def get_leave_application(
    name: str,
    database: Database = Depends(get_database),
    actor: Actor = Depends(get_actor),
) -> dict[str, dict[str, object]]:
    application = _repository(database).get_leave_application(name)
    if application is None:
        raise HTTPException(status_code=404, detail="Leave Application not found")
    if not _can_view_all(actor):
        employee = _repository(database).get_employee_by_identity(actor.identity)
        if employee is None or application["employee"] != employee["name"]:
            raise HTTPException(status_code=403, detail="leave access is restricted")
    return {"data": application}


@router.post("/Leave Application", status_code=201)
async def create_leave_application_route(
    data: dict[str, Any],
    database: Database = Depends(get_database),
    actor: Actor = Depends(get_actor),
) -> dict[str, dict[str, object]]:
    try:
        application = create_leave_application(
            database,
            actor,
            employee_name=str(data.get("employee", "")),
            leave_type=str(data.get("leave_type", "")),
            from_date=str(data.get("from_date", "")),
            to_date=str(data.get("to_date", "")),
            half_day=bool(data.get("half_day", False)),
            description=str(data.get("description", "")),
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except HRServiceError as exc:
        raise _error(exc) from exc
    return {"data": application.as_dict()}


@router.post("/Leave Application/{name}/approve")
async def approve_leave_route(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        application = approve_leave_application(database, actor, name)
    except HRServiceError as exc:
        raise _error(exc) from exc
    return {"data": application.as_dict()}


@router.post("/Leave Application/{name}/reject")
async def reject_leave_route(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        application = reject_leave_application(database, actor, name)
    except HRServiceError as exc:
        raise _error(exc) from exc
    return {"data": application.as_dict()}


@router.post("/Leave Application/{name}/cancel")
async def cancel_leave_route(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        application = cancel_leave_application(database, actor, name)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except HRServiceError as exc:
        raise _error(exc) from exc
    return {"data": application.as_dict()}


@router.get("/Salary Slip")
async def list_salary_slips(role: str = Depends(get_role)) -> dict[str, list[dict[str, object]]]:
    return {"data": salary_slips}
