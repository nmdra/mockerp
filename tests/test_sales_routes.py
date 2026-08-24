from fastapi.testclient import TestClient


def test_sales_order_seed_is_available(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get("/api/resource/Sales Order", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["data"][0]["customer"] == "Southern Hotels"
