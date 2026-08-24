from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from dependencies import get_actor, get_database
from repositories.organization import OrganizationRepository
from services.authorization import Actor, AuthorizationService
from services.workflow import (
    WorkflowError,
    approve_request,
    create_approval_request,
    reject_request,
)
from database import Database

router = APIRouter(prefix="/api/resource")


def _repository(database: Database) -> OrganizationRepository:
    return OrganizationRepository(database)


def _list(resource: str, database: Database, actor: Actor) -> dict[str, list[dict[str, object]]]:
    if resource in {"User", "Audit Event"} and actor.role != "admin":
        raise HTTPException(status_code=403, detail="organization resource is restricted")
    return {"data": _repository(database).list_resource(resource)}


def _get(resource: str, name: str, database: Database, actor: Actor) -> dict[str, object]:
    if resource in {"User", "Audit Event"} and actor.role != "admin":
        raise HTTPException(status_code=403, detail="organization resource is restricted")
    result = _repository(database).get_resource(resource, name)
    if result is None:
        raise HTTPException(status_code=404, detail=f"{resource} {name} not found")
    return {"data": result}


@router.get("/Company")
async def list_companies(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return _list("Company", database, actor)


@router.get("/Company/{name}")
async def get_company(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, object]:
    return _get("Company", name, database, actor)


@router.get("/Branch")
async def list_branches(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return _list("Branch", database, actor)


@router.get("/Department")
async def list_organization_departments(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return _list("Department", database, actor)


@router.get("/Designation")
async def list_designations(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return _list("Designation", database, actor)


@router.get("/Employment Type")
async def list_employment_types(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return _list("Employment Type", database, actor)


@router.get("/User")
async def list_users(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return _list("User", database, actor)


@router.get("/Role")
async def list_roles(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return _list("Role", database, actor)


@router.get("/Approval Rule")
async def list_approval_rules(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return _list("Approval Rule", database, actor)


@router.get("/Approval Request")
async def list_approval_requests(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return _list("Approval Request", database, actor)


@router.get("/Approval Request/{name}")
async def get_approval_request(
    name: str,
    database: Database = Depends(get_database),
    actor: Actor = Depends(get_actor),
) -> dict[str, object]:
    return _get("Approval Request", name, database, actor)


@router.post("/Approval Request", status_code=201)
async def create_approval_request_route(
    data: dict[str, Any],
    database: Database = Depends(get_database),
    actor: Actor = Depends(get_actor),
) -> JSONResponse:
    try:
        request = create_approval_request(
            database,
            actor,
            document_type=str(data.get("document_type", "")),
            reference_name=str(data.get("reference_name", "")),
            amount=data.get("amount", 0),
        )
    except WorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return JSONResponse(status_code=201, content={"data": request.as_dict()})


@router.post("/Approval Request/{name}/approve")
async def approve_approval_request(
    name: str,
    data: dict[str, Any] | None = None,
    database: Database = Depends(get_database),
    actor: Actor = Depends(get_actor),
) -> dict[str, dict[str, object]]:
    try:
        request = approve_request(database, actor, name, str((data or {}).get("comment", "")))
    except WorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"data": request.as_dict()}


@router.post("/Approval Request/{name}/reject")
async def reject_approval_request(
    name: str,
    data: dict[str, Any] | None = None,
    database: Database = Depends(get_database),
    actor: Actor = Depends(get_actor),
) -> dict[str, dict[str, object]]:
    try:
        request = reject_request(database, actor, name, str((data or {}).get("comment", "")))
    except WorkflowError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"data": request.as_dict()}


@router.get("/Audit Event")
async def list_audit_events(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    return _list("Audit Event", database, actor)
