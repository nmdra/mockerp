from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import sqlite3

from database import Database
from services.accounting import AccountingError, create_journal_entry, minor_to_money, money_to_minor, submit_journal_entry
from services.audit import record_audit
from services.authorization import Actor


class AssetError(ValueError):
    """Raised when an asset lifecycle event is invalid."""


@dataclass(frozen=True)
class Asset:
    name: str
    asset_name: str
    category: str
    location: str
    status: str
    acquisition_cost: float


def _from_row(row: sqlite3.Row) -> Asset:
    return Asset(row["name"], row["asset_name"], row["category"], row["location"], row["status"], float(minor_to_money(row["acquisition_cost_minor"])))


def _row(database: Database, name: str) -> sqlite3.Row:
    with database.connection() as connection:
        row = connection.execute("SELECT * FROM assets WHERE name = ?", (name,)).fetchone()
    if row is None:
        raise AssetError("asset was not found")
    return row


def create_asset(
    database: Database,
    actor: Actor,
    *,
    category: str,
    asset_name: str,
    acquisition_date: str,
    acquisition_cost: str,
    location: str,
) -> Asset:
    try:
        cost = money_to_minor(acquisition_cost)
    except AccountingError as exc:
        raise AssetError(str(exc)) from exc
    if cost <= 0:
        raise AssetError("asset cost must be positive")
    name = database.next_document_name("SCP-AST")
    with database.transaction() as connection:
        if connection.execute("SELECT 1 FROM asset_categories WHERE name = ?", (category,)).fetchone() is None:
            raise AssetError("asset category was not found")
        connection.execute(
            """
            INSERT INTO assets
                (name, category, asset_name, acquisition_date,
                 acquisition_cost_minor, location, status, docstatus, owner_identity)
            VALUES (?, ?, ?, ?, ?, ?, 'Draft', 0, ?)
            """,
            (name, category, asset_name, acquisition_date, cost, location, actor.identity),
        )
        record_audit(database, actor, "create", "Asset", name, after={"status": "Draft", "location": location}, connection=connection)
        return _from_row(connection.execute("SELECT * FROM assets WHERE name = ?", (name,)).fetchone())


def capitalize_asset(database: Database, actor: Actor, name: str) -> Asset:
    row = _row(database, name)
    if row["status"] != "Draft":
        raise AssetError("asset is not draft")
    try:
        journal = create_journal_entry(
            database, actor, posting_date=row["acquisition_date"], remark=f"Capitalize {name}",
            accounts=[
                {"account": "1000 - Assets - SCP", "debit": float(minor_to_money(row["acquisition_cost_minor"])), "credit": 0},
                {"account": "2100 - Creditors - SCP", "debit": 0, "credit": float(minor_to_money(row["acquisition_cost_minor"]))},
            ],
        )
        submit_journal_entry(database, actor, journal.name)
    except AccountingError as exc:
        raise AssetError(str(exc)) from exc
    with database.transaction() as connection:
        connection.execute("UPDATE assets SET status = 'Capitalized', docstatus = 1 WHERE name = ?", (name,))
        connection.execute("INSERT INTO asset_events (asset_name, event_type, event_date, amount_minor, actor_identity, journal_entry) VALUES (?, 'Capitalized', ?, ?, ?, ?)", (name, row["acquisition_date"], row["acquisition_cost_minor"], actor.identity, journal.name))
        record_audit(database, actor, "capitalize", "Asset", name, before={"status": "Draft"}, after={"status": "Capitalized"}, connection=connection)
        return _from_row(connection.execute("SELECT * FROM assets WHERE name = ?", (name,)).fetchone())


def transfer_asset(database: Database, actor: Actor, name: str, *, location: str, effective_date: str) -> Asset:
    row = _row(database, name)
    if row["status"] != "Capitalized":
        raise AssetError("only capitalized assets can be transferred")
    with database.transaction() as connection:
        connection.execute("UPDATE assets SET location = ? WHERE name = ?", (location, name))
        connection.execute("INSERT INTO asset_events (asset_name, event_type, event_date, from_location, to_location, actor_identity) VALUES (?, 'Transferred', ?, ?, ?, ?)", (name, effective_date, row["location"], location, actor.identity))
        record_audit(database, actor, "transfer", "Asset", name, before={"location": row["location"]}, after={"location": location}, connection=connection)
        return _from_row(connection.execute("SELECT * FROM assets WHERE name = ?", (name,)).fetchone())


def dispose_asset(database: Database, actor: Actor, name: str, *, disposal_date: str, proceeds: str) -> Asset:
    row = _row(database, name)
    if row["status"] == "Disposed":
        raise AssetError("asset is already disposed")
    if row["status"] != "Capitalized":
        raise AssetError("only capitalized assets can be disposed")
    try:
        proceeds_minor = money_to_minor(proceeds)
    except AccountingError as exc:
        raise AssetError(str(exc)) from exc
    with database.transaction() as connection:
        connection.execute("UPDATE assets SET status = 'Disposed', docstatus = 2, disposal_date = ?, disposal_proceeds_minor = ? WHERE name = ?", (disposal_date, proceeds_minor, name))
        connection.execute("INSERT INTO asset_events (asset_name, event_type, event_date, amount_minor, actor_identity) VALUES (?, 'Disposed', ?, ?, ?)", (name, disposal_date, proceeds_minor, actor.identity))
        record_audit(database, actor, "dispose", "Asset", name, before={"status": row["status"]}, after={"status": "Disposed", "proceeds_minor": proceeds_minor}, connection=connection)
        return _from_row(connection.execute("SELECT * FROM assets WHERE name = ?", (name,)).fetchone())
