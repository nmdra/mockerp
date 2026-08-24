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
