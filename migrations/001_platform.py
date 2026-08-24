import sqlite3

VERSION = 1
NAME = "platform"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS document_sequences (
            series TEXT PRIMARY KEY,
            next_value INTEGER NOT NULL CHECK (next_value > 0)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS companies (
            name TEXT PRIMARY KEY,
            currency TEXT NOT NULL,
            country TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS system_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS service_identities (
            name TEXT PRIMARY KEY,
            role TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1))
        )
        """
    )
