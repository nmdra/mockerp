from pathlib import Path

import pytest

from database import Database
from seed import seed_platform
from services.authorization import Actor
from services.inventory import (
    InventoryError,
    cancel_stock_entry,
    create_stock_entry,
    submit_stock_entry,
)


@pytest.fixture
def inventory_database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "mockerp.db")
    database.initialize()
    seed_platform(database)
    yield database
    database.close()


def test_stock_receipt_transfer_and_cancellation_preserve_quantities(
    inventory_database: Database,
) -> None:
    actor = Actor(identity="inventory-service", role="inventory_manager")
    receipt = create_stock_entry(
        inventory_database,
        actor,
        entry_type="Material Receipt",
        posting_date="2026-06-01",
        items=[
            {
                "item_code": "RM-SUGAR-001",
                "target_warehouse": "Katunayake Raw Material",
                "qty": 100,
                "rate": "250.00",
            }
        ],
    )
    submit_stock_entry(inventory_database, actor, receipt.name)
    transfer = create_stock_entry(
        inventory_database,
        actor,
        entry_type="Material Transfer",
        posting_date="2026-06-02",
        items=[
            {
                "item_code": "RM-SUGAR-001",
                "source_warehouse": "Katunayake Raw Material",
                "target_warehouse": "Katunayake WIP",
                "qty": 40,
                "rate": "250.00",
            }
        ],
    )
    submit_stock_entry(inventory_database, actor, transfer.name)

    with inventory_database.connection() as connection:
        raw = connection.execute(
            "SELECT actual_qty FROM bins WHERE item_code = ? AND warehouse = ?",
            ("RM-SUGAR-001", "Katunayake Raw Material"),
        ).fetchone()[0]
        wip = connection.execute(
            "SELECT actual_qty FROM bins WHERE item_code = ? AND warehouse = ?",
            ("RM-SUGAR-001", "Katunayake WIP"),
        ).fetchone()[0]
    assert (raw, wip) == (60, 40)

    cancel_stock_entry(inventory_database, actor, transfer.name)
    with inventory_database.connection() as connection:
        raw_after = connection.execute(
            "SELECT actual_qty FROM bins WHERE item_code = ? AND warehouse = ?",
            ("RM-SUGAR-001", "Katunayake Raw Material"),
        ).fetchone()[0]
        wip_after = connection.execute(
            "SELECT actual_qty FROM bins WHERE item_code = ? AND warehouse = ?",
            ("RM-SUGAR-001", "Katunayake WIP"),
        ).fetchone()[0]
    assert (raw_after, wip_after) == (100, 0)


def test_stock_issue_cannot_make_bin_negative(inventory_database: Database) -> None:
    actor = Actor(identity="inventory-service", role="inventory_manager")
    entry = create_stock_entry(
        inventory_database,
        actor,
        entry_type="Material Issue",
        posting_date="2026-06-01",
        items=[
            {
                "item_code": "FG-TEA-001",
                "source_warehouse": "Katunayake Finished Goods",
                "qty": 1000,
                "rate": "850.00",
            }
        ],
    )

    with pytest.raises(InventoryError, match="negative"):
        submit_stock_entry(inventory_database, actor, entry.name)
