from pathlib import Path

import pytest

from database import Database
from seed import seed_platform
from services.authorization import Actor
from services.purchasing import (
    PurchasingError,
    approve_purchase_order,
    create_material_request,
    create_purchase_order,
    create_purchase_receipt,
    create_purchase_invoice,
    submit_purchase_receipt,
    submit_purchase_invoice,
)


@pytest.fixture
def purchasing_database(tmp_path: Path) -> Database:
    database = Database(tmp_path / "mockerp.db")
    database.initialize()
    seed_platform(database)
    yield database
    database.close()


def test_purchase_flow_tracks_partial_receipt_billing_and_payment(
    purchasing_database: Database,
) -> None:
    requester = Actor(identity="procurement-service", role="procurement_manager")
    finance = Actor(identity="finance-service", role="finance_manager")
    administrator = Actor(identity="admin-service", role="admin")

    request = create_material_request(
        purchasing_database,
        requester,
        posting_date="2026-06-01",
        items=[{"item_code": "PKG-BOTTLE-001", "qty": 4000, "warehouse": "Peliyagoda Main"}],
    )
    order = create_purchase_order(
        purchasing_database,
        requester,
        material_request_name=request.name,
        supplier="SCP-Local Packaging",
        transaction_date="2026-06-01",
        items=[
            {
                "item_code": "PKG-BOTTLE-001",
                "qty": 4000,
                "warehouse": "Peliyagoda Main",
                "rate": "35.00",
            }
        ],
    )
    assert approve_purchase_order(purchasing_database, finance, order.name).status == "Pending Approval"
    assert approve_purchase_order(purchasing_database, administrator, order.name).status == "Approved"

    receipt = create_purchase_receipt(
        purchasing_database,
        requester,
        purchase_order_name=order.name,
        items=[{"item_code": "PKG-BOTTLE-001", "qty": 4, "warehouse": "Peliyagoda Main", "rate": "35.00"}],
    )
    submit_purchase_receipt(purchasing_database, requester, receipt.name)
    with pytest.raises(PurchasingError, match="exceed"):
        create_purchase_receipt(
            purchasing_database,
            requester,
            purchase_order_name=order.name,
            items=[{"item_code": "PKG-BOTTLE-001", "qty": 3997, "warehouse": "Peliyagoda Main", "rate": "35.00"}],
        )

    invoice = create_purchase_invoice(
        purchasing_database,
        finance,
        purchase_receipt_name=receipt.name,
        items=[{"item_code": "PKG-BOTTLE-001", "qty": 4, "rate": "35.00"}],
    )
    submitted = submit_purchase_invoice(purchasing_database, finance, invoice.name)
    assert submitted.status == "Submitted"
    assert submitted.outstanding > 0
