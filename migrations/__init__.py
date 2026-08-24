from collections.abc import Callable
import importlib
import sqlite3

platform = importlib.import_module("migrations.001_platform")
organization = importlib.import_module("migrations.002_organization")
finance = importlib.import_module("migrations.003_finance")
hr = importlib.import_module("migrations.004_hr")
payroll = importlib.import_module("migrations.005_payroll")
masters = importlib.import_module("migrations.006_masters")
inventory = importlib.import_module("migrations.007_inventory")
purchasing = importlib.import_module("migrations.008_purchasing")
sales = importlib.import_module("migrations.009_sales")
manufacturing = importlib.import_module("migrations.010_manufacturing")

Migration = tuple[int, str, Callable[[sqlite3.Connection], None]]

MIGRATIONS: tuple[Migration, ...] = (
    (platform.VERSION, platform.NAME, platform.upgrade),
    (organization.VERSION, organization.NAME, organization.upgrade),
    (finance.VERSION, finance.NAME, finance.upgrade),
    (hr.VERSION, hr.NAME, hr.upgrade),
    (payroll.VERSION, payroll.NAME, payroll.upgrade),
    (masters.VERSION, masters.NAME, masters.upgrade),
    (inventory.VERSION, inventory.NAME, inventory.upgrade),
    (purchasing.VERSION, purchasing.NAME, purchasing.upgrade),
    (sales.VERSION, sales.NAME, sales.upgrade),
    (manufacturing.VERSION, manufacturing.NAME, manufacturing.upgrade),
)
