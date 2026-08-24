from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Iterator[TestClient]:
    monkeypatch.setenv("MOCK_ERP_DB_PATH", str(tmp_path / "mockerp.db"))
    with TestClient(app) as test_client:
        yield test_client
