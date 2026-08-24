from fastapi.testclient import TestClient


def test_purchase_invoice_uses_sqlite_envelope(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get("/api/resource/Purchase Invoice", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["data"][0]["name"] == "SCP-PINV-2026-00001"
    assert response.json()["data"][0]["company"] == "Serendib Consumer Products (Pvt) Ltd"


def test_purchase_order_route_requires_approval_for_high_value_order(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get("/api/resource/Purchase Order", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["data"][0]["status"] == "Approved"
