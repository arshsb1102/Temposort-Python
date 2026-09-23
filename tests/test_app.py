from fastapi.testclient import TestClient

from app.db import store
from app.main import app

client = TestClient(app)


def setup_function() -> None:
    store.clear()


def test_health_check():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_registration_and_login_produce_jwt():
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "name": "Alice",
            "email": "alice@example.com",
            "password": "secret123",
        },
    )
    assert register_response.status_code == 201

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
