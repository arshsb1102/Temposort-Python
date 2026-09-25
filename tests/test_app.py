from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.db import store
from app.main import app
from app.services.email_service import email_service

try:
    from app.api.v1 import auth as v1_auth
    from app.api.v1 import tasks as v1_tasks
    from app.api.v1 import reminders as v1_reminders
except ImportError as exc:  # pragma: no cover - intentional regression guard
    v1_auth = None
    v1_tasks = None
    v1_reminders = None
    import_error = exc
else:
    import_error = None

client = TestClient(app)


def test_versioned_v1_modules_are_available():
    assert import_error is None
    assert v1_auth is not None
    assert v1_tasks is not None
    assert v1_reminders is not None


def setup_function() -> None:
    store.clear()
    email_service.clear_history()


def test_health_check():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_registration_sends_verification_email_and_login_requires_verification():
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Alice",
            "email": "alice@example.com",
            "password": "secret123",
        },
    )
    assert register_response.status_code == 201
    assert "verification_required" in register_response.json()

    verification_email = email_service.sent_messages[-1]
    assert verification_email["to"] == "alice@example.com"

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "alice@example.com",
            "password": "secret123",
        },
    )
    assert login_response.status_code == 403
    assert "verify your email" in login_response.json()["detail"].lower()

    verify_response = client.get(
        "/api/v1/auth/verify-email",
        params={"token": verification_email["token"]},
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["verified"] is True

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "alice@example.com",
            "password": "secret123",
        },
    )
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()
    assert login_response.json()["token_type"] == "bearer"


def test_tasks_require_authentication():
    client.post(
        "/api/v1/auth/register",
        json={
            "name": "Alice",
            "email": "alice@example.com",
            "password": "secret123",
        },
    )

    verify_response = client.get(
        "/api/v1/auth/verify-email",
        params={"token": email_service.sent_messages[-1]["token"]},
    )
    assert verify_response.status_code == 200

    unauthenticated = client.get("/api/v1/tasks")
    assert unauthenticated.status_code == 401

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "alice@example.com",
            "password": "secret123",
        },
    )
    token = login_response.json()["access_token"]

    payload = {
        "title": "Learn FastAPI",
        "description": "Build the first production-aligned TempoSort backend",
        "due_at": "2026-10-01T10:00:00Z",
        "priority": "high",
    }

    create_response = client.post(
        "/api/v1/tasks",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_response.status_code == 201

    task = create_response.json()
    assert task["title"] == payload["title"]
    assert task["priority"] == "high"

    list_response = client.get(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 1


def test_due_reminders_can_be_processed():
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Alice",
            "email": "alice@example.com",
            "password": "secret123",
        },
    )
    assert register_response.status_code == 201

    verify_response = client.get(
        "/api/v1/auth/verify-email",
        params={"token": email_service.sent_messages[-1]["token"]},
    )
    assert verify_response.status_code == 200

    reminder_response = client.post(
        "/api/v1/reminders",
        json={
            "user_email": "alice@example.com",
            "title": "Task reminder",
            "message": "Your task is due soon.",
            "channel": "email",
            "scheduled_for": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
        },
    )
    assert reminder_response.status_code == 201

    process_response = client.post("/api/v1/reminders/process")
    assert process_response.status_code == 200
    assert process_response.json()["processed"] >= 1


def test_task_can_be_deleted():
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Alice",
            "email": "alice@example.com",
            "password": "secret123",
        },
    )
    assert register_response.status_code == 201

    verify_response = client.get(
        "/api/v1/auth/verify-email",
        params={"token": email_service.sent_messages[-1]["token"]},
    )
    assert verify_response.status_code == 200

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "alice@example.com",
            "password": "secret123",
        },
    )
    token = login_response.json()["access_token"]

    task_response = client.post(
        "/api/v1/tasks",
        json={
            "title": "Delete me",
            "description": "This task should be removed",
            "priority": "medium",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    task_id = task_response.json()["id"]

    delete_response = client.delete(
        f"/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True


def test_user_can_delete_their_account():
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Alice",
            "email": "alice@example.com",
            "password": "secret123",
        },
    )
    assert register_response.status_code == 201

    verify_response = client.get(
        "/api/v1/auth/verify-email",
        params={"token": email_service.sent_messages[-1]["token"]},
    )
    assert verify_response.status_code == 200

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "alice@example.com",
            "password": "secret123",
        },
    )
    token = login_response.json()["access_token"]

    delete_response = client.post(
        "/api/v1/auth/delete-user",
        json={"email": "alice@example.com", "password": "secret123"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True

    follow_up_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "alice@example.com",
            "password": "secret123",
        },
    )
    assert follow_up_login.status_code == 401
