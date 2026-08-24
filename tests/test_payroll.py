from pathlib import Path

import pytest

from database import Database
from seed import seed_platform
from services.authorization import Actor
from services.payroll import (
    PayrollError,
    approve_employee_advance,
    create_employee_advance,
    create_salary_slip,
    settle_employee_advance,
    submit_salary_slip,
)


@pytest.fixture
def payroll_database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "mockerp.db")
    database.initialize()
    seed_platform(database)
    yield database
    database.close()


def test_salary_slip_uses_approved_structure_without_statutory_claims(
    payroll_database: Database,
) -> None:
    actor = Actor(identity="hr-service", role="hr_manager")
    slip = create_salary_slip(
        payroll_database,
        actor,
        employee_name="EMP-SCP-00001",
        start_date="2026-06-01",
        end_date="2026-06-30",
    )

    assert slip.gross_pay == 90000
    assert slip.total_deduction == 1000
    assert slip.net_pay == 89000
    assert "PAYE" not in {line["component"] for line in slip.lines}

    submitted = submit_salary_slip(payroll_database, actor, slip.name)
    assert submitted.status == "Submitted"
    with payroll_database.connection() as connection:
        assert connection.execute(
            "SELECT 1 FROM gl_entries WHERE voucher_no = ?", (submitted.journal_entry,)
        ).fetchone() is not None


def test_employee_advance_has_controlled_lifecycle(payroll_database: Database) -> None:
    employee = Actor(identity="employee-service", role="employee")
    manager = Actor(identity="manager-service", role="department_manager")

    advance = create_employee_advance(
        payroll_database,
        employee,
        employee_name="EMP-SCP-00001",
        posting_date="2026-06-01",
        amount="1000.00",
    )
    assert advance.status == "Draft"
    assert approve_employee_advance(payroll_database, manager, advance.name).status == "Approved"
    assert settle_employee_advance(payroll_database, manager, advance.name).status == "Settled"


def test_salary_slip_requires_an_active_assignment(payroll_database: Database) -> None:
    actor = Actor(identity="hr-service", role="hr_manager")
    with pytest.raises(PayrollError, match="assignment"):
        create_salary_slip(
            payroll_database,
            actor,
            employee_name="missing-employee",
            start_date="2026-06-01",
            end_date="2026-06-30",
        )
