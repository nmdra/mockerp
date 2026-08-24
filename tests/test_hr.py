from datetime import date, timedelta
from pathlib import Path

import pytest

from database import Database
from seed import seed_platform
from services.authorization import Actor
from services.hr import (
    HRServiceError,
    create_attendance,
    create_leave_application,
    approve_leave_application,
    calculate_leave_days,
)


@pytest.fixture
def hr_database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "mockerp.db")
    database.initialize()
    seed_platform(database)
    yield database
    database.close()


def test_attendance_accepts_four_states_and_rejects_future_or_duplicate(
    hr_database: Database,
) -> None:
    employee = Actor(identity="employee-service", role="employee")
    attendance_date = date.today().isoformat()

    created = create_attendance(
        hr_database, employee, "EMP-SCP-00001", attendance_date, "Work From Home"
    )
    assert created.status == "Work From Home"

    with pytest.raises(HRServiceError, match="duplicate"):
        create_attendance(
            hr_database, employee, "EMP-SCP-00001", attendance_date, "Present"
        )
    with pytest.raises(HRServiceError, match="future"):
        create_attendance(
            hr_database,
            employee,
            "EMP-SCP-00001",
            (date.today() + timedelta(days=1)).isoformat(),
            "Present",
        )


def test_leave_workflow_calculates_days_and_updates_balance(
    hr_database: Database,
) -> None:
    employee = Actor(identity="employee-service", role="employee")
    manager = Actor(identity="manager-service", role="department_manager")
    hr_manager = Actor(identity="hr-service", role="hr_manager")

    assert calculate_leave_days("2026-07-01", "2026-07-03", False) == 3
    assert calculate_leave_days("2026-07-01", "2026-07-03", True) == 2.5
    application = create_leave_application(
        hr_database,
        employee,
        employee_name="EMP-SCP-00001",
        leave_type="Annual Leave",
        from_date="2026-07-01",
        to_date="2026-07-03",
        half_day=False,
        description="Fictional test leave",
    )
    assert application.status == "Pending Approval"

    pending = approve_leave_application(hr_database, manager, application.name)
    assert pending.status == "Pending Approval"
    approved = approve_leave_application(hr_database, hr_manager, application.name)
    assert approved.status == "Approved"

    with hr_database.connection() as connection:
        used = connection.execute(
            "SELECT used_days FROM leave_allocations WHERE employee_name = ?",
            ("EMP-SCP-00001",),
        ).fetchone()[0]
    assert used == 6

    with pytest.raises(HRServiceError, match="balance"):
        create_leave_application(
            hr_database,
            employee,
            employee_name="EMP-SCP-00001",
            leave_type="Annual Leave",
            from_date="2026-08-01",
            to_date="2026-08-30",
            half_day=False,
            description="Too much leave",
        )
