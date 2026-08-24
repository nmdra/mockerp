from pathlib import Path

import pytest

from database import Database
from seed import seed_platform
from services.authorization import Actor
from services.expenses import (
    ExpenseError,
    approve_expense_claim,
    create_expense_claim,
    reimburse_expense_claim,
)


@pytest.fixture
def expense_database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "mockerp.db")
    database.initialize()
    seed_platform(database)
    yield database
    database.close()


def test_expense_claim_reimbursement_posts_payment_and_redacts_documents(
    expense_database: Database,
) -> None:
    employee = Actor(identity="employee-service", role="employee")
    manager = Actor(identity="manager-service", role="department_manager")

    claim = create_expense_claim(
        expense_database,
        employee,
        employee_name="EMP-SCP-00001",
        posting_date="2026-06-01",
        description="Fictional travel claim",
        lines=[{"expense_type": "Travel", "amount": "2500.00"}],
    )
    approved = approve_expense_claim(expense_database, manager, claim.name)
    reimbursed = reimburse_expense_claim(expense_database, manager, approved.name)

    assert reimbursed.status == "Reimbursed"
    assert reimbursed.payment_entry is not None
    with expense_database.connection() as connection:
        assert connection.execute(
            "SELECT 1 FROM payment_entries WHERE name = ?",
            (reimbursed.payment_entry,),
        ).fetchone() is not None


def test_expense_claim_rejects_unknown_employee(expense_database: Database) -> None:
    employee = Actor(identity="employee-service", role="employee")
    with pytest.raises(ExpenseError, match="employee"):
        create_expense_claim(
            expense_database,
            employee,
            employee_name="missing-employee",
            posting_date="2026-06-01",
            description="Invalid",
            lines=[{"expense_type": "Travel", "amount": "1.00"}],
        )
