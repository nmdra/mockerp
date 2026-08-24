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
_CUSTOMERS = (
    ("SCP-Wholesale Distributors", "SCP Wholesale Distributors", "Wholesale", "Western"),
    ("SCP-Kandy Retail Network", "SCP Kandy Retail Network", "Retail", "Central"),
    ("Southern Hotels", "Southern Hotels", "Hospitality", "Southern"),
)
_SUPPLIERS = (
    ("SCP-Local Packaging", "SCP Local Packaging", "Packaging", "Sri Lanka"),
    ("SCP-Imported Ingredients", "SCP Imported Ingredients", "Raw Materials", "Sri Lanka"),
)
_ITEM_GROUPS = (
    ("Raw Materials", None),
    ("Packaging", None),
    ("Finished Goods", None),
    ("Imported Products", None),
    ("Office Supplies", None),
    ("Spare Parts", None),
    ("WIP", None),
)
_UOMS = (("Nos", 1), ("Kg", 0), ("Litre", 0), ("Box", 1))
_WAREHOUSES = (
    ("Katunayake Raw Material", None, "Raw Material"),
    ("Katunayake WIP", None, "Work In Progress"),
    ("Katunayake Finished Goods", None, "Finished Goods"),
    ("Katunayake Scrap", None, "Scrap"),
    ("Peliyagoda Main", None, "Distribution"),
    ("Kandy DC", None, "Distribution"),
    ("Galle DC", None, "Distribution"),
)
_ITEMS = (
    ("RM-SUGAR-001", "Ceylon Cane Sugar", "Raw Materials", "Kg", 250, "Moving Average", 0, 1000, 5000),
    ("RM-CLEANER-CONC-001", "Floor Cleaner Concentrate", "Raw Materials", "Litre", 420, "Moving Average", 0, 100, 500),
    ("PKG-BOTTLE-001", "Food Grade Bottle", "Packaging", "Nos", 35, "Moving Average", 0, 5000, 20000),
    ("FG-TEA-001", "Serendib Breakfast Tea", "Finished Goods", "Box", 850, "FIFO", 1, 500, 2000),
    ("FG-CLEANER-5L", "Serendib Floor Cleaner 5L", "Finished Goods", "Nos", 1450, "FIFO", 1, 50, 200),
    ("IMP-SPICE-001", "Imported Cinnamon Blend", "Imported Products", "Kg", 1800, "FIFO", 1, 100, 500),
    ("OFF-PAPER-001", "Office Copy Paper", "Office Supplies", "Box", 2200, "Moving Average", 0, 20, 100),
    ("SPARE-BELT-001", "Factory Conveyor Belt", "Spare Parts", "Nos", 12500, "Moving Average", 0, 2, 5),
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
    ("1300 - Debtors - SCP", "1300", "Asset", "1000 - Assets - SCP", 0),
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
    seed_masters(database)
    seed_inventory(database)
    seed_purchasing(database)
    seed_sales(database)
    seed_manufacturing(database)
    seed_assets(database)


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


def seed_assets(database: Database) -> None:
    with database.transaction() as connection:
        connection.executemany(
            """
            INSERT OR IGNORE INTO asset_categories
                (name, asset_account, accumulated_depreciation_account,
                 depreciation_expense_account, default_useful_life_months, is_active)
            VALUES (?, '1000 - Assets - SCP', '2000 - Liabilities - SCP',
                    '5100 - COGS - SCP', ?, 1)
            """,
            [
                ("Vehicles", 60),
                ("Material Handling Equipment", 60),
                ("Factory Machinery", 120),
                ("Computer Equipment", 36),
                ("Furniture", 60),
                ("Air Conditioners", 60),
                ("Generators", 120),
            ],
        )
        samples = (
            ("SCP-AST-TRUCK-001", "Vehicles", "SCP Delivery Truck 001", 8500000, "Peliyagoda Main"),
            ("SCP-AST-FORKLIFT-001", "Material Handling Equipment", "SCP Forklift 001", 2200000, "Katunayake Raw Material"),
            ("SCP-AST-MIXER-001", "Factory Machinery", "SCP Mixing Machine 001", 12500000, "Katunayake Factory"),
            ("SCP-AST-COMPUTER-001", "Computer Equipment", "SCP Office Computer 001", 250000, "Peliyagoda Head Office"),
            ("SCP-AST-FURNITURE-001", "Furniture", "SCP Office Furniture 001", 180000, "Peliyagoda Head Office"),
            ("SCP-AST-AC-001", "Air Conditioners", "SCP Factory Air Conditioner 001", 450000, "Katunayake Factory"),
            ("SCP-AST-GENERATOR-001", "Generators", "SCP Backup Generator 001", 3800000, "Katunayake Factory"),
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO assets
                (name, category, asset_name, acquisition_date,
                 acquisition_cost_minor, location, status, docstatus, owner_identity)
            VALUES (?, ?, ?, '2026-01-01', ?, ?, 'Capitalized', 1, 'admin-service')
            """,
            samples,
        )
        connection.executemany(
            "INSERT OR IGNORE INTO document_sequences (series, next_value) VALUES (?, 2)",
            [("SCP-AST",)],
        )


def seed_manufacturing(database: Database) -> None:
    with database.transaction() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO boms (name, item_code, quantity, is_active)
            VALUES ('BOM-FG-CLEANER-5L-001', 'FG-CLEANER-5L', 1, 1)
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO bom_items (bom_name, item_code, qty, uom)
            VALUES ('BOM-FG-CLEANER-5L-001', 'RM-CLEANER-CONC-001', 1, 'Litre')
            """
        )
        connection.execute(
            "INSERT OR IGNORE INTO document_sequences (series, next_value) VALUES ('SCP-PROD', 2)"
        )


def seed_sales(database: Database) -> None:
    with database.transaction() as connection:
        connection.execute(
            "UPDATE customers SET credit_limit_minor = 5000000 WHERE name = 'Southern Hotels'"
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO sales_orders
                (name, customer, transaction_date, status, docstatus,
                 total_minor, owner_identity)
            VALUES ('SCP-SO-2026-00001', 'Southern Hotels', '2026-01-01',
                    'Approved', 1, 850000, 'inventory-service')
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO sales_order_items
                (sales_order_name, item_code, qty, delivered_qty, billed_qty,
                 warehouse, rate_minor)
            VALUES ('SCP-SO-2026-00001', 'FG-TEA-001', 10, 0, 0,
                    'Katunayake Finished Goods', 85000)
            """
        )
        for series in ("SCP-SO", "SCP-DN", "SCP-SINV"):
            connection.execute(
                "INSERT OR IGNORE INTO document_sequences (series, next_value) VALUES (?, 2)",
                (series,),
            )


def seed_purchasing(database: Database) -> None:
    with database.transaction() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO material_requests
                (name, posting_date, status, docstatus, requester_identity)
            VALUES ('SCP-MR-2026-00001', '2026-01-01', 'Approved', 1, 'procurement-service')
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO material_request_items
                (request_name, item_code, qty, warehouse, ordered_qty)
            VALUES ('SCP-MR-2026-00001', 'PKG-BOTTLE-001', 10, 'Peliyagoda Main', 10)
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO purchase_orders
                (name, supplier, transaction_date, status, docstatus,
                 total_minor, requester_identity, material_request_name)
            VALUES ('SCP-PO-2026-00001', 'SCP-Local Packaging', '2026-01-01',
                    'Approved', 1, 35000, 'procurement-service', 'SCP-MR-2026-00001')
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO purchase_order_items
                (purchase_order_name, material_request_item_id, item_code, qty,
                 received_qty, billed_qty, warehouse, rate_minor)
            VALUES ('SCP-PO-2026-00001', 1, 'PKG-BOTTLE-001', 10, 0, 0,
                    'Peliyagoda Main', 3500)
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO purchase_invoices
                (name, supplier, posting_date, status, docstatus,
                 total_minor, outstanding_minor, owner_identity)
            VALUES ('SCP-PINV-2026-00001', 'SCP-Local Packaging', '2026-01-01',
                    'Draft', 0, 1250000, 1250000, 'finance-service')
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO purchase_invoice_items
                (invoice_name, item_code, qty, rate_minor)
            VALUES ('SCP-PINV-2026-00001', 'RM-SUGAR-001', 50, 25000)
            """
        )
        for series in ("SCP-MR", "SCP-PO", "SCP-PR", "SCP-PINV"):
            connection.execute(
                "INSERT OR IGNORE INTO document_sequences (series, next_value) VALUES (?, 2)",
                (series,),
            )


def seed_inventory(database: Database) -> None:
    with database.transaction() as connection:
        connection.executemany(
            """
            INSERT OR IGNORE INTO bins
                (item_code, warehouse, actual_qty, reserved_qty, ordered_qty,
                 valuation_rate_minor, stock_value_minor)
            VALUES (?, ?, ?, 0, 0, ?, ?)
            """,
            [
                ("RM-SUGAR-001", "Katunayake Raw Material", 0, 25000, 0),
                ("RM-SUGAR-001", "Katunayake WIP", 0, 25000, 0),
                ("RM-CLEANER-CONC-001", "Katunayake Raw Material", 500, 42000, 21000000),
                ("FG-CLEANER-5L", "Katunayake Finished Goods", 0, 145000, 0),
                ("FG-TEA-001", "Katunayake Finished Goods", 145, 85000, 12325000),
                ("FG-TEA-001", "Peliyagoda Main", 0, 85000, 0),
                ("FG-TEA-001", "Kandy DC", 0, 85000, 0),
                ("FG-TEA-001", "Galle DC", 0, 85000, 0),
            ],
        )


def seed_masters(database: Database) -> None:
    with database.transaction() as connection:
        connection.executemany(
            """
            INSERT OR IGNORE INTO customers
                (name, customer_name, customer_group, territory, company_name, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            [(name, customer_name, group, territory, _COMPANY[0]) for name, customer_name, group, territory in _CUSTOMERS],
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO suppliers
                (name, supplier_name, supplier_group, country, company_name, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            [(name, supplier_name, group, country, _COMPANY[0]) for name, supplier_name, group, country in _SUPPLIERS],
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO party_contacts
                (party_type, party_name, contact_name, email, phone, address, is_primary)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            [
                ("Supplier", "SCP-Local Packaging", "SCP Packaging Desk", "packaging@scp.example", "+94-11-555-0101", "Peliyagoda, Sri Lanka"),
                ("Supplier", "SCP-Imported Ingredients", "SCP Ingredients Desk", "ingredients@scp.example", "+94-11-555-0102", "Katunayake, Sri Lanka"),
                ("Customer", "SCP-Wholesale Distributors", "SCP Wholesale Desk", "wholesale@scp.example", "+94-11-555-0201", "Colombo, Sri Lanka"),
            ],
        )
        connection.executemany(
            "INSERT OR IGNORE INTO item_groups (name, parent_group) VALUES (?, ?)",
            _ITEM_GROUPS,
        )
        connection.executemany(
            "INSERT OR IGNORE INTO uoms (name, must_be_whole_number, is_active) VALUES (?, ?, 1)",
            _UOMS,
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO warehouses
                (name, parent_warehouse, company_name, warehouse_type, is_group, is_active)
            VALUES (?, ?, ?, ?, 0, 1)
            """,
            [(name, parent, _COMPANY[0], kind) for name, parent, kind in _WAREHOUSES],
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO items
                (name, item_name, description, item_group, stock_uom,
                 standard_rate_minor, valuation_method, valuation_account,
                 is_stock_item, is_purchase_item, is_sales_item, has_batch_no,
                 reorder_level, reorder_qty, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, '5100 - COGS - SCP', 1, 1, 1, ?, ?, ?, 1)
            """,
            [
                (name, item_name, f"Fictional SCP {item_name}", group, uom, rate * 100, method, batch, reorder, qty)
                for name, item_name, group, uom, rate, method, batch, reorder, qty in _ITEMS
            ],
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO item_warehouse_eligibility (item_code, warehouse, direction)
            VALUES (?, ?, ?)
            """,
            [
                (item, warehouse, direction)
                for item, warehouse, direction in (
                    ("RM-SUGAR-001", "Katunayake Raw Material", "source"),
                    ("RM-SUGAR-001", "Katunayake Raw Material", "target"),
                    ("RM-SUGAR-001", "Katunayake WIP", "target"),
                    ("FG-TEA-001", "Katunayake Finished Goods", "source"),
                    ("FG-TEA-001", "Peliyagoda Main", "target"),
                    ("FG-TEA-001", "Kandy DC", "target"),
                    ("FG-TEA-001", "Galle DC", "target"),
                    ("PKG-BOTTLE-001", "Peliyagoda Main", "target"),
                    ("RM-CLEANER-CONC-001", "Katunayake Raw Material", "source"),
                    ("FG-CLEANER-5L", "Katunayake Finished Goods", "source"),
                    ("FG-CLEANER-5L", "Katunayake Finished Goods", "target"),
                )
            ],
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
