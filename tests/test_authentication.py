import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from main import app
from settings import SettingsError, load_settings


@pytest.fixture
def configured_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, str]:
    values = {
        "api_key": "test-admin-key",
        "api_secret": "test-admin-secret",
    }
    monkeypatch.setenv("MOCK_ERP_DB_PATH", str(tmp_path / "mockerp.db"))
    monkeypatch.setenv(
        "MOCK_ERP_CREDENTIALS_JSON",
        json.dumps(
            {
                "credentials": [
                    {
                        "api_key": values["api_key"],
                        "api_secret": values["api_secret"],
                        "role": "admin",
                        "identity": "admin-service",
                    }
                ]
            }
        ),
    )
    monkeypatch.delenv("MOCK_ERP_CREDENTIALS_FILE", raising=False)
    return values


def test_missing_credential_source_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MOCK_ERP_CREDENTIALS_JSON", raising=False)
    monkeypatch.delenv("MOCK_ERP_CREDENTIALS_FILE", raising=False)

    with pytest.raises(SettingsError, match="credential source"):
        load_settings()


def test_credentials_can_be_loaded_from_a_secret_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    secret_file = tmp_path / "credentials.json"
    secret_file.write_text(
        json.dumps(
            {
                "credentials": [
                    {
                        "api_key": "file-key",
                        "api_secret": "file-secret",
                        "role": "finance_viewer",
                        "identity": "finance-service",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("MOCK_ERP_CREDENTIALS_FILE", str(secret_file))
    monkeypatch.delenv("MOCK_ERP_CREDENTIALS_JSON", raising=False)

    settings = load_settings()

    assert settings.credential_source == str(secret_file)
    assert settings.credentials[0].role == "finance_viewer"


def test_configured_token_authentication_still_uses_erpnext_shape(
    configured_environment: dict[str, str],
) -> None:
    headers = {
        "Authorization": "token "
        f"{configured_environment['api_key']}:{configured_environment['api_secret']}"
    }

    with TestClient(app) as client:
        response = client.get("/api/resource/Plugin Fixture", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["id"] == "plugin-fixture"
