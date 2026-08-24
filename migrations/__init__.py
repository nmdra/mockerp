from collections.abc import Callable
import importlib
import sqlite3

platform = importlib.import_module("migrations.001_platform")
organization = importlib.import_module("migrations.002_organization")
finance = importlib.import_module("migrations.003_finance")
hr = importlib.import_module("migrations.004_hr")
payroll = importlib.import_module("migrations.005_payroll")

Migration = tuple[int, str, Callable[[sqlite3.Connection], None]]

MIGRATIONS: tuple[Migration, ...] = (
    (platform.VERSION, platform.NAME, platform.upgrade),
    (organization.VERSION, organization.NAME, organization.upgrade),
    (finance.VERSION, finance.NAME, finance.upgrade),
    (hr.VERSION, hr.NAME, hr.upgrade),
    (payroll.VERSION, payroll.NAME, payroll.upgrade),
)
