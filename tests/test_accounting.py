from decimal import Decimal
from pathlib import Path

import pytest

from database import Database
from seed import seed_platform
from services.accounting import (
    AccountingError,
    create_journal_entry,
    create_payment_entry,
    money_to_minor,
    minor_to_money,
    submit_journal_entry,
    submit_payment_entry,
    cancel_journal_entry,
)
from services.authorization import Actor


@pytest.fixture
def finance_database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "mockerp.db")
    database.initialize()
    seed_platform(database)
    yield database
    database.close()


def test_money_conversion_uses_minor_units() -> None:
    assert money_to_minor("125000.10") == 12500010
    assert minor_to_money(12500010) == Decimal("125000.10")


def test_unbalanced_journal_entry_cannot_be_submitted(
    finance_database: Database,
) -> None:
    actor = Actor(identity="finance-service", role="finance_editor")
    entry = create_journal_entry(
        finance_database,
        actor,
        posting_date="2026-06-01",
        remark="Unbalanced test",
        accounts=[
            {"account": "1100 - Bank - SCP", "debit": "100.00", "credit": "0"},
            {"account": "2100 - Creditors - SCP", "debit": "0", "credit": "90.00"},
        ],
    )

    with pytest.raises(AccountingError, match="balanced"):
        submit_journal_entry(finance_database, actor, entry.name)


def test_journal_submission_and_cancellation_are_double_entry(
    finance_database: Database,
) -> None:
    actor = Actor(identity="finance-service", role="finance_editor")
    entry = create_journal_entry(
        finance_database,
        actor,
        posting_date="2026-06-01",
        remark="Balanced test",
        accounts=[
            {"account": "1100 - Bank - SCP", "debit": "100.00", "credit": "0"},
            {"account": "2100 - Creditors - SCP", "debit": "0", "credit": "100.00"},
        ],
    )

    submitted = submit_journal_entry(finance_database, actor, entry.name)
    assert submitted.status == "Submitted"
    with finance_database.connection() as connection:
        totals = connection.execute(
            "SELECT SUM(debit_minor), SUM(credit_minor) FROM gl_entries WHERE voucher_no = ?",
            (entry.name,),
        ).fetchone()
    assert tuple(totals) == (10000, 10000)

    cancelled = cancel_journal_entry(finance_database, actor, entry.name)
    assert cancelled.status == "Cancelled"
    with finance_database.connection() as connection:
        net = connection.execute(
            """
            SELECT SUM(debit_minor - credit_minor)
            FROM gl_entries WHERE voucher_no = ?
            """,
            (entry.name,),
        ).fetchone()[0]
    assert net == 0


def test_payment_submission_allocates_partial_open_item(
    finance_database: Database,
) -> None:
    actor = Actor(identity="finance-service", role="finance_editor")
    payment = create_payment_entry(
        finance_database,
        actor,
        posting_date="2026-06-01",
        party_type="Supplier",
        party="SUP-00001",
        paid_from="2100 - Creditors - SCP",
        paid_to="1200 - Bank - SCP",
        paid_amount="500.00",
        references=[
            {
                "reference_doctype": "Purchase Invoice",
                "reference_name": "SCP-PINV-2026-00001",
                "allocated_amount": "500.00",
            }
        ],
    )

    submitted = submit_payment_entry(finance_database, actor, payment.name)

    assert submitted.status == "Submitted"
    with finance_database.connection() as connection:
        outstanding = connection.execute(
            "SELECT outstanding_minor FROM open_items WHERE reference_name = ?",
            ("SCP-PINV-2026-00001",),
        ).fetchone()[0]
    assert outstanding == 1200000
