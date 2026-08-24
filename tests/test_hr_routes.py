from datetime import date

from fastapi.testclient import TestClient


def test_hr_routes_use_scp_seed_data(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    employees = client.get("/api/resource/Employee", headers=admin_headers)
    leaves = client.get("/api/resource/Leave Application", headers=admin_headers)

    assert employees.status_code == 200
    assert employees.json()["data"][0]["name"] == "EMP-SCP-00001"
    assert "personal_email" not in employees.json()["data"][0]
    assert leaves.status_code == 200
    assert leaves.json()["data"][0]["status"] == "Approved"


def test_hr_routes_create_attendance_and_leave_request(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    attendance = client.post(
        "/api/resource/Attendance",
        headers=admin_headers,
        json={
            "employee": "EMP-SCP-00001",
            "attendance_date": date.today().isoformat(),
            "status": "Present",
        },
    )
    leave = client.post(
        "/api/resource/Leave Application",
        headers=admin_headers,
        json={
            "employee": "EMP-SCP-00001",
            "leave_type": "Sick Leave",
            "from_date": "2026-07-10",
            "to_date": "2026-07-10",
            "description": "Fictional sick leave",
        },
    )

    assert attendance.status_code == 201
    assert leave.status_code == 201
    assert leave.json()["data"]["status"] == "Pending Approval"
