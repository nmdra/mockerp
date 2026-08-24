from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
import json
import sqlite3
from typing import Any

from database import Database
from services.authorization import Actor

_SENSITIVE_KEYS = {
    "api_key",
    "api_secret",
    "credential",
    "password",
    "secret",
    "token",
    "document_content",
    "file_content",
}


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: "[REDACTED]" if key.lower() in _SENSITIVE_KEYS else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def _json(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(_redact(value), sort_keys=True, separators=(",", ":"))


def _insert_audit(
    connection: sqlite3.Connection,
    actor: Actor,
    action: str,
    resource_type: str,
    resource_id: str,
    before: Any,
    after: Any,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO audit_events
            (actor_identity, action, resource_type, resource_id,
             before_json, after_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            actor.identity,
            action,
            resource_type,
            resource_id,
            _json(before),
            _json(after),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    return int(cursor.lastrowid)


def record_audit(
    database: Database,
    actor: Actor,
    action: str,
    resource_type: str,
    resource_id: str,
    before: Any = None,
    after: Any = None,
    connection: sqlite3.Connection | None = None,
) -> int:
    if connection is not None:
        return _insert_audit(
            connection, actor, action, resource_type, resource_id, before, after
        )
    with database.transaction() as transaction:
        return _insert_audit(
            transaction, actor, action, resource_type, resource_id, before, after
        )


class AuditService:
    def __init__(self, database: Database):
        self.database = database

    def record(self, actor: Actor, action: str, resource_type: str, resource_id: str, before: Any = None, after: Any = None) -> int:
        return record_audit(
            self.database, actor, action, resource_type, resource_id, before, after
        )
