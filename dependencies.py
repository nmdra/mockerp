from __future__ import annotations

import base64
import binascii
import hmac

from fastapi import HTTPException, Request

from database import Database
from settings import Settings


class CredentialResolver:
    def __init__(self, settings: Settings):
        self._token_credentials = {
            f"{credential.api_key}:{credential.api_secret}": credential.role
            for credential in settings.credentials
        }
        self._sessions = {session.sid: session.role for session in settings.sessions}
        self._basic_credentials = {
            credential.username: (credential.password, credential.role)
            for credential in settings.basic_credentials
        }

    def token_role(self, token: str) -> str | None:
        for expected, role in self._token_credentials.items():
            if hmac.compare_digest(token, expected):
                return role
        return None

    def session_role(self, sid: str | None) -> str | None:
        if sid is None:
            return None
        for expected, role in self._sessions.items():
            if hmac.compare_digest(sid, expected):
                return role
        return None

    def basic_role(self, username: str, password: str) -> str | None:
        record = self._basic_credentials.get(username)
        if record is None:
            return None
        expected_password, role = record
        if hmac.compare_digest(password, expected_password):
            return role
        return None


def get_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if settings is None:
        raise RuntimeError("MockERP settings are not initialized")
    return settings


def get_database(request: Request) -> Database:
    database = getattr(request.app.state, "database", None)
    if database is None:
        raise RuntimeError("MockERP database is not initialized")
    return database


def get_resolver(request: Request) -> CredentialResolver:
    resolver = getattr(request.app.state, "credential_resolver", None)
    if resolver is None:
        raise RuntimeError("MockERP credentials are not initialized")
    return resolver


async def get_role(request: Request) -> str:
    resolver = get_resolver(request)
    auth = request.headers.get("Authorization", "")

    if auth.startswith("token "):
        token = auth.removeprefix("token ")
        role = resolver.token_role(token)
        if role is not None:
            return role
        raise_erpnext_error("AuthenticationError", "Invalid Credentials", 401)

    role = resolver.session_role(request.cookies.get("sid"))
    if role is not None:
        return role

    if auth.startswith("Basic "):
        encoded = auth.removeprefix("Basic ")
        try:
            decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
            username, password = decoded.split(":", 1)
        except (ValueError, UnicodeDecodeError, binascii.Error):
            username = password = ""
        role = resolver.basic_role(username, password)
        if role is not None:
            return role

    raise_erpnext_error("AuthenticationError", "Not logged in", 401)


def check_role(required_roles: list[str], current_role: str) -> None:
    if current_role == "admin":
        return
    if current_role not in required_roles:
        raise_erpnext_error("PermissionError", "Not permitted", 403)


def raise_erpnext_error(exc_type: str, message: str, status_code: int) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={
            "exc_type": exc_type,
            "exception": f"frappe.exceptions.{exc_type}: {message}",
            "_server_messages": "[]",
        },
    )
