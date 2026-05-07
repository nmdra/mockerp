# Mock ERP Service

A FastAPI-based mock ERP server that simulates the **ERPNext (Frappe Framework)** REST API conventions. This service is designed for local development and testing of the ERPBridge middleware.

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
cd mock-erp
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

## API Documentation
The full OpenAPI specification is available in [openapi.yaml](./openapi.yaml).

### Common Endpoints
- `GET /api/resource/Purchase Invoice` - List purchase invoices
- `GET /api/resource/Employee` - List employees
- `GET /api/resource/Item` - List items
- `GET /api/resource/Bin?filters=[["Bin","item_code","=","ITEM-001"]]` - Get stock levels for an item
