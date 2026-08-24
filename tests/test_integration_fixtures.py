from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

ADMIN_HEADERS = {"Authorization": "token adm_key_001:adm_sec_stu901"}


def test_plugin_fixture_is_stable_and_authenticated(client: TestClient) -> None:
    response = client.get("/api/resource/Plugin Fixture", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "data": {"id": "plugin-fixture", "state": "source"}
    }


def test_echo_preserves_payload_and_readback(client: TestClient) -> None:
    payload = {"nested": {"value": 7}, "items": ["a", "b"]}

    response = client.post(
        "/api/integration/echo", headers=ADMIN_HEADERS, json=payload
    )
    readback = client.get("/api/integration/echo/last", headers=ADMIN_HEADERS)

    assert response.status_code == 200
    assert response.json() == {"data": payload}
    assert "role" not in response.json()["data"]
    assert readback.status_code == 200
    assert readback.json() == {"data": payload}


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/api/resource/Plugin Fixture"),
        ("post", "/api/integration/echo"),
        ("get", "/api/integration/echo/last"),
    ],
)
def test_fixture_routes_require_authentication(
    client: TestClient, method: str, path: str
) -> None:
    response = client.request(
        method, path, headers={}, json={} if method == "post" else None
    )

    assert response.status_code == 401
    assert response.json()["exc_type"] == "AuthenticationError"


def test_echo_rejects_non_object_payload(client: TestClient) -> None:
    response = client.post(
        "/api/integration/echo", headers=ADMIN_HEADERS, json=["not", "an", "object"]
    )

    assert response.status_code == 422


def test_openapi_describes_fixture_contract() -> None:
    document = yaml.safe_load(
        Path(__file__).parents[1].joinpath("openapi.yaml").read_text(encoding="utf-8")
    )

    assert document["components"]["securitySchemes"]["TokenAuth"]
    assert "/resource/Plugin Fixture" in document["paths"]
    assert "/integration/echo" in document["paths"]
    assert "/integration/echo/last" in document["paths"]
    assert document["paths"]["/integration/echo"]["post"]["security"] == [
        {"TokenAuth": []}
    ]
