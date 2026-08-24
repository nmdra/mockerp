from fastapi.testclient import TestClient


def test_scp_organization_resources_are_seeded(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    branches = client.get("/api/resource/Branch", headers=admin_headers)
    departments = client.get("/api/resource/Department", headers=admin_headers)
    users = client.get("/api/resource/User", headers=admin_headers)

    assert branches.status_code == 200
    assert [row["name"] for row in branches.json()["data"]] == [
        "Peliyagoda Head Office",
        "Peliyagoda Main Warehouse",
        "Katunayake Factory",
        "Katunayake Raw Material Warehouse",
        "Kandy Distribution Centre",
        "Galle Distribution Centre",
    ]
    assert departments.status_code == 200
    assert {row["name"] for row in departments.json()["data"]} >= {
        "Finance",
        "Human Resources",
        "Procurement",
        "Production",
        "Warehouse",
    }
    assert users.status_code == 200
    assert all("api_secret" not in row for row in users.json()["data"])


def test_organization_http_routes_record_audit_events(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    response = client.post(
        "/api/resource/Approval Request",
        headers=admin_headers,
        json={
            "document_type": "Purchase Order",
            "reference_name": "PUR-ORD-2026-00001",
            "amount": 150000,
        },
    )
    audit = client.get("/api/resource/Audit Event", headers=admin_headers)

    assert response.status_code == 201
    assert response.json()["data"]["status"] == "PENDING_APPROVAL"
    assert audit.status_code == 200
    assert any(
        row["action"] == "create" for row in audit.json()["data"]
    )
