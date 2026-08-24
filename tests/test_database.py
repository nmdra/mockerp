from pathlib import Path

import pytest

from database import Database
from seed import reset_and_seed, seed_platform
from settings import Settings, SettingsError


def test_database_initializes_foreign_keys_and_is_idempotent(tmp_path: Path) -> None:
    database = Database(tmp_path / "mockerp.db")

    database.initialize()
    first_tables = database.table_names()
    database.close()

    reopened = Database(tmp_path / "mockerp.db")
    reopened.initialize()

    assert reopened.foreign_keys_enabled() is True
    assert "schema_migrations" in first_tables
    assert "document_sequences" in first_tables
    assert "companies" in first_tables
    assert reopened.table_names() == first_tables

    reopened.close()


def test_database_transactions_roll_back_on_failure(tmp_path: Path) -> None:
    database = Database(tmp_path / "mockerp.db")
    database.initialize()

    with pytest.raises(RuntimeError, match="rollback"):
        with database.transaction() as connection:
            connection.execute(
                "INSERT INTO system_settings (setting_key, setting_value) VALUES (?, ?)",
                ("temporary", "value"),
            )
            raise RuntimeError("rollback")

    with database.connection() as connection:
        assert connection.execute(
            "SELECT 1 FROM system_settings WHERE setting_key = ?", ("temporary",)
        ).fetchone() is None

    database.close()


def test_document_names_are_monotonic(tmp_path: Path) -> None:
    database = Database(tmp_path / "mockerp.db")
    database.initialize()

    assert database.next_document_name("SCP-TEST") == "SCP-TEST-00001"
    assert database.next_document_name("SCP-TEST") == "SCP-TEST-00002"
    assert database.next_document_name("SCP-OTHER") == "SCP-OTHER-00001"

    database.close()


def test_seed_is_deterministic_and_repeatable(tmp_path: Path) -> None:
    database = Database(tmp_path / "mockerp.db")
    database.initialize()

    seed_platform(database)
    seed_platform(database)

    with database.connection() as connection:
        company = connection.execute(
            "SELECT name, currency FROM companies WHERE name = ?",
            ("Serendib Consumer Products (Pvt) Ltd",),
        ).fetchone()
        settings = connection.execute(
            "SELECT setting_key, setting_value FROM system_settings ORDER BY setting_key"
        ).fetchall()
        identities = connection.execute(
            "SELECT name, role FROM service_identities ORDER BY name"
        ).fetchall()

    assert tuple(company) == (
        "Serendib Consumer Products (Pvt) Ltd",
        "LKR",
    )
    assert [tuple(row) for row in settings] == [
        ("base_currency", "LKR"),
        ("fiscal_year_end", "2026-12-31"),
        ("fiscal_year_start", "2026-01-01"),
    ]
    assert [tuple(row) for row in identities] == [
        ("admin-service", "admin"),
        ("finance-service", "finance_editor"),
        ("hr-service", "hr_manager"),
        ("inventory-service", "inv_editor"),
    ]

    database.close()


def test_reset_and_seed_requires_development_mode(tmp_path: Path) -> None:
    database = Database(tmp_path / "mockerp.db")
    database.initialize()
    settings = Settings(
        database_path=tmp_path / "mockerp.db",
        credential_source="test",
        credentials=(),
        sessions=(),
        basic_credentials=(),
        environment="test",
        allow_reset=True,
    )

    with pytest.raises(SettingsError, match="development"):
        reset_and_seed(database, settings)

    database.close()
