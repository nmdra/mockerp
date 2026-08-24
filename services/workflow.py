from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import sqlite3

from database import Database
from services.audit import record_audit
from services.authorization import Actor


class WorkflowError(ValueError):
    """Raised when an approval request cannot advance."""


@dataclass(frozen=True)
class ApprovalRequest:
    id: str
    document_type: str
    reference_name: str
    amount: Decimal
    status: str
    requester_identity: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ApprovalRequest":
        return cls(
            id=row["id"],
            document_type=row["document_type"],
            reference_name=row["reference_name"],
            amount=Decimal(str(row["amount"])),
            status=row["status"],
            requester_identity=row["requester_identity"],
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.id,
            "document_type": self.document_type,
            "reference_name": self.reference_name,
            "amount": float(self.amount),
            "status": self.status,
            "requester_identity": self.requester_identity,
        }


def _amount(value: Decimal | int | float | str) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise WorkflowError("approval amount must be numeric") from exc
    if parsed < 0:
        raise WorkflowError("approval amount cannot be negative")
    return parsed


def _rules(
    connection: sqlite3.Connection, document_type: str, amount: Decimal
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT sequence_no, role, minimum_amount
        FROM approval_rules
        WHERE document_type = ? AND is_active = 1 AND minimum_amount <= ?
        ORDER BY sequence_no
        """,
        (document_type, float(amount)),
    ).fetchall()


def _get_request(connection: sqlite3.Connection, request_id: str) -> sqlite3.Row:
    row = connection.execute(
        "SELECT * FROM approval_requests WHERE id = ?", (request_id,)
    ).fetchone()
    if row is None:
        raise WorkflowError("approval request was not found")
    return row


def create_approval_request(
    database: Database,
    actor: Actor,
    *,
    document_type: str,
    reference_name: str,
    amount: Decimal | int | float | str = 0,
) -> ApprovalRequest:
    if not document_type or not reference_name:
        raise WorkflowError("document type and reference name are required")
    parsed_amount = _amount(amount)
    request_id = database.next_document_name("APP-REQ")
    now = datetime.now(timezone.utc).isoformat()
    with database.transaction() as connection:
        rules = _rules(connection, document_type, parsed_amount)
        status = "PENDING_APPROVAL" if rules else "APPROVED"
        try:
            connection.execute(
                """
                INSERT INTO approval_requests
                    (id, document_type, reference_name, amount, status,
                     requester_identity, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    document_type,
                    reference_name,
                    float(parsed_amount),
                    status,
                    actor.identity,
                    now,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise WorkflowError("an approval request already exists") from exc
        after = {
            "name": request_id,
            "document_type": document_type,
            "reference_name": reference_name,
            "amount": float(parsed_amount),
            "status": status,
            "requester_identity": actor.identity,
        }
        record_audit(
            database,
            actor,
            "create",
            "Approval Request",
            request_id,
            after=after,
            connection=connection,
        )
        return ApprovalRequest(
            request_id, document_type, reference_name, parsed_amount, status, actor.identity
        )


def _act(
    database: Database, actor: Actor, request_id: str, action: str, comment: str = ""
) -> ApprovalRequest:
    if action not in {"approve", "reject"}:
        raise WorkflowError("unsupported approval action")
    with database.transaction() as connection:
        row = _get_request(connection, request_id)
        if row["status"] != "PENDING_APPROVAL":
            raise WorkflowError("approval request is not pending")
        rules = _rules(connection, row["document_type"], Decimal(str(row["amount"])))
        action_count = connection.execute(
            "SELECT COUNT(*) FROM approval_actions WHERE request_id = ?",
            (request_id,),
        ).fetchone()[0]
        next_sequence = action_count + 1
        if next_sequence > len(rules):
            raise WorkflowError("approval request has no remaining approval sequence")
        rule = rules[next_sequence - 1]
        if actor.role != rule["role"]:
            raise WorkflowError(f"approval sequence requires role {rule['role']}")
        now = datetime.now(timezone.utc).isoformat()
        connection.execute(
            """
            INSERT INTO approval_actions
                (request_id, sequence_no, actor_identity, action, comment, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (request_id, next_sequence, actor.identity, action, comment, now),
        )
        status = "REJECTED" if action == "reject" else (
            "APPROVED" if next_sequence == len(rules) else "PENDING_APPROVAL"
        )
        connection.execute(
            "UPDATE approval_requests SET status = ? WHERE id = ?",
            (status, request_id),
        )
        before = dict(row)
        before.pop("created_at", None)
        after = dict(before)
        after["status"] = status
        record_audit(
            database,
            actor,
            action,
            "Approval Request",
            request_id,
            before=before,
            after=after,
            connection=connection,
        )
        updated = _get_request(connection, request_id)
        return ApprovalRequest.from_row(updated)


def approve_request(
    database: Database, actor: Actor, request_id: str, comment: str = ""
) -> ApprovalRequest:
    return _act(database, actor, request_id, "approve", comment)


def reject_request(
    database: Database, actor: Actor, request_id: str, comment: str = ""
) -> ApprovalRequest:
    return _act(database, actor, request_id, "reject", comment)


class WorkflowService:
    def __init__(self, database: Database):
        self.database = database

    def create(self, actor: Actor, **kwargs: object) -> ApprovalRequest:
        return create_approval_request(self.database, actor, **kwargs)

    def approve(self, actor: Actor, request_id: str, comment: str = "") -> ApprovalRequest:
        return approve_request(self.database, actor, request_id, comment)

    def reject(self, actor: Actor, request_id: str, comment: str = "") -> ApprovalRequest:
        return reject_request(self.database, actor, request_id, comment)
