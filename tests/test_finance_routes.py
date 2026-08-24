from fastapi.testclient import TestClient


def test_finance_routes_expose_seeded_scp_documents(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    journal_entries = client.get("/api/resource/Journal Entry", headers=admin_headers)
    payments = client.get("/api/resource/Payment Entry", headers=admin_headers)

    assert journal_entries.status_code == 200
    assert journal_entries.json()["data"][0]["name"] == "SCP-JV-2026-00001"
    assert payments.status_code == 200
    assert payments.json()["data"][0]["name"] == "SCP-PAY-2026-00001"


def test_finance_route_rejects_unbalanced_submission(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    created = client.post(
        "/api/resource/Journal Entry",
        headers=admin_headers,
        json={
            "posting_date": "2026-06-01",
            "remark": "Route test",
            "accounts": [
                {"account": "1100 - Bank - SCP", "debit": "10", "credit": "0"},
                {"account": "2100 - Creditors - SCP", "debit": "0", "credit": "9"},
            ],
        },
    )

    assert created.status_code == 201
    name = created.json()["data"]["name"]
    submitted = client.post(
        f"/api/resource/Journal Entry/{name}/submit", headers=admin_headers
    )

    assert submitted.status_code == 422
    assert "balanced" in submitted.json()["message"]
