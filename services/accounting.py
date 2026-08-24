from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import sqlite3
from typing import Any

from database import Database
from services.audit import record_audit
from services.authorization import Actor


class AccountingError(ValueError):
    """Raised when an accounting document cannot be posted safely."""


def money_to_minor(value: Decimal | int | float | str) -> int:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise AccountingError("amount must be numeric") from exc
    rounded = parsed.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if parsed != rounded:
        raise AccountingError("amount supports at most two decimal places")
    return int(rounded * 100)


def minor_to_money(value: int) -> Decimal:
    return (Decimal(value) / Decimal(100)).quantize(Decimal("0.01"))


@dataclass(frozen=True)
class JournalEntry:
    name: str
    posting_date: str
    status: str
    docstatus: int
    total_debit: Decimal
    total_credit: Decimal
    remark: str
    accounts: tuple[dict[str, object], ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "doctype": "Journal Entry",
            "docstatus": self.docstatus,
            "posting_date": self.posting_date,
            "status": self.status,
            "total_debit": float(self.total_debit),
            "total_credit": float(self.total_credit),
            "remark": self.remark,
            "accounts": list(self.accounts),
        }


@dataclass(frozen=True)
class PaymentEntry:
    name: str
    posting_date: str
    status: str
    docstatus: int
    payment_type: str
    party_type: str | None
    party: str | None
    paid_amount: Decimal
    received_amount: Decimal
    paid_from: str
    paid_to: str
    references: tuple[dict[str, object], ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "doctype": "Payment Entry",
            "docstatus": self.docstatus,
            "posting_date": self.posting_date,
            "status": self.status,
            "payment_type": self.payment_type,
            "party_type": self.party_type,
            "party": self.party,
            "paid_amount": float(self.paid_amount),
            "received_amount": float(self.received_amount),
            "paid_from": self.paid_from,
            "paid_to": self.paid_to,
            "references": list(self.references),
        }


def _account_exists(connection: sqlite3.Connection, account: str) -> None:
    if connection.execute("SELECT 1 FROM accounts WHERE name = ?", (account,)).fetchone() is None:
        raise AccountingError(f"account {account} does not exist")


def _journal_from_row(
    connection: sqlite3.Connection, row: sqlite3.Row
) -> JournalEntry:
    lines = connection.execute(
        """
        SELECT account, debit_minor, credit_minor
        FROM journal_entry_accounts WHERE journal_entry_name = ? ORDER BY id
        """,
        (row["name"],),
    ).fetchall()
    return JournalEntry(
        name=row["name"],
        posting_date=row["posting_date"],
        status=row["status"],
        docstatus=row["docstatus"],
        total_debit=minor_to_money(row["total_debit_minor"]),
        total_credit=minor_to_money(row["total_credit_minor"]),
        remark=row["remark"],
        accounts=tuple(
            {
                "account": line["account"],
                "debit": float(minor_to_money(line["debit_minor"])),
                "credit": float(minor_to_money(line["credit_minor"])),
            }
            for line in lines
        ),
    )


def _payment_from_row(
    connection: sqlite3.Connection, row: sqlite3.Row
) -> PaymentEntry:
    references = connection.execute(
        """
        SELECT reference_doctype, reference_name, allocated_minor
        FROM payment_references WHERE payment_entry_name = ? ORDER BY id
        """,
        (row["name"],),
    ).fetchall()
    return PaymentEntry(
        name=row["name"],
        posting_date=row["posting_date"],
        status=row["status"],
        docstatus=row["docstatus"],
        payment_type=row["payment_type"],
        party_type=row["party_type"],
        party=row["party"],
        paid_amount=minor_to_money(row["paid_amount_minor"]),
        received_amount=minor_to_money(row["received_amount_minor"]),
        paid_from=row["paid_from"],
        paid_to=row["paid_to"],
        references=tuple(
            {
                "reference_doctype": reference["reference_doctype"],
                "reference_name": reference["reference_name"],
                "allocated_amount": float(minor_to_money(reference["allocated_minor"])),
            }
            for reference in references
        ),
    )


def create_journal_entry(
    database: Database,
    actor: Actor,
    *,
    posting_date: str,
    accounts: list[dict[str, Any]],
    remark: str = "",
) -> JournalEntry:
    if not accounts:
        raise AccountingError("journal entry requires accounts")
    name = database.next_document_name("SCP-JV")
    normalized: list[tuple[str, int, int]] = []
    for line in accounts:
        account = str(line.get("account", ""))
        debit = money_to_minor(line.get("debit", 0))
        credit = money_to_minor(line.get("credit", 0))
        if debit < 0 or credit < 0 or (debit and credit) or not (debit or credit):
            raise AccountingError("each journal line must contain one positive side")
        normalized.append((account, debit, credit))
    total_debit = sum(line[1] for line in normalized)
    total_credit = sum(line[2] for line in normalized)
    with database.transaction() as connection:
        for account, _, _ in normalized:
            _account_exists(connection, account)
        connection.execute(
            """
            INSERT INTO journal_entries
                (name, posting_date, remark, docstatus, status,
                 total_debit_minor, total_credit_minor, owner_identity)
            VALUES (?, ?, ?, 0, 'Draft', ?, ?, ?)
            """,
            (name, posting_date, remark, total_debit, total_credit, actor.identity),
        )
        connection.executemany(
            """
            INSERT INTO journal_entry_accounts
                (journal_entry_name, account, debit_minor, credit_minor)
            VALUES (?, ?, ?, ?)
            """,
            [(name, account, debit, credit) for account, debit, credit in normalized],
        )
        row = connection.execute(
            "SELECT * FROM journal_entries WHERE name = ?", (name,)
        ).fetchone()
        return _journal_from_row(connection, row)


