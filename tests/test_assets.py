from pathlib import Path

import pytest

from database import Database
from seed import seed_platform
from services.assets import AssetError, capitalize_asset, create_asset, dispose_asset, transfer_asset
from services.authorization import Actor


@pytest.fixture
def asset_database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "mockerp.db")
    database.initialize()
    seed_platform(database)
    yield database
    database.close()


def test_asset_transfer_and_single_disposal_are_audited(
    asset_database: Database,
) -> None:
    actor = Actor(identity="finance-service", role="finance_manager")
    asset = create_asset(
        asset_database,
        actor,
        category="Computer Equipment",
        asset_name="SCP Finance Laptop",
        acquisition_date="2026-06-01",
        acquisition_cost="250000.00",
        location="Peliyagoda Head Office",
    )
    capitalized = capitalize_asset(asset_database, actor, asset.name)
    transferred = transfer_asset(
        asset_database,
        actor,
        capitalized.name,
        location="Katunayake Factory",
        effective_date="2026-07-01",
    )
    assert transferred.location == "Katunayake Factory"
    disposed = dispose_asset(
        asset_database,
        actor,
        transferred.name,
        disposal_date="2026-08-01",
        proceeds="10000.00",
    )
    assert disposed.status == "Disposed"
    with pytest.raises(AssetError, match="disposed"):
        dispose_asset(
            asset_database,
            actor,
            transferred.name,
            disposal_date="2026-08-02",
            proceeds="0",
        )
