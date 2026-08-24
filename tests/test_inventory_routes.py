from fastapi.testclient import TestClient


def test_bin_route_reads_sqlite_projection(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get(
        "/api/resource/Bin",
        headers=admin_headers,
        params={"filters": '[["Bin","item_code","=","FG-TEA-001"]]'},
    )

    assert response.status_code == 200
    assert response.json()["data"][0]["item_code"] == "FG-TEA-001"
    assert any(
        row["warehouse"] == "Katunayake Finished Goods"
        for row in response.json()["data"]
    )
