from pathlib import Path

import pytest

from database import Database
from seed import seed_platform
from services.reports import audit_events, stock_summary, trial_balance


@pytest.fixture
def report_database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "mockerp.db")
    database.initialize()
    seed_platform(database)
    yield database
    database.close()


def test_seeded_trial_balance_and_stock_reports_are_deterministic(
    report_database: Database,
) -> None:
    first_trial = trial_balance(report_database)
    first_stock = stock_summary(report_database)

    report_database.reset()
    seed_platform(report_database)

    assert trial_balance(report_database) == first_trial
    assert stock_summary(report_database) == first_stock
    assert sum(row["debit"] - row["credit"] for row in first_trial) == 0


def test_audit_readback_is_paginated_and_redacted(report_database: Database) -> None:
    rows, total = audit_events(report_database, limit=10, offset=0)

    assert total >= 0
    assert len(rows) <= 10
    assert all("api_secret" not in str(row) for row in rows)
