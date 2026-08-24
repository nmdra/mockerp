from fastapi.testclient import TestClient


def test_asset_category_route_is_seeded(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get("/api/resource/Asset Category", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["data"]
