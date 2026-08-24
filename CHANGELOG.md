# Changelog

All notable changes to MockERP are documented here.

## [Unreleased]

### Added

- Standalone CI and GHCR image publication workflows.
- Health smoke coverage for the service boundary.
- Authenticated deterministic integration fixture and echo endpoints.
- SQLite platform migrations, deterministic SCP bootstrap, and development-only reset.
- Environment or Docker-secret credential loading with fail-closed startup.
- SCP organization masters, sequential approvals, authorization, and audit history.
- SQLite-backed chart of accounts, journal entries, payments, and open-item allocation.
- SCP employees, attendance, leave balances, and sequential leave approvals.
- Assignment-based payroll, salary slips, employee advances, and expense claims.
- Fictional SCP customer, supplier, item, UOM, and warehouse masters.
- Append-only stock ledger, Stock Entry lifecycle, and SQLite Bin projections.
- Linked procure-to-pay documents with receipt, invoice, AP, and approval flow.
- Southern Hotels order-to-cash flow with delivery stock issues and AR invoices.
- Single-level Floor Cleaner BOM and production stock flow.
- Fictional fixed-asset categories, lifecycle events, and disposal controls.

## [0.1.1] - 2026-08-24

### Added

- Authenticated deterministic integration fixture and echo endpoints.

## [0.1.0] - 2026-08-24

### Added

- ERPNext-style Finance, HR, and Inventory resource fixtures.
- FastAPI service with token, session, and basic authentication.
