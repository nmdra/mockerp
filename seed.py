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
_BRANCHES = (
    ("Peliyagoda Head Office", "Peliyagoda office, Western Province"),
    ("Peliyagoda Main Warehouse", "Peliyagoda warehouse, Western Province"),
    ("Katunayake Factory", "Katunayake factory, Western Province"),
    (
        "Katunayake Raw Material Warehouse",
        "Katunayake raw-material warehouse, Western Province",
    ),
    ("Kandy Distribution Centre", "Kandy distribution centre, Central Province"),
    ("Galle Distribution Centre", "Galle distribution centre, Southern Province"),
)
_DEPARTMENTS = (
    ("Finance", None, "Peliyagoda Head Office"),
    ("Human Resources", None, "Peliyagoda Head Office"),
    ("Procurement", None, "Peliyagoda Head Office"),
    ("Sales and Distribution", None, "Peliyagoda Head Office"),
    ("Production", None, "Katunayake Factory"),
    ("Warehouse", None, "Peliyagoda Main Warehouse"),
    ("Quality Assurance", None, "Katunayake Factory"),
    ("Raw Materials", "Warehouse", "Katunayake Raw Material Warehouse"),
)
_DESIGNATIONS = ("Managing Director", "Finance Manager", "HR Manager", "Department Manager", "Officer")
_EMPLOYMENT_TYPES = ("Full-time", "Part-time", "Contract")
_ROLES = (
    ("admin", "System administrator"),
    ("finance_manager", "Finance approval manager"),
    ("finance_editor", "Finance document editor"),
    ("hr_manager", "Human resources manager"),
    ("inventory_manager", "Inventory manager"),
    ("inv_editor", "Inventory editor"),
    ("procurement_manager", "Procurement manager"),
    ("department_manager", "Department manager"),
    ("employee", "Employee self-service user"),
)
_USERS = (
    ("admin-service", "SCP Administrator", "admin-service@scp.example"),
    ("finance-service", "SCP Finance Service", "finance-service@scp.example"),
    ("hr-service", "SCP HR Service", "hr-service@scp.example"),
    ("inventory-service", "SCP Inventory Service", "inventory-service@scp.example"),
    ("procurement-service", "SCP Procurement Service", "procurement-service@scp.example"),
    ("employee-service", "SCP Employee Service", "employee-service@scp.example"),
    ("manager-service", "SCP Department Manager", "manager-service@scp.example"),
)
_USER_ROLES = (
    ("admin-service", "admin"),
    ("finance-service", "finance_manager"),
    ("finance-service", "finance_editor"),
    ("hr-service", "hr_manager"),
    ("inventory-service", "inventory_manager"),
    ("inventory-service", "inv_editor"),
    ("procurement-service", "procurement_manager"),
    ("employee-service", "employee"),
    ("manager-service", "department_manager"),
)
_APPROVAL_RULES = (
    ("Purchase Order", 1, "finance_manager", 0),
    ("Purchase Order", 2, "admin", 100000),
    ("Leave Application", 1, "department_manager", 0),
    ("Leave Application", 2, "hr_manager", 0),
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
    seed_organization(database)


def seed_organization(database: Database) -> None:
    with database.transaction() as connection:
        connection.executemany(
            """
            INSERT OR IGNORE INTO branches (name, company_name, address, is_active)
            VALUES (?, ?, ?, 1)
            """,
            [(name, _COMPANY[0], address) for name, address in _BRANCHES],
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO departments
                (name, company_name, parent_department, branch_name, is_group, is_active)
            VALUES (?, ?, ?, ?, 0, 1)
            """,
            [
                (name, _COMPANY[0], parent, branch)
                for name, parent, branch in _DEPARTMENTS
            ],
        )
        connection.executemany(
            "INSERT OR IGNORE INTO designations (name, is_active) VALUES (?, 1)",
            [(name,) for name in _DESIGNATIONS],
        )
        connection.executemany(
            "INSERT OR IGNORE INTO employment_types (name, is_active) VALUES (?, 1)",
            [(name,) for name in _EMPLOYMENT_TYPES],
        )
        connection.executemany(
            "INSERT OR IGNORE INTO roles (name, description) VALUES (?, ?)",
            _ROLES,
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO users (identity, full_name, email, is_active)
            VALUES (?, ?, ?, 1)
            """,
            _USERS,
        )
        connection.executemany(
            "INSERT OR IGNORE INTO user_roles (identity, role) VALUES (?, ?)",
            _USER_ROLES,
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO approval_rules
                (document_type, sequence_no, role, minimum_amount, is_active)
            VALUES (?, ?, ?, ?, 1)
            """,
            _APPROVAL_RULES,
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
