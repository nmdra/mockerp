from pathlib import Path
import sqlite3

import pytest

from database import Database
from seed import seed_platform
from services.audit import record_audit
from services.authorization import Actor, AuthorizationService
from services.workflow import WorkflowError, approve_request, create_approval_request


@pytest.fixture
def organization_database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "mockerp.db")
    database.initialize()
    seed_platform(database)
    yield database
    database.close()


def test_purchase_threshold_adds_a_sequential_finance_approval(
    organization_database: Database,
) -> None:
    requester = Actor(identity="procurement-service", role="procurement_manager")
    finance = Actor(identity="finance-service", role="finance_manager")
    administrator = Actor(identity="admin-service", role="admin")

    request = create_approval_request(
        organization_database,
        requester,
        document_type="Purchase Order",
        reference_name="PUR-ORD-2026-00002",
        amount=150000,
    )
    assert request.status == "PENDING_APPROVAL"

    with pytest.raises(WorkflowError, match="sequence"):
        approve_request(organization_database, administrator, request.id)

    first = approve_request(organization_database, finance, request.id)
    assert first.status == "PENDING_APPROVAL"
    assert approve_request(organization_database, administrator, request.id).status == "APPROVED"


def test_audit_events_are_immutable_and_redacted(
    organization_database: Database,
) -> None:
    actor = Actor(identity="admin-service", role="admin")
    record_audit(
        organization_database,
        actor,
        "create",
        "Test",
        "TEST-001",
        after={"credential": "not-stored", "visible": "ok"},
    )

    with organization_database.connection() as connection:
        row = connection.execute("SELECT * FROM audit_events").fetchone()
        assert "not-stored" not in (row["after_json"] or "")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute("UPDATE audit_events SET action = 'changed'")
        with pytest.raises(sqlite3.IntegrityError, match="immutable"):
            connection.execute("DELETE FROM audit_events")


def test_authorization_restricts_employee_self_service(
    organization_database: Database,
) -> None:
    service = AuthorizationService(organization_database)
    employee = Actor(identity="employee-service", role="employee")
    manager = Actor(identity="manager-service", role="department_manager")

    assert service.can_access_employee(employee, "employee-service") is True
    assert service.can_access_employee(employee, "manager-service") is False
    assert service.can_access_employee(manager, "employee-service") is True
