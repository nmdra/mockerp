from collections.abc import Callable
import importlib
import sqlite3

platform = importlib.import_module("migrations.001_platform")
organization = importlib.import_module("migrations.002_organization")
finance = importlib.import_module("migrations.003_finance")

Migration = tuple[int, str, Callable[[sqlite3.Connection], None]]

MIGRATIONS: tuple[Migration, ...] = (
    (platform.VERSION, platform.NAME, platform.upgrade),
    (organization.VERSION, organization.NAME, organization.upgrade),
    (finance.VERSION, finance.NAME, finance.upgrade),
)
