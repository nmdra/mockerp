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
_EMPLOYEES = (
    (
        "EMP-SCP-00001",
        "Kavindu Jayasekara",
        "Kavindu",
        "Jayasekara",
        "Peliyagoda Head Office",
        "Finance",
        "Officer",
        "Full-time",
        "employee-service",
        "manager-service",
        "1992-03-15",
        "2021-06-01",
    ),
)
_LEAVE_TYPES = (("Annual Leave", 20), ("Sick Leave", 10))
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
    seed_hr(database)
    seed_payroll(database)


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


def seed_payroll(database: Database) -> None:
    with database.transaction() as connection:
        connection.executemany(
            """
            INSERT OR IGNORE INTO salary_components (name, component_type, is_active)
            VALUES (?, ?, 1)
            """,
            [("Basic Salary", "Earning"), ("Transport Allowance", "Earning"), ("Employee Welfare", "Deduction")],
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO salary_structures
                (name, company_name, currency, is_active)
            VALUES ('Officer Grade A', ?, 'LKR', 1)
            """,
            (_COMPANY[0],),
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO salary_structure_components
                (structure_name, component_name, amount_minor, percentage)
            VALUES ('Officer Grade A', ?, ?, NULL)
            """,
            [("Basic Salary", 0), ("Transport Allowance", 500000), ("Employee Welfare", 100000)],
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO salary_assignments
                (employee_name, structure_name, base_amount_minor,
                 from_date, to_date, is_active)
            VALUES ('EMP-SCP-00001', 'Officer Grade A', 8500000, '2026-01-01', NULL, 1)
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO salary_slips
                (name, employee_name, start_date, end_date, posting_date,
                 gross_pay_minor, total_deduction_minor, net_pay_minor,
                 status, docstatus, owner_identity)
            VALUES ('SCP-SAL-2026-05-00001', 'EMP-SCP-00001',
                    '2026-05-01', '2026-05-31', '2026-05-31',
                    9000000, 100000, 8900000, 'Draft', 0, 'hr-service')
            """
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO salary_slip_lines
                (salary_slip_name, component_name, component_type, amount_minor)
            VALUES ('SCP-SAL-2026-05-00001', ?, ?, ?)
            """,
            [("Basic Salary", "Earning", 8500000), ("Transport Allowance", "Earning", 500000), ("Employee Welfare", "Deduction", 100000)],
        )
        connection.execute(
            "INSERT OR IGNORE INTO document_sequences (series, next_value) VALUES ('SCP-SAL', 2)"
        )


def seed_hr(database: Database) -> None:
    with database.transaction() as connection:
        connection.executemany(
            """
            INSERT OR IGNORE INTO employees
                (name, employee_name, first_name, last_name, company_name,
                 branch_name, department_name, designation, employment_type,
                 user_identity, supervisor_identity, date_of_birth,
                 date_of_joining, status, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active', 1)
            """,
            [
                (
                    name,
                    employee_name,
                    first_name,
                    last_name,
                    _COMPANY[0],
                    branch,
                    department,
                    designation,
                    employment_type,
                    user_identity,
                    supervisor,
                    date_of_birth,
                    date_of_joining,
                )
                for (
                    name,
                    employee_name,
                    first_name,
                    last_name,
                    branch,
                    department,
                    designation,
                    employment_type,
                    user_identity,
                    supervisor,
                    date_of_birth,
                    date_of_joining,
                ) in _EMPLOYEES
            ],
        )
        connection.executemany(
            "INSERT OR IGNORE INTO leave_types (name, max_days, is_active) VALUES (?, ?, 1)",
            _LEAVE_TYPES,
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO leave_allocations
                (employee_name, leave_type, from_date, to_date, total_days, used_days)
            VALUES ('EMP-SCP-00001', 'Annual Leave', '2026-01-01', '2026-12-31', 20, 3)
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO leave_allocations
                (employee_name, leave_type, from_date, to_date, total_days, used_days)
            VALUES ('EMP-SCP-00001', 'Sick Leave', '2026-01-01', '2026-12-31', 10, 0)
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO leave_applications
                (name, employee_name, leave_type, from_date, to_date, total_days,
                 half_day, status, docstatus, description, posting_date,
                 approval_request_id, owner_identity)
            VALUES ('SCP-LA-2026-00001', 'EMP-SCP-00001', 'Annual Leave',
                    '2026-06-10', '2026-06-12', 3, 0, 'Approved', 1,
                    'Fictional annual leave fixture', '2026-05-15', NULL,
                    'employee-service')
            """
        )
        connection.execute(
            "INSERT OR IGNORE INTO document_sequences (series, next_value) VALUES ('SCP-LA', 2)"
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
