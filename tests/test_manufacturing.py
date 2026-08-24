from pathlib import Path

import pytest

from database import Database
from seed import seed_platform
from services.authorization import Actor
from services.manufacturing import ManufacturingError, create_production_order, submit_production_order


@pytest.fixture
def manufacturing_database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "mockerp.db")
    database.initialize()
    seed_platform(database)
    yield database
    database.close()


def test_floor_cleaner_bom_consumes_raw_material_and_receives_finished_goods(
    manufacturing_database: Database,
) -> None:
    actor = Actor(identity="inventory-service", role="inventory_manager")
    order = create_production_order(
        manufacturing_database,
        actor,
        item_code="FG-CLEANER-5L",
        qty=5,
        source_warehouse="Katunayake Raw Material",
        target_warehouse="Katunayake Finished Goods",
    )

    completed = submit_production_order(manufacturing_database, actor, order.name)

    assert completed.status == "Completed"
    with manufacturing_database.connection() as connection:
        finished = connection.execute(
            "SELECT actual_qty FROM bins WHERE item_code = ? AND warehouse = ?",
            ("FG-CLEANER-5L", "Katunayake Finished Goods"),
        ).fetchone()[0]
    assert finished == 5


def test_production_requires_active_bom(manufacturing_database: Database) -> None:
    actor = Actor(identity="inventory-service", role="inventory_manager")
    with pytest.raises(ManufacturingError, match="BOM"):
        create_production_order(
            manufacturing_database,
            actor,
            item_code="FG-TEA-001",
            qty=1,
            source_warehouse="Katunayake Raw Material",
            target_warehouse="Katunayake Finished Goods",
        )
