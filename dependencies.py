from fastapi import Request, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
import base64

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
security = HTTPBasic()

MOCK_CREDENTIALS = {
    # API Keys
    "finance-key-001": "finance_viewer",
    "finance-key-002": "finance_editor",
    "hr-key-001": "hr_viewer",
    "hr-key-002": "hr_manager",
    "inv-key-001": "inv_viewer",
    "inv-key-002": "inv_editor",
    "admin-key-001": "admin",
}

BASIC_AUTH_ROLES = {
    "user:pass": "finance_viewer",
    "admin:admin": "admin",
}

async def get_role(
    request: Request,
    api_key: str = Security(api_key_header),
):
    # 1. API Key
    if api_key in MOCK_CREDENTIALS:
        return MOCK_CREDENTIALS[api_key]

    # 2. Basic Auth
    auth = request.headers.get("Authorization")
    if auth and auth.startswith("Basic "):
        try:
            encoded = auth.split(" ")[1]
            decoded = base64.b64decode(encoded).decode("utf-8")
            if decoded in BASIC_AUTH_ROLES:
                return BASIC_AUTH_ROLES[decoded]
        except Exception:
            pass

    # 3. Bearer (Stub)
    if auth and auth.startswith("Bearer "):
        token = auth.split(" ")[1]
        if token == "dev-stub-token":
            return "admin"

    raise HTTPException(status_code=401, detail="unauthorized")

def check_role(required_roles: list, current_role: str):
    if current_role == "admin":
        return
    if current_role not in required_roles:
        raise HTTPException(status_code=403, detail="forbidden")
