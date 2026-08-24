from __future__ import annotations

from collections.abc import Iterable
import json
import sqlite3

from database import Database


_RESOURCE_TABLES = {
    "Company": "companies",
    "Branch": "branches",
    "Department": "departments",
    "Designation": "designations",
    "Employment Type": "employment_types",
    "User": "users",
    "Role": "roles",
    "Approval Rule": "approval_rules",
    "Approval Request": "approval_requests",
    "Approval Action": "approval_actions",
    "Audit Event": "audit_events",
}


class OrganizationRepository:
    def __init__(self, database: Database):
        self.database = database

    def list_resource(self, resource: str) -> list[dict[str, object]]:
        table = _RESOURCE_TABLES.get(resource)
        if table is None:
            raise ValueError(f"unsupported organization resource: {resource}")
        with self.database.connection() as connection:
            rows = connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            result = [self._row_to_resource(resource, row) for row in rows]
            if resource == "User":
                self._add_user_roles(connection, result)
            return result

    def get_resource(self, resource: str, name: str) -> dict[str, object] | None:
        table = _RESOURCE_TABLES.get(resource)
        if table is None:
            raise ValueError(f"unsupported organization resource: {resource}")
        with self.database.connection() as connection:
            row = connection.execute(
                f"SELECT * FROM {table} WHERE {self._identity_column(resource)} = ?",
                (name,),
            ).fetchone()
            if row is None:
                return None
            result = self._row_to_resource(resource, row)
            if resource == "User":
                self._add_user_roles(connection, [result])
            return result

    def _identity_column(self, resource: str) -> str:
        if resource == "User":
            return "identity"
        if resource in {"Approval Rule", "Approval Request", "Approval Action", "Audit Event"}:
            return "id"
        return "name"

    def _add_user_roles(
        self, connection: sqlite3.Connection, users: Iterable[dict[str, object]]
    ) -> None:
        for user in users:
            identity = user["name"]
            roles = connection.execute(
                "SELECT role FROM user_roles WHERE identity = ? ORDER BY role",
                (identity,),
            ).fetchall()
            user["roles"] = [row[0] for row in roles]

    def _row_to_resource(
        self, resource: str, row: sqlite3.Row
    ) -> dict[str, object]:
        values = dict(row)
        if resource == "Company":
            return {
                "name": values["name"],
                "company_name": values["name"],
                "currency": values["currency"],
                "country": values["country"],
                "is_active": values["is_active"],
            }
        if resource == "Branch":
            return {
                "name": values["name"],
                "company": values["company_name"],
                "address": values["address"],
                "is_active": values["is_active"],
            }
        if resource == "Department":
            return {
                "name": values["name"],
                "department_name": values["name"],
                "company": values["company_name"],
                "parent_department": values["parent_department"],
                "branch": values["branch_name"],
                "is_group": values["is_group"],
                "is_active": values["is_active"],
            }
        if resource in {"Designation", "Employment Type"}:
            return {"name": values["name"], "is_active": values["is_active"]}
        if resource == "User":
            return {
                "name": values["identity"],
                "full_name": values["full_name"],
                "email": values["email"],
                "is_active": values["is_active"],
            }
        if resource == "Role":
            return {"name": values["name"], "description": values["description"]}
        if resource == "Approval Rule":
            return {
                "name": f"APP-RULE-{values['id']:05d}",
                "document_type": values["document_type"],
                "sequence_no": values["sequence_no"],
                "role": values["role"],
                "minimum_amount": values["minimum_amount"],
                "is_active": values["is_active"],
            }
        if resource == "Approval Request":
            return {
                "name": values["id"],
                "document_type": values["document_type"],
                "reference_name": values["reference_name"],
                "amount": values["amount"],
                "status": values["status"],
                "requester_identity": values["requester_identity"],
                "created_at": values["created_at"],
            }
        if resource == "Approval Action":
            return {
                "name": f"APP-ACTION-{values['id']:05d}",
                "request_id": values["request_id"],
                "sequence_no": values["sequence_no"],
                "actor_identity": values["actor_identity"],
                "action": values["action"],
                "comment": values["comment"],
                "created_at": values["created_at"],
            }
        if resource == "Audit Event":
            return {
                "name": f"AUDIT-{values['id']:05d}",
                "actor_identity": values["actor_identity"],
                "action": values["action"],
                "resource_type": values["resource_type"],
                "resource_id": values["resource_id"],
                "before": json.loads(values["before_json"])
                if values["before_json"]
                else None,
                "after": json.loads(values["after_json"])
                if values["after_json"]
                else None,
                "created_at": values["created_at"],
            }
        return dict(values)
