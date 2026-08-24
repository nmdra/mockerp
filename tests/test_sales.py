from pathlib import Path

import pytest

from database import Database
from seed import seed_platform
from services.authorization import Actor
from services.sales import (
    SalesError,
    create_sales_order,
    create_delivery_note,
    create_sales_invoice,
    submit_delivery_note,
    submit_sales_invoice,
)


@pytest.fixture
def sales_database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "mockerp.db")
    database.initialize()
    seed_platform(database)
    yield database
    database.close()


def test_sales_flow_supports_partial_delivery_and_billing(
    sales_database: Database,
) -> None:
    actor = Actor(identity="inventory-service", role="inventory_manager")
    finance = Actor(identity="finance-service", role="finance_manager")
    order = create_sales_order(
        sales_database,
        actor,
        customer="Southern Hotels",
        transaction_date="2026-06-01",
        items=[
            {
                "item_code": "FG-TEA-001",
                "qty": 10,
                "warehouse": "Katunayake Finished Goods",
                "rate": "850.00",
            }
        ],
    )
    delivery = create_delivery_note(
        sales_database,
        actor,
        sales_order_name=order.name,
        items=[
            {
                "item_code": "FG-TEA-001",
                "qty": 4,
                "warehouse": "Katunayake Finished Goods",
                "rate": "850.00",
            }
        ],
    )
    submit_delivery_note(sales_database, actor, delivery.name)
    with pytest.raises(SalesError, match="exceed"):
        create_delivery_note(
            sales_database,
            actor,
            sales_order_name=order.name,
            items=[
                {
                    "item_code": "FG-TEA-001",
                    "qty": 7,
                    "warehouse": "Katunayake Finished Goods",
                    "rate": "850.00",
                }
            ],
        )
    invoice = create_sales_invoice(
        sales_database,
        finance,
        delivery_note_name=delivery.name,
        items=[{"item_code": "FG-TEA-001", "qty": 4, "rate": "850.00"}],
    )
    submitted = submit_sales_invoice(sales_database, finance, invoice.name)

    assert submitted.status == "Submitted"
    assert submitted.outstanding > 0
