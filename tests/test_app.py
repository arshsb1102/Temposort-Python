import asyncio
import smtplib
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx
import pytest
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


def test_redis_settings_are_configurable():
    from app.core.environment import settings

    assert hasattr(settings, "redis_url")
    assert settings.redis_url.startswith("redis://")


def test_daily_digest_settings_are_configurable():
    from app.core.environment import settings

    assert hasattr(settings, "reminder_digest_enabled")
    assert hasattr(settings, "reminder_digest_hour")
    assert hasattr(settings, "reminder_digest_minute")
    assert settings.reminder_digest_enabled is True
    assert 0 <= settings.reminder_digest_hour <= 23
    assert 0 <= settings.reminder_digest_minute <= 59


def test_production_settings_reject_weak_jwt_secret():
    from pydantic import ValidationError

    from app.core.environment import Settings

    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(app_env="production", jwt_secret="short", _env_file=None)


def test_reminder_schema_rejects_unimplemented_channels():
    from pydantic import ValidationError

    from app.schemas.reminders import ReminderCreate

    with pytest.raises(ValidationError):
        ReminderCreate(
            user_email="alice@example.com",
            title="Reminder",
            message="Test",
            channel="sms",
            scheduled_for=datetime.now(timezone.utc),
        )


def test_reminder_processing_is_idempotent_when_lock_is_not_available(monkeypatch):
    from app.services.reminder_service import reminder_service
    from app.services.redis_service import redis_service

    due_reminder = {
        "id": "reminder-1",
        "user_email": "alice@example.com",
        "title": "Reminder",
        "message": "Test",
    }
    monkeypatch.setattr(redis_service, "acquire_lock", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        reminder_service.repo.reminders,
        "list_due_reminders",
        AsyncMock(return_value=[due_reminder]),
    )
    get_user = AsyncMock()
    mark_sent = AsyncMock()
    monkeypatch.setattr(reminder_service.user_repo, "get_user_by_email", get_user)
    monkeypatch.setattr(reminder_service.repo.reminders, "mark_reminder_sent", mark_sent)

    result = asyncio.run(reminder_service.process_due_reminders())

    assert result == 0
    get_user.assert_not_awaited()
    mark_sent.assert_not_awaited()


def test_celery_retry_settings_are_enabled():
    from app.services.celery_app import celery_app
    from app.services.tasks import process_due_reminders_task

    assert process_due_reminders_task.name == "app.services.tasks.process_due_reminders_task"
    assert process_due_reminders_task.max_retries == 8
    assert process_due_reminders_task.retry_backoff == 5
    assert process_due_reminders_task.retry_backoff_max == 600
    assert celery_app.conf.task_default_queue == "temposort"
    assert celery_app.conf.beat_schedule["daily-reminder-digest"]["options"]["queue"] == "temposort"


def test_celery_retries_transient_delivery_failures(monkeypatch):
    from app.services.email_transport import RetryableEmailDeliveryError
    from app.services.reminder_service import reminder_service
    from app.services.tasks import process_due_reminders_task

    process = AsyncMock(side_effect=RetryableEmailDeliveryError("temporary provider outage"))
    monkeypatch.setattr(reminder_service, "process_due_reminders", process)

    result = process_due_reminders_task.apply(args=["user@example.invalid"], throw=False)

    assert result.failed()
    assert process.await_count == process_due_reminders_task.max_retries + 1


def setup_function() -> None:
    asyncio.run(store.clear())
    email_service.clear_history()


@pytest.fixture(autouse=True)
def prevent_external_email_delivery(monkeypatch):
    monkeypatch.setattr(
        "app.services.email_service.send_email_message",
        lambda *args, **kwargs: {"provider": "test", "status": "sent"},
    )


def test_health_check():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] in {"ok", "degraded"}
    assert response.json()["database_ok"] is True
    assert response.json()["redis_ok"] is True
    assert response.json()["queue"] == "temposort"
    assert "broker" not in response.json()
    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    assert "temposort_http_requests_total" in metrics.text
    assert "temposort_celery_queue_depth" in metrics.text


def test_reminder_routes_require_authentication():
    assert client.get("/api/v1/reminders").status_code == 401
    assert client.post("/api/v1/reminders/process").status_code == 401
    assert client.post(
        "/api/v1/reminders",
        json={
            "user_email": "alice@example.com",
            "title": "Reminder",
            "message": "Test",
            "channel": "email",
            "scheduled_for": datetime.now(timezone.utc).isoformat(),
        },
    ).status_code == 401


