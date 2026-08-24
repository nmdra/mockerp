from collections.abc import Iterator
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app

TEST_API_KEY = "test-admin-key"
TEST_API_SECRET = "test-admin-secret"


@pytest.fixture(autouse=True)
def runtime_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MOCK_ERP_DB_PATH", str(tmp_path / "mockerp.db"))
    monkeypatch.setenv(
        "MOCK_ERP_CREDENTIALS_JSON",
        json.dumps(
            {
                "credentials": [
                    {
                        "api_key": TEST_API_KEY,
                        "api_secret": TEST_API_SECRET,
                        "role": "admin",
                        "identity": "admin-service",
                    }
                ]
            }
        ),
    )
    monkeypatch.delenv("MOCK_ERP_CREDENTIALS_FILE", raising=False)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return {"Authorization": f"token {TEST_API_KEY}:{TEST_API_SECRET}"}
