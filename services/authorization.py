from __future__ import annotations

from dataclasses import dataclass

from database import Database


@dataclass(frozen=True)
class Actor:
    identity: str
    role: str


class AuthorizationService:
    """Apply organization access rules without embedding credentials."""

    def __init__(self, database: Database):
        self.database = database

    def can_access_employee(self, actor: Actor, employee_identity: str) -> bool:
        if actor.role in {"admin", "hr_manager", "department_manager"}:
            return True
        return actor.identity == employee_identity

    def require_employee_access(self, actor: Actor, employee_identity: str) -> None:
        if not self.can_access_employee(actor, employee_identity):
            raise PermissionError("employee self-service access is restricted")

    def require_role(self, actor: Actor, *roles: str) -> None:
        if actor.role != "admin" and actor.role not in roles:
            raise PermissionError("actor role is not authorized")