def test_queue_observability_reports_workers_and_depth(monkeypatch):
    from app.services import queue_observability
    from app.services.celery_app import celery_app
    from app.services.redis_service import redis_service

    class Inspect:
        def stats(self):
            return {"worker@localhost": {"pool": {}}}

    monkeypatch.setattr(redis_service, "ping", lambda: True)
    monkeypatch.setattr(redis_service, "queue_length", lambda queue="temposort": 3)
    monkeypatch.setattr(celery_app.control, "inspect", lambda timeout: Inspect())

    snapshot = queue_observability.queue_observability.snapshot()

    assert snapshot["redis_ok"] is True
    assert snapshot["celery_ok"] is True
    assert snapshot["worker_count"] == 1
    assert snapshot["queue_depth"] == 3


def test_queue_observability_caches_worker_snapshot(monkeypatch):
    from app.services.queue_observability import QueueObservability
    from app.services.celery_app import celery_app
    from app.services.redis_service import redis_service

    inspect = Mock()

    class FakeInspect:
        def stats(self):
            inspect()
            return {"worker@localhost": {}}

    monkeypatch.setattr(redis_service, "ping", lambda: True)
    monkeypatch.setattr(redis_service, "queue_length", lambda queue="temposort": 0)
    monkeypatch.setattr(celery_app.control, "inspect", lambda timeout: FakeInspect())
    observability = QueueObservability(worker_stats_ttl_seconds=60)

    observability.snapshot()
    observability.snapshot()

    inspect.assert_called_once()


def test_reminder_process_endpoint_only_enqueues(monkeypatch):
    from app.core.security import create_access_token
    from app.services.reminder_service import reminder_service

    enqueue = AsyncMock(return_value="celery-task-123")
    process = AsyncMock()
    monkeypatch.setattr(reminder_service, "enqueue_due_reminder_processing", enqueue)
    monkeypatch.setattr(reminder_service, "process_due_reminders", process)

    response = client.post(
        "/api/v1/reminders/process",
        headers={"Authorization": f"Bearer {create_access_token('user-123')}"},
    )

    assert response.status_code == 202
    assert response.json() == {"status": "queued", "task_id": "celery-task-123"}
    enqueue.assert_awaited_once()
    process.assert_not_awaited()


