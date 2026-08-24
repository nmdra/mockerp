from fastapi.testclient import TestClient


def test_manufacturing_routes_expose_floor_cleaner_bom(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get("/api/resource/BOM", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["data"][0]["item"] == "FG-CLEANER-5L"
