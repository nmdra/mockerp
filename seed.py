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
_ACCOUNTS = (
    ("1000 - Assets - SCP", "1000", "Asset", None, 1),
    ("1100 - Bank - SCP", "1100", "Asset", "1000 - Assets - SCP", 0),
    ("1200 - Bank - SCP", "1200", "Asset", "1000 - Assets - SCP", 0),
    ("2000 - Liabilities - SCP", "2000", "Liability", None, 1),
    ("2100 - Creditors - SCP", "2100", "Liability", "2000 - Liabilities - SCP", 0),
    ("4000 - Income - SCP", "4000", "Income", None, 1),
    ("4100 - Sales - SCP", "4100", "Income", "4000 - Income - SCP", 0),
    ("5000 - Expenses - SCP", "5000", "Expense", None, 1),
    ("5100 - COGS - SCP", "5100", "Expense", "5000 - Expenses - SCP", 0),
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
    seed_finance(database)


def seed_finance(database: Database) -> None:
    with database.transaction() as connection:
        connection.executemany(
            """
            INSERT OR IGNORE INTO accounts
                (name, account_number, root_type, parent_account,
                 account_currency, company_name, is_group, is_active)
            VALUES (?, ?, ?, ?, 'LKR', ?, ?, 1)
            """,
            [
                (name, number, root_type, parent, _COMPANY[0], is_group)
                for name, number, root_type, parent, is_group in _ACCOUNTS
            ],
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO journal_entries
                (name, posting_date, remark, docstatus, status,
                 total_debit_minor, total_credit_minor, owner_identity)
            VALUES ('SCP-JV-2026-00001', '2026-01-01', 'Opening SCP balances', 1,
                    'Submitted', 5000000, 5000000, 'admin-service')
            """
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO journal_entry_accounts
                (journal_entry_name, account, debit_minor, credit_minor)
            VALUES ('SCP-JV-2026-00001', ?, ?, ?)
            """,
            [
                ("1100 - Bank - SCP", 5000000, 0),
                ("2100 - Creditors - SCP", 0, 5000000),
            ],
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO gl_entries
                (voucher_type, voucher_no, account, posting_date,
                 debit_minor, credit_minor, is_reversal)
            VALUES ('Journal Entry', 'SCP-JV-2026-00001', '1100 - Bank - SCP',
                    '2026-01-01', 5000000, 0, 0)
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO gl_entries
                (voucher_type, voucher_no, account, posting_date,
                 debit_minor, credit_minor, is_reversal)
            VALUES ('Journal Entry', 'SCP-JV-2026-00001', '2100 - Creditors - SCP',
                    '2026-01-01', 0, 5000000, 0)
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO payment_entries
                (name, payment_type, posting_date, party_type, party,
                 paid_from, paid_to, paid_amount_minor, received_amount_minor,
                 docstatus, status, owner_identity)
            VALUES ('SCP-PAY-2026-00001', 'Pay', '2026-01-01', 'Supplier', 'SUP-00001',
                    '2100 - Creditors - SCP', '1200 - Bank - SCP',
                    125000, 125000, 0, 'Draft', 'finance-service')
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO open_items
                (reference_doctype, reference_name, party_type, party,
                 total_minor, outstanding_minor, account)
            VALUES ('Purchase Invoice', 'SCP-PINV-2026-00001', 'Supplier',
                    'SUP-00001', 1250000, 1250000, '2100 - Creditors - SCP')
            """
        )
        connection.execute(
            "INSERT OR IGNORE INTO document_sequences (series, next_value) VALUES ('SCP-JV', 2)"
        )
        connection.execute(
            "INSERT OR IGNORE INTO document_sequences (series, next_value) VALUES ('SCP-PAY', 2)"
        )


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
