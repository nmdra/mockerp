from __future__ import annotations

import argparse

from database import Database
from settings import Settings, SettingsError, load_settings

_COMPANY = (
    "Serendib Consumer Products (Pvt) Ltd",
    "LKR",
    "Sri Lanka",
)
_SETTINGS = (
    ("base_currency", "LKR"),
    ("fiscal_year_start", "2026-01-01"),
    ("fiscal_year_end", "2026-12-31"),
)
_IDENTITIES = (
    ("admin-service", "admin"),
    ("finance-service", "finance_editor"),
    ("hr-service", "hr_manager"),
    ("inventory-service", "inv_editor"),
)


def seed_platform(database: Database) -> None:
    with database.transaction() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO companies (name, currency, country, is_active)
            VALUES (?, ?, ?, 1)
            """,
            _COMPANY,
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO system_settings (setting_key, setting_value)
            VALUES (?, ?)
            """,
            _SETTINGS,
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO service_identities (name, role, is_active)
            VALUES (?, ?, 1)
            """,
            _IDENTITIES,
        )


def reset_and_seed(database: Database, settings: Settings) -> None:
    if settings.environment != "development" or not settings.allow_reset:
        raise SettingsError(
            "database reset is available only in development with "
            "MOCK_ERP_ALLOW_RESET=true"
        )
    database.reset()
    seed_platform(database)


def _main() -> None:
    parser = argparse.ArgumentParser(description="Initialize or reset MockERP data")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="drop and recreate the database (development only)",
    )
    args = parser.parse_args()
    settings = load_settings()
    database = Database(settings.database_path)
    try:
        database.initialize()
        if args.reset:
            reset_and_seed(database, settings)
        else:
            seed_platform(database)
    finally:
        database.close()


if __name__ == "__main__":
    _main()
