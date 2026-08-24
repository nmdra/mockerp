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
uv run main.py
```

The server will be available at `http://localhost:8081`.

## Authentication

### Token Authentication
Include the `Authorization` header with the following format:
`Authorization: token <api_key>:<api_secret>`

**Mock Credentials:**
| Role | API Key | API Secret | Header Example |
| :--- | :--- | :--- | :--- |
| Admin | `adm_key_001` | `adm_sec_stu901` | `token adm_key_001:adm_sec_stu901` |
| Finance Editor | `fin_key_002` | `fin_sec_def456` | `token fin_key_002:fin_sec_def456` |
| HR Manager | `hr_key_002` | `hr_sec_jkl012` | `token hr_key_002:hr_sec_jkl012` |
| Inv Editor | `inv_key_002` | `inv_sec_pqr678` | `token inv_key_002:inv_sec_pqr678` |

### Session Authentication
Set a cookie named `sid`.
- `sid=sess-888-admin` (Admin role)
- `sid=sess-999-finance` (Finance Viewer role)

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
