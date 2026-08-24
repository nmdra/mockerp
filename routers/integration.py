from typing import Any

from fastapi import APIRouter, Depends

from dependencies import get_role

router = APIRouter(prefix="/api")

_last_echo_payload: dict[str, Any] | None = None


@router.get("/resource/Plugin Fixture")
async def get_plugin_fixture(role: str = Depends(get_role)) -> dict[str, Any]:
    return {"data": {"id": "plugin-fixture", "state": "source"}}


@router.post("/integration/echo")
async def echo_payload(
    data: dict[str, Any], role: str = Depends(get_role)
) -> dict[str, dict[str, Any]]:
    global _last_echo_payload
    _last_echo_payload = data
    return {"data": data}


@router.get("/integration/echo/last")
async def get_last_echo(role: str = Depends(get_role)) -> dict[str, dict[str, Any] | None]:
    return {"data": _last_echo_payload}