def test_reminder_process_endpoint_reports_broker_failure(monkeypatch):
    from app.core.security import create_access_token
    from app.services.reminder_service import reminder_service

    enqueue = AsyncMock(side_effect=RuntimeError("broker offline"))
    monkeypatch.setattr(reminder_service, "enqueue_due_reminder_processing", enqueue)

    response = client.post(
        "/api/v1/reminders/process",
        headers={"Authorization": f"Bearer {create_access_token('user-123')}"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Reminder queue is unavailable"


def test_redis_lock_requires_matching_owner_token():
    from app.services.redis_service import redis_service

    lock_key = f"test:lock:{uuid4().hex}"
    owner_token = redis_service.acquire_lock(lock_key, ttl_seconds=30)

    try:
        assert owner_token is not None
        assert redis_service.acquire_lock(lock_key, ttl_seconds=30) is None
        assert redis_service.release_lock(lock_key, "not-the-owner") is False
        assert redis_service.acquire_lock(lock_key, ttl_seconds=30) is None
        assert redis_service.release_lock(lock_key, owner_token) is True
        assert redis_service.acquire_lock(lock_key, ttl_seconds=30) is not None
    finally:
        redis_service.delete(lock_key)


def test_failed_email_delivery_is_not_marked_sent(monkeypatch):
    from app.services.email_service import email_service
    from app.services.reminder_service import reminder_service
    from app.services.redis_service import redis_service

    due_reminder = {
        "id": "reminder-failed-delivery",
        "user_email": "alice@example.com",
        "title": "Reminder",
        "message": "Test",
    }
    monkeypatch.setattr(
        reminder_service.repo.reminders,
        "list_due_reminders",
        AsyncMock(return_value=[due_reminder]),
    )
    monkeypatch.setattr(
        reminder_service.user_repo,
        "get_user_by_email",
        AsyncMock(return_value={"email": "alice@example.com", "name": "Alice"}),
    )
    mark_sent = AsyncMock()
    monkeypatch.setattr(reminder_service.repo.reminders, "mark_reminder_sent", mark_sent)
    monkeypatch.setattr(redis_service, "acquire_lock", lambda *args, **kwargs: "lock-owner")
    release_lock = Mock(return_value=True)
    monkeypatch.setattr(redis_service, "release_lock", release_lock)
    monkeypatch.setattr(
        email_service,
        "send_reminder_email",
        lambda **kwargs: {"delivery": {"status": "queued"}},
    )

    with pytest.raises(RuntimeError, match="Failed to deliver reminder"):
        asyncio.run(reminder_service.process_due_reminders())

    mark_sent.assert_not_awaited()
    release_lock.assert_called_once_with("reminder:send:reminder-failed-delivery", "lock-owner")


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
    response_json = register_response.json()
    assert "verification_required" in response_json
    assert "email_delivery" in response_json
    assert response_json["user"]["email"] == "alice@example.com"

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


def test_task_creation_idempotency_replays_and_rejects_payload_mismatch():
    from app.core.security import create_access_token
    from app.db.repositories.user_repository import UserRepository

    user = asyncio.run(UserRepository().create_user("Idempotency User", "idempotency@example.com", "unused"))
    token = create_access_token(user["id"])
    headers = {
        "Authorization": f"Bearer {token}",
        "Idempotency-Key": "create-task-demo-1",
    }
    payload = {"title": "Retry-safe task", "priority": "high"}

    first = client.post("/api/v1/tasks", json=payload, headers=headers)
    replay = client.post("/api/v1/tasks", json=payload, headers=headers)

    assert first.status_code == 201
    assert replay.status_code == 201
    assert replay.json()["id"] == first.json()["id"]

    conflict = client.post(
        "/api/v1/tasks",
        json={"title": "Different payload", "priority": "high"},
        headers=headers,
    )
    assert conflict.status_code == 409

    tasks = client.get("/api/v1/tasks", headers=headers).json()
    assert len([task for task in tasks if task["id"] == first.json()["id"]]) == 1


def test_due_reminders_can_be_processed(monkeypatch):
    from app.services.reminder_service import reminder_service

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
        json={"email": "alice@example.com", "password": "secret123"},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    reminder_response = client.post(
        "/api/v1/reminders",
        headers=headers,
        json={
            "user_email": "alice@example.com",
            "title": "Task reminder",
            "message": "Your task is due soon.",
            "channel": "email",
            "scheduled_for": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
        },
    )
    assert reminder_response.status_code == 201

    monkeypatch.setattr(
        reminder_service,
        "enqueue_due_reminder_processing",
        AsyncMock(return_value="test-celery-task"),
    )
    process_response = client.post("/api/v1/reminders/process", headers=headers)
    assert process_response.status_code == 202
    assert process_response.json()["status"] == "queued"

    from app.services.reminder_service import reminder_service

    processed = asyncio.run(reminder_service.process_due_reminders())
    assert processed == 1
    assert email_service.sent_messages[-1]["to"] == "alice@example.com"


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
    from app.core.security import decode_access_token
    from app.db.repositories.reminder_repository import ReminderRepository
    from app.db.repositories.task_repository import TaskRepository

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
    headers = {"Authorization": f"Bearer {token}"}
    user_id = decode_access_token(token)["sub"]

    task_response = client.post(
        "/api/v1/tasks",
        headers=headers,
        json={"title": "Cascade delete task", "priority": "low"},
    )
    assert task_response.status_code == 201

    reminder_response = client.post(
        "/api/v1/reminders",
        headers=headers,
        json={
            "user_email": "alice@example.com",
            "title": "Cascade delete reminder",
            "message": "This should be removed with the user.",
            "scheduled_for": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        },
    )
    assert reminder_response.status_code == 201

    delete_response = client.post(
        "/api/v1/auth/delete-user",
        json={"email": "alice@example.com", "password": "secret123"},
        headers=headers,
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["deleted"] is True
    assert asyncio.run(TaskRepository().list_tasks_for_user(user_id)) == []
    assert asyncio.run(ReminderRepository().list_reminders("alice@example.com")) == []

    follow_up_login = client.post(
        "/api/v1/auth/login",
        json={
            "email": "alice@example.com",
            "password": "secret123",
        },
    )
    assert follow_up_login.status_code == 401


def test_smtp_failures_are_exposed_in_result(monkeypatch):
    from app.services import email_transport

    class FakeSMTP:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def ehlo(self, *args, **kwargs):
            return None

        def starttls(self):
            raise smtplib.SMTPAuthenticationError(535, b'bad credentials')

        def login(self, *args, **kwargs):
            raise smtplib.SMTPAuthenticationError(535, b'bad credentials')

        def send_message(self, *args, **kwargs):
            raise smtplib.SMTPAuthenticationError(535, b'bad credentials')

    monkeypatch.setattr(email_transport, "settings", type("S", (), {"smtp_host": "smtp.gmail.com", "smtp_port": 587, "smtp_username": "user@example.com", "smtp_password": type("P", (), {"get_secret_value": lambda self: "pw"})(), "smtp_from_name": "TempoSort", "smtp_from_email": "no-reply@example.com", "enable_ssl": True, "mail_provider": "smtp"})())
    monkeypatch.setattr(email_transport.smtplib, "SMTP", FakeSMTP)

    result = email_transport.send_via_smtp("to@example.com", "Subject", "<p>Hi</p>")

    assert result["status"] == "failed"
    assert "error" in result
    assert "bad credentials" in result["error"].lower()


def test_resend_failures_are_exposed_in_result(monkeypatch):
    from app.services import email_transport

    def fake_post(*args, **kwargs):
        raise httpx.HTTPError("network error")

    monkeypatch.setattr(
        email_transport,
        "settings",
        type(
            "S",
            (),
            {
                "resend_api_key": type("P", (), {"get_secret_value": lambda self: "abc123"})(),
                "smtp_from_name": "TempoSort",
                "smtp_from_email": "no-reply@example.com",
                "mail_provider": "resend",
            },
        )(),
    )
    monkeypatch.setattr(email_transport.httpx, "post", fake_post)

    result = email_transport.send_via_resend("to@example.com", "Subject", "<p>Hi</p>")

    assert result["status"] == "failed"
    assert "network error" in result["error"]
    assert result["retryable"] is True


@pytest.mark.parametrize(("status_code", "retryable"), [(429, True), (503, True), (422, False)])
def test_resend_http_errors_are_classified_for_retry(monkeypatch, status_code, retryable):
    from app.services import email_transport

    class FakeResponse:
        text = "provider response"

        def __init__(self, status):
            self.status_code = status

        def raise_for_status(self):
            request = httpx.Request("POST", "https://api.resend.com/emails")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("provider error", request=request, response=response)

    monkeypatch.setattr(
        email_transport,
        "settings",
        type(
            "S",
            (),
            {
                "resend_api_key": type("P", (), {"get_secret_value": lambda self: "abc123"})(),
                "smtp_from_name": "TempoSort",
                "smtp_from_email": "no-reply@example.com",
                "mail_provider": "resend",
            },
        )(),
    )
    monkeypatch.setattr(email_transport.httpx, "post", lambda *args, **kwargs: FakeResponse(status_code))

    result = email_transport.send_via_resend("to@example.com", "Subject", "<p>Hi</p>")

    assert result["status"] == "failed"
    assert result["retryable"] is retryable


def test_resend_email_sends_stable_idempotency_key(monkeypatch):
    from app.services import email_transport

    captured = {}

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"id": "email-123"}

    def fake_post(url, *, headers, **kwargs):
        captured.update(headers)
        return FakeResponse()

    monkeypatch.setattr(
        email_transport,
        "settings",
        type(
            "S",
            (),
            {
                "resend_api_key": type("P", (), {"get_secret_value": lambda self: "abc123"})(),
                "smtp_from_name": "TempoSort",
                "smtp_from_email": "no-reply@example.com",
                "mail_provider": "resend",
            },
        )(),
    )
    monkeypatch.setattr(email_transport.httpx, "post", fake_post)

    result = email_transport.send_via_resend(
        "to@example.com",
        "Subject",
        "<p>Hi</p>",
        idempotency_key="reminder-123",
    )

    assert result["status"] == "sent"
    assert captured["Idempotency-Key"] == "reminder-123"


def test_email_delivery_outcome_increments_provider_metric(monkeypatch):
    from app.services import email_transport
    from app.services.telemetry import EMAIL_DELIVERIES

    monkeypatch.setattr(
        email_transport,
        "settings",
        type("S", (), {"mail_provider": "resend"})(),
    )
    monkeypatch.setattr(
        email_transport,
        "send_via_resend",
        lambda *args, **kwargs: {"provider": "resend", "status": "sent"},
    )
    counter = EMAIL_DELIVERIES.labels("resend", "sent")
    before = counter._value.get()

    result = email_transport.send_email_message("to@example.com", "Subject", "<p>Hi</p>")

    assert result["status"] == "sent"
    assert counter._value.get() == before + 1