def submit_journal_entry(
    database: Database, actor: Actor, name: str
) -> JournalEntry:
    with database.transaction() as connection:
        row = connection.execute(
            "SELECT * FROM journal_entries WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            raise AccountingError("journal entry was not found")
        if row["status"] != "Draft":
            raise AccountingError("only draft journal entries can be submitted")
        if row["total_debit_minor"] <= 0 or row["total_debit_minor"] != row["total_credit_minor"]:
            raise AccountingError("journal entry must be balanced before submission")
        lines = connection.execute(
            """
            SELECT account, debit_minor, credit_minor
            FROM journal_entry_accounts WHERE journal_entry_name = ?
            """,
            (name,),
        ).fetchall()
        connection.executemany(
            """
            INSERT INTO gl_entries
                (voucher_type, voucher_no, account, posting_date,
                 debit_minor, credit_minor, is_reversal)
            VALUES ('Journal Entry', ?, ?, ?, ?, ?, 0)
            """,
            [
                (name, line["account"], row["posting_date"], line["debit_minor"], line["credit_minor"])
                for line in lines
            ],
        )
        connection.execute(
            "UPDATE journal_entries SET docstatus = 1, status = 'Submitted' WHERE name = ?",
            (name,),
        )
        record_audit(
            database,
            actor,
            "submit",
            "Journal Entry",
            name,
            before={"status": "Draft"},
            after={"status": "Submitted"},
            connection=connection,
        )
        return _journal_from_row(connection, connection.execute("SELECT * FROM journal_entries WHERE name = ?", (name,)).fetchone())


def cancel_journal_entry(
    database: Database, actor: Actor, name: str
) -> JournalEntry:
    with database.transaction() as connection:
        row = connection.execute(
            "SELECT * FROM journal_entries WHERE name = ?", (name,)
        ).fetchone()
        if row is None or row["status"] != "Submitted":
            raise AccountingError("only submitted journal entries can be cancelled")
        lines = connection.execute(
            "SELECT * FROM gl_entries WHERE voucher_no = ? AND is_reversal = 0", (name,)
        ).fetchall()
        connection.executemany(
            """
            INSERT INTO gl_entries
                (voucher_type, voucher_no, account, posting_date,
                 debit_minor, credit_minor, is_reversal)
            VALUES ('Journal Entry', ?, ?, ?, ?, ?, 1)
            """,
            [
                (name, line["account"], line["posting_date"], line["credit_minor"], line["debit_minor"])
                for line in lines
            ],
        )
        connection.execute(
            "UPDATE journal_entries SET docstatus = 2, status = 'Cancelled' WHERE name = ?",
            (name,),
        )
        record_audit(
            database,
            actor,
            "cancel",
            "Journal Entry",
            name,
            before={"status": "Submitted"},
            after={"status": "Cancelled"},
            connection=connection,
        )
        return _journal_from_row(connection, connection.execute("SELECT * FROM journal_entries WHERE name = ?", (name,)).fetchone())


def create_payment_entry(
    database: Database,
    actor: Actor,
    *,
    posting_date: str,
    party_type: str | None,
    party: str | None,
    paid_from: str,
    paid_to: str,
    paid_amount: Decimal | int | float | str,
    references: list[dict[str, Any]] | None = None,
    payment_type: str = "Pay",
) -> PaymentEntry:
    if payment_type not in {"Pay", "Receive", "Internal Transfer"}:
        raise AccountingError("unsupported payment type")
    paid_minor = money_to_minor(paid_amount)
    if paid_minor <= 0:
        raise AccountingError("payment amount must be positive")
    received_minor = paid_minor
    name = database.next_document_name("SCP-PAY")
    normalized_refs = [
        (
            str(reference.get("reference_doctype", "")),
            str(reference.get("reference_name", "")),
            money_to_minor(reference.get("allocated_amount", 0)),
        )
        for reference in (references or [])
    ]
    with database.transaction() as connection:
        _account_exists(connection, paid_from)
        _account_exists(connection, paid_to)
        if any(not doctype or not ref_name or amount <= 0 for doctype, ref_name, amount in normalized_refs):
            raise AccountingError("payment references must contain positive amounts")
        connection.execute(
            """
            INSERT INTO payment_entries
                (name, payment_type, posting_date, party_type, party,
                 paid_from, paid_to, paid_amount_minor, received_amount_minor,
                 docstatus, status, owner_identity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'Draft', ?)
            """,
            (
                name,
                payment_type,
                posting_date,
                party_type,
                party,
                paid_from,
                paid_to,
                paid_minor,
                received_minor,
                actor.identity,
            ),
        )
        connection.executemany(
            """
            INSERT INTO payment_references
                (payment_entry_name, reference_doctype, reference_name, allocated_minor)
            VALUES (?, ?, ?, ?)
            """,
            [(name, doctype, reference, amount) for doctype, reference, amount in normalized_refs],
        )
        return _payment_from_row(connection, connection.execute("SELECT * FROM payment_entries WHERE name = ?", (name,)).fetchone())


def submit_payment_entry(
    database: Database, actor: Actor, name: str
) -> PaymentEntry:
    with database.transaction() as connection:
        row = connection.execute(
            "SELECT * FROM payment_entries WHERE name = ?", (name,)
        ).fetchone()
        if row is None or row["status"] != "Draft":
            raise AccountingError("only draft payment entries can be submitted")
        references = connection.execute(
            "SELECT * FROM payment_references WHERE payment_entry_name = ?", (name,)
        ).fetchall()
        if sum(reference["allocated_minor"] for reference in references) > row["paid_amount_minor"]:
            raise AccountingError("payment allocations exceed the payment amount")
        for reference in references:
            item = connection.execute(
                "SELECT * FROM open_items WHERE reference_name = ?",
                (reference["reference_name"],),
            ).fetchone()
            if item is None:
                raise AccountingError("payment reference is not an open item")
            if reference["allocated_minor"] > item["outstanding_minor"]:
                raise AccountingError("payment allocation exceeds outstanding amount")
        for reference in references:
            connection.execute(
                """
                UPDATE open_items
                SET outstanding_minor = outstanding_minor - ?
                WHERE reference_name = ?
                """,
                (reference["allocated_minor"], reference["reference_name"]),
            )
        if row["payment_type"] == "Receive":
            debit_account, credit_account = row["paid_to"], row["paid_from"]
        else:
            debit_account, credit_account = row["paid_from"], row["paid_to"]
        connection.executemany(
            """
            INSERT INTO gl_entries
                (voucher_type, voucher_no, account, posting_date,
                 debit_minor, credit_minor, is_reversal)
            VALUES ('Payment Entry', ?, ?, ?, ?, ?, 0)
            """,
            [
                (name, debit_account, row["posting_date"], row["paid_amount_minor"], 0),
                (name, credit_account, row["posting_date"], 0, row["paid_amount_minor"]),
            ],
        )
        connection.execute(
            "UPDATE payment_entries SET docstatus = 1, status = 'Submitted' WHERE name = ?",
            (name,),
        )
        record_audit(
            database,
            actor,
            "submit",
            "Payment Entry",
            name,
            before={"status": "Draft"},
            after={"status": "Submitted"},
            connection=connection,
        )
        return _payment_from_row(connection, connection.execute("SELECT * FROM payment_entries WHERE name = ?", (name,)).fetchone())


def cancel_payment_entry(
    database: Database, actor: Actor, name: str
) -> PaymentEntry:
    with database.transaction() as connection:
        row = connection.execute(
            "SELECT * FROM payment_entries WHERE name = ?", (name,)
        ).fetchone()
        if row is None or row["status"] != "Submitted":
            raise AccountingError("only submitted payment entries can be cancelled")
        references = connection.execute(
            "SELECT * FROM payment_references WHERE payment_entry_name = ?", (name,)
        ).fetchall()
        for reference in references:
            connection.execute(
                """
                UPDATE open_items SET outstanding_minor = outstanding_minor + ?
                WHERE reference_name = ? AND outstanding_minor + ? <= total_minor
                """,
                (reference["allocated_minor"], reference["reference_name"], reference["allocated_minor"]),
            )
        original = connection.execute(
            "SELECT * FROM gl_entries WHERE voucher_no = ? AND is_reversal = 0", (name,)
        ).fetchall()
        connection.executemany(
            """
            INSERT INTO gl_entries
                (voucher_type, voucher_no, account, posting_date,
                 debit_minor, credit_minor, is_reversal)
            VALUES ('Payment Entry', ?, ?, ?, ?, ?, 1)
            """,
            [
                (name, line["account"], line["posting_date"], line["credit_minor"], line["debit_minor"])
                for line in original
            ],
        )
        connection.execute(
            "UPDATE payment_entries SET docstatus = 2, status = 'Cancelled' WHERE name = ?",
            (name,),
        )
        record_audit(
            database,
            actor,
            "cancel",
            "Payment Entry",
            name,
            before={"status": "Submitted"},
            after={"status": "Cancelled"},
            connection=connection,
        )
        return _payment_from_row(connection, connection.execute("SELECT * FROM payment_entries WHERE name = ?", (name,)).fetchone())
