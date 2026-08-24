from pathlib import Path

import yaml


def test_openapi_covers_the_supported_scp_contract() -> None:
    document = yaml.safe_load(
        Path(__file__).parents[1].joinpath("openapi.yaml").read_text(encoding="utf-8")
    )

    assert document["openapi"] == "3.0.3"
    assert document["servers"][0]["url"].endswith("/api")
    for path in (
        "/resource/Company",
        "/resource/Journal Entry/{name}/submit",
        "/resource/Attendance",
        "/resource/Item",
        "/resource/Stock Entry/{name}/submit",
        "/resource/Purchase Invoice/{name}/submit",
        "/resource/Sales Invoice/{name}/submit",
        "/resource/Production Order/{name}/submit",
        "/resource/Asset/{name}/dispose",
        "/report/trial-balance",
    ):
        assert path in document["paths"], path

    serialized = Path(__file__).parents[1].joinpath("openapi.yaml").read_text(
        encoding="utf-8"
    )
    assert "adm_key_001" not in serialized
    assert "api_secret: " not in serialized
