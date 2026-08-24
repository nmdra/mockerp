from collections.abc import Callable
import importlib
import sqlite3

platform = importlib.import_module("migrations.001_platform")

Migration = tuple[int, str, Callable[[sqlite3.Connection], None]]

MIGRATIONS: tuple[Migration, ...] = (
    (platform.VERSION, platform.NAME, platform.upgrade),
)
