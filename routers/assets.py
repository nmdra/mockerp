from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from database import Database
from dependencies import get_actor, get_database
from services.assets import AssetError, capitalize_asset, create_asset, dispose_asset, transfer_asset
from services.authorization import Actor

router = APIRouter(prefix="/api/resource")


def _error(exc: AssetError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


@router.get("/Asset Category")
async def list_asset_categories(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    with database.connection() as connection:
        rows = connection.execute("SELECT * FROM asset_categories ORDER BY name").fetchall()
        return {"data": [dict(row) for row in rows]}


@router.get("/Asset")
async def list_assets(
    database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, list[dict[str, object]]]:
    with database.connection() as connection:
        rows = connection.execute("SELECT * FROM assets ORDER BY name").fetchall()
        return {"data": [dict(row) for row in rows]}


@router.post("/Asset", status_code=201)
async def create_asset_route(
    data: dict[str, Any], database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        asset = create_asset(
            database,
            actor,
            category=str(data.get("category", "")),
            asset_name=str(data.get("asset_name", "")),
            acquisition_date=str(data.get("acquisition_date", "")),
            acquisition_cost=str(data.get("acquisition_cost", "0")),
            location=str(data.get("location", "")),
        )
    except AssetError as exc:
        raise _error(exc) from exc
    return {"data": {"name": asset.name, "asset_name": asset.asset_name, "status": asset.status, "location": asset.location}}


@router.post("/Asset/{name}/capitalize")
async def capitalize_asset_route(
    name: str, database: Database = Depends(get_database), actor: Actor = Depends(get_actor)
) -> dict[str, dict[str, object]]:
    try:
        asset = capitalize_asset(database, actor, name)
    except AssetError as exc:
        raise _error(exc) from exc
    return {"data": {"name": asset.name, "status": asset.status}}


@router.post("/Asset/{name}/transfer")
async def transfer_asset_route(
    name: str,
    data: dict[str, Any],
    database: Database = Depends(get_database),
    actor: Actor = Depends(get_actor),
) -> dict[str, dict[str, object]]:
    try:
        asset = transfer_asset(
            database,
            actor,
            name,
            location=str(data.get("location", "")),
            effective_date=str(data.get("effective_date", "")),
        )
    except AssetError as exc:
        raise _error(exc) from exc
    return {"data": {"name": asset.name, "status": asset.status, "location": asset.location}}


@router.post("/Asset/{name}/dispose")
async def dispose_asset_route(
    name: str,
    data: dict[str, Any],
    database: Database = Depends(get_database),
    actor: Actor = Depends(get_actor),
) -> dict[str, dict[str, object]]:
    try:
        asset = dispose_asset(
            database,
            actor,
            name,
            disposal_date=str(data.get("disposal_date", "")),
            proceeds=str(data.get("proceeds", "0")),
        )
    except AssetError as exc:
        raise _error(exc) from exc
    return {"data": {"name": asset.name, "status": asset.status}}
