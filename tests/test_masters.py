from fastapi.testclient import TestClient


def test_scp_master_data_is_seeded(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    items = client.get("/api/resource/Item", headers=admin_headers)
    suppliers = client.get("/api/resource/Supplier", headers=admin_headers)
    warehouses = client.get("/api/resource/Warehouse", headers=admin_headers)

    assert items.status_code == 200
    assert {row["name"] for row in items.json()["data"]} >= {
        "RM-SUGAR-001",
        "FG-TEA-001",
        "SPARE-BELT-001",
    }
    assert suppliers.status_code == 200
    assert suppliers.json()["data"][0]["name"] == "SCP-Local Packaging"
    assert warehouses.status_code == 200
    assert {row["name"] for row in warehouses.json()["data"]} >= {
        "Katunayake Raw Material",
        "Katunayake Finished Goods",
        "Peliyagoda Main",
        "Kandy DC",
        "Galle DC",
    }


def test_item_read_includes_batch_and_warehouse_eligibility(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.get("/api/resource/Item/FG-TEA-001", headers=admin_headers)

    assert response.status_code == 200
    item = response.json()["data"]
    assert item["has_batch_no"] == 1
    assert "source_warehouses" in item
    assert "target_warehouses" in item
