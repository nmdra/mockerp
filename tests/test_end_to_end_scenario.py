from fastapi.testclient import TestClient


def test_report_routes_expose_role_gated_scp_summaries(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    trial = client.get("/api/report/trial-balance", headers=admin_headers)
    stock = client.get("/api/report/stock", headers=admin_headers)
    audit = client.get("/api/report/audit?limit=5", headers=admin_headers)

    assert trial.status_code == 200
    assert stock.status_code == 200
    assert audit.status_code == 200
    assert len(audit.json()["data"]) <= 5
