from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any, Mapping


class SettingsError(ValueError):
    """Raised when MockERP cannot build a safe runtime configuration."""


@dataclass(frozen=True)
class Credential:
    api_key: str
    api_secret: str
    role: str
    identity: str


@dataclass(frozen=True)
class SessionCredential:
    sid: str
    role: str
    identity: str


@dataclass(frozen=True)
class BasicCredential:
    username: str
    password: str
    role: str
    identity: str


@dataclass(frozen=True)
class Settings:
    database_path: Path
    credential_source: str
    credentials: tuple[Credential, ...]
    sessions: tuple[SessionCredential, ...]
    basic_credentials: tuple[BasicCredential, ...]
    environment: str = "development"
    allow_reset: bool = False


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise SettingsError(f"credential field {field!r} must be a non-empty string")
    return value


def _as_records(value: Any, field: str) -> list[Mapping[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise SettingsError(f"credential field {field!r} must be a list")
    records: list[Mapping[str, Any]] = []
    for record in value:
        if not isinstance(record, Mapping):
            raise SettingsError(f"credential field {field!r} contains an invalid record")
        records.append(record)
    return records


def _parse_payload(payload: Any) -> tuple[
    tuple[Credential, ...], tuple[SessionCredential, ...], tuple[BasicCredential, ...]
]:
    if not isinstance(payload, Mapping):
        raise SettingsError("credential configuration must be a JSON object")

    credentials = tuple(
        Credential(
            api_key=_require_text(record.get("api_key"), "api_key"),
            api_secret=_require_text(record.get("api_secret"), "api_secret"),
            role=_require_text(record.get("role"), "role"),
            identity=_require_text(record.get("identity"), "identity"),
        )
        for record in _as_records(payload.get("credentials"), "credentials")
    )
    sessions = tuple(
        SessionCredential(
            sid=_require_text(record.get("sid"), "sid"),
            role=_require_text(record.get("role"), "role"),
            identity=_require_text(record.get("identity"), "identity"),
        )
        for record in _as_records(payload.get("sessions"), "sessions")
    )
    basic_credentials = tuple(
        BasicCredential(
            username=_require_text(record.get("username"), "username"),
            password=_require_text(record.get("password"), "password"),
            role=_require_text(record.get("role"), "role"),
            identity=_require_text(record.get("identity"), "identity"),
        )
        for record in _as_records(payload.get("basic"), "basic")
    )

    if not credentials and not sessions and not basic_credentials:
        raise SettingsError("credential configuration must contain at least one identity")
    return credentials, sessions, basic_credentials


def _load_payload(environ: Mapping[str, str]) -> tuple[Any, str]:
    credentials_file = environ.get("MOCK_ERP_CREDENTIALS_FILE", "").strip()
    credentials_json = environ.get("MOCK_ERP_CREDENTIALS_JSON", "").strip()
    if credentials_file and credentials_json:
        raise SettingsError("configure only one credential source")
    if credentials_file:
        path = Path(credentials_file)
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SettingsError("credential source file cannot be read") from exc
        source = str(path)
    elif credentials_json:
        raw = credentials_json
        source = "MOCK_ERP_CREDENTIALS_JSON"
    else:
        raise SettingsError("credential source is required")

    try:
        return json.loads(raw), source
    except json.JSONDecodeError as exc:
        raise SettingsError("credential source must contain valid JSON") from exc


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    values = os.environ if environ is None else environ
    payload, source = _load_payload(values)
    credentials, sessions, basic_credentials = _parse_payload(payload)
    return Settings(
        database_path=Path(values.get("MOCK_ERP_DB_PATH", "/data/mockerp.db")),
        credential_source=source,
        credentials=credentials,
        sessions=sessions,
        basic_credentials=basic_credentials,
        environment=values.get("MOCK_ERP_ENV", "development"),
        allow_reset=values.get("MOCK_ERP_ALLOW_RESET", "").lower()
        in {"1", "true", "yes"},
    )
