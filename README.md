# MockERP

A FastAPI-based mock ERP server that simulates **ERPNext/Frappe REST API**
conventions for local development and integration testing. MockERP is an
independent service for the fictional Serendib Consumer Products (Pvt) Ltd
scenario and is consumed by ERPBridge through its published container image.

- Repository: <https://github.com/nmdra/mockerp>
- Container: `ghcr.io/nmdra/mockerp:<version>`
- API contract: [openapi.yaml](./openapi.yaml)
- ERPBridge consumer: <https://github.com/nmdra/ERPBridge>

The API is a test fixture. It must use fictional data and environment-provided
credentials only; it is not a production ERP or a replacement for ERPNext.

## Features
- **ERPNext API Paths:** Endpoints follow the `/api/resource/{DocType}` pattern.
- **Realistic Envelopes:** All responses are wrapped in a `{"data": ...}` envelope.
- **Authentication:** Supports ERPNext's `token api_key:api_secret` format, Session Cookies (`sid`), and Basic Auth.
- **Standardized Errors:** Returns ERPNext-style exceptions (e.g., `DoesNotExistError`) with appropriate status codes.
- **Simulated Data:** Includes mock data for Finance (Invoices, Payments), HR (Employees, Leave), and Inventory (Items, Bins).

## Getting Started

### Prerequisites
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Recommended) or `pip`

### Running the Server
Using `uv` (Recommended):
```bash
export MOCK_ERP_CREDENTIALS_JSON='{"credentials":[{"api_key":"<api-key>","api_secret":"<api-secret>","role":"admin","identity":"admin-service"}]}'
uv run main.py
```

The server will be available at `http://localhost:8081`. MockERP fails closed
when no credential source is configured. For a Docker deployment, set
`MOCK_ERP_CREDENTIALS_FILE` to a mounted JSON secret instead of using the
inline environment variable.

## Authentication

### Token Authentication
Include the `Authorization` header with the following format:
`Authorization: token <api_key>:<api_secret>`

Credential configuration contains `credentials`, `sessions`, and optional
`basic` lists. Each identity must define an opaque credential, a role, and an
identity name. MockERP does not provide default credentials.

### Session Authentication
Configure session IDs in the credential source, then set a cookie named `sid`.

## SQLite platform

MockERP stores platform data in SQLite. The default path is
`/data/mockerp.db`; set `MOCK_ERP_DB_PATH` for local development. Startup applies
idempotent migrations and seeds the SCP company, LKR fiscal settings, and safe
service identity names. The destructive reset command is development-only:

```bash
MOCK_ERP_ENV=development MOCK_ERP_ALLOW_RESET=true uv run python -m seed --reset
```

## SCP organization and approvals

Startup seeds the fictional SCP organization with Peliyagoda, Katunayake,
Kandy, and Galle locations; department hierarchy; designations; employment
types; service identities; and data-driven roles. Organization resources use
ERPNext envelopes under `/api/resource/{DocType}`.

Approval requests use configured sequential rules. A purchase order at or above
the configured threshold requires finance and administrator approvals in order.
Approval actions write immutable, redacted audit events. Credentials and
protected document values are never written to audit metadata.

## HR foundation

Employee, attendance, leave type, allocation, and leave application resources
are SQLite-backed. Attendance accepts `Present`, `Absent`, `Half Day`, and `Work
From Home`; future and duplicate employee/date records are rejected. Leave
applications calculate inclusive days, enforce allocation balances, and use the
employee → department manager → HR approval sequence.

## Finance foundation

The finance routes use SQLite-backed SCP accounts and minor-unit money values.
Journal entries and payment entries are created as drafts, submitted only after
validation, and cancelled with compensating postings. Payment references update
open-item balances in the same transaction as the ledger posting.

## SCP inventory masters

The master data includes fictional customers, suppliers, safe contacts, item
groups, UOMs, batch-controlled items, and the Katunayake, Peliyagoda, Kandy,
and Galle warehouse tree. Item responses expose source and target warehouse
eligibility; stock quantities remain in the existing Bin fixture until the
stock-ledger tasks are complete.

## Manufacturing-lite

The seeded single-level Floor Cleaner 5L BOM supports a constrained production
flow. A submitted production order consumes raw material and receives finished
goods through the stock ledger. The service does not implement MRP, scheduling,
routing, or job cards.

## Order-to-cash

Sales Order, Delivery Note, and Sales Invoice link through source quantities.
Delivery issues stock, invoices create AR open items, and customer credit limits
are checked before order creation. Southern Hotels is a fictional seeded
customer scenario.

## Procure-to-pay

The purchasing flow links Material Request, Purchase Order approval, Purchase
Receipt, Purchase Invoice, and Payment Entry. Receipt and billing quantities
are checked against their source documents. Submitted receipts update stock and
submitted invoices create AP open items through the accounting boundary.

## Stock ledger

Stock Entry supports material receipt, issue, transfer, manufacturing consumption
and receipt, and stock adjustment. Submission updates Bin projections and writes
append-only stock ledger rows in one transaction. Negative stock, invalid
warehouse eligibility, and invalid lifecycle changes fail without a partial
posting.

## Payroll and expenses

Payroll uses seeded salary components and active assignments to calculate salary
slips. It does not calculate or claim compliance for PAYE, EPF, or ETF. Submitted
salary slips and reimbursed expense claims create balanced finance postings.

## Shared integration fixtures

These deterministic endpoints are used by ERPBridge integration tests. Each
route requires the existing ERPNext-style authentication boundary.

- `GET /api/resource/Plugin Fixture` returns
  `{"data":{"id":"plugin-fixture","state":"source"}}`.
- `POST /api/integration/echo` accepts one JSON object and returns it unchanged
  in the `data` property.
- `GET /api/integration/echo/last` returns the last successful echo payload, or
  `null` before the first echo. This readback is process-local test state and is
  not persisted in the business database.

The echo response never adds authorization, credential, timestamp, or request
metadata. Non-object request bodies return `422`.

## API Documentation

The full OpenAPI specification is available in
[openapi.yaml](./openapi.yaml). ERPBridge pins a MockERP release and retrieves
this file from the matching Git tag instead of copying the source tree.

### Common Endpoints
- `GET /api/resource/Purchase Invoice` - List purchase invoices
- `GET /api/resource/Employee` - List employees
- `GET /api/resource/Item` - List items
- `GET /api/resource/Bin?filters=[["Bin","item_code","=","ITEM-001"]]` - Get stock levels for an item
