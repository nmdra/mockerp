from fastapi import Request, HTTPException
import base64

# ERPNext-style credentials map
# Format: "api_key:api_secret" -> resolved role
MOCK_CREDENTIALS = {
    "fin_key_001:fin_sec_abc123": "finance_viewer",
    "fin_key_002:fin_sec_def456": "finance_editor",
    "hr_key_001:hr_sec_ghi789": "hr_viewer",
    "hr_key_002:hr_sec_jkl012": "hr_manager",
    "inv_key_001:inv_sec_mno345": "inv_viewer",
    "inv_key_002:inv_sec_pqr678": "inv_editor",
    "adm_key_001:adm_sec_stu901": "admin",
}

# Session ID map (for sid cookie)
MOCK_SESSIONS = {
    "sess-999-finance": "finance_viewer",
    "sess-888-admin": "admin",
}

async def get_role(request: Request):
    auth = request.headers.get("Authorization")
    
    # 1. ERPNext Token Auth: "token api_key:api_secret"
    if auth and auth.startswith("token "):
        token = auth.split(" ")[1]
        if token in MOCK_CREDENTIALS:
            return MOCK_CREDENTIALS[token]
        raise_erpnext_error("AuthenticationError", "Invalid Credentials", 401)

    # 2. Session Cookie (sid)
    sid = request.cookies.get("sid")
    if sid in MOCK_SESSIONS:
        return MOCK_SESSIONS[sid]

    # 3. Fallback Basic Auth (for browser simulation)
    if auth and auth.startswith("Basic "):
        try:
            encoded = auth.split(" ")[1]
            decoded = base64.b64decode(encoded).decode("utf-8")
            if decoded == "admin:admin":
                return "admin"
        except Exception:
            pass

    raise_erpnext_error("AuthenticationError", "Not logged in", 401)

def check_role(required_roles: list, current_role: str):
    if current_role == "admin":
        return
    if current_role not in required_roles:
        raise_erpnext_error("PermissionError", "Not permitted", 403)

def raise_erpnext_error(exc_type: str, message: str, status_code: int):
    raise HTTPException(
        status_code=status_code,
        detail={
            "exc_type": exc_type,
            "exception": f"frappe.exceptions.{exc_type}: {message}",
            "_server_messages": "[]"
        }
    )
