from __future__ import annotations

import os
import time
from threading import Lock
from typing import Any

from celery.signals import task_postrun, task_prerun, worker_ready
from fastapi import FastAPI, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    REGISTRY,
    generate_latest,
    start_http_server,
)
from prometheus_client.multiprocess import MultiProcessCollector
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.environment import settings

HTTP_REQUESTS = Counter(
    "temposort_http_requests_total",
    "Completed API requests",
    ("method", "route", "status"),
)
HTTP_DURATION = Histogram(
    "temposort_http_request_duration_seconds",
    "API request duration in seconds",
    ("method", "route"),
)
CELERY_TASKS = Counter(
    "temposort_celery_tasks_total",
    "Completed Celery task attempts",
    ("task", "state"),
)
CELERY_TASK_DURATION = Histogram(
    "temposort_celery_task_duration_seconds",
    "Celery task attempt duration in seconds",
    ("task",),
)
EMAIL_DELIVERIES = Counter(
    "temposort_email_deliveries_total",
    "Email provider delivery outcomes",
    ("provider", "status"),
)
QUEUE_DEPTH = Gauge("temposort_celery_queue_depth", "Number of ready jobs in the default Celery queue")
CELERY_WORKERS = Gauge("temposort_celery_workers", "Number of responding Celery workers")
_TASK_STARTS: dict[str, float] = {}
_TASK_STARTS_LOCK = Lock()
_TELEMETRY_CONFIGURED = False
_TRACER_PROVIDER: Any = None


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        started_at = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            route = request.scope.get("route")
            route_name = getattr(route, "path", "unmatched")
            HTTP_REQUESTS.labels(request.method, route_name, str(status_code)).inc()
            HTTP_DURATION.labels(request.method, route_name).observe(time.perf_counter() - started_at)


def metrics_response() -> Response:
    multiprocess_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if multiprocess_dir:
        registry = CollectorRegistry()
        MultiProcessCollector(registry)
        payload = generate_latest(registry)
    else:
        payload = generate_latest(REGISTRY)
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)


@task_prerun.connect(weak=False)
def record_task_start(task_id: str | None = None, **_: Any) -> None:
    if task_id:
        with _TASK_STARTS_LOCK:
            _TASK_STARTS[task_id] = time.perf_counter()


@task_postrun.connect(weak=False)
def record_task_completion(task_id: str | None = None, task: Any = None, state: str = "UNKNOWN", **_: Any) -> None:
    task_name = getattr(task, "name", "unknown")
    CELERY_TASKS.labels(task_name, state.lower()).inc()
    if task_id:
        with _TASK_STARTS_LOCK:
            started_at = _TASK_STARTS.pop(task_id, None)
        if started_at is not None:
            CELERY_TASK_DURATION.labels(task_name).observe(time.perf_counter() - started_at)


def start_worker_metrics_server(**_: Any) -> None:
    if not settings.metrics_enabled or not os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        return
    registry = CollectorRegistry()
    MultiProcessCollector(registry)
    port = int(os.environ.get("WORKER_METRICS_PORT", "9100"))
    start_http_server(port=port, addr="0.0.0.0", registry=registry)


worker_ready.connect(start_worker_metrics_server, weak=False)


def _get_tracer_provider() -> Any:
    global _TRACER_PROVIDER
    if _TRACER_PROVIDER is not None:
        return _TRACER_PROVIDER
    if not settings.otel_enabled:
        return None

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "deployment.environment": settings.app_env,
        }
    )
    provider = TracerProvider(resource=resource)
    endpoint = settings.otel_exporter_otlp_endpoint.rstrip("/")
    if not endpoint.endswith("/v1/traces"):
        endpoint = f"{endpoint}/v1/traces"
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    _TRACER_PROVIDER = provider
    return provider


def configure_tracing(app: FastAPI) -> None:
    global _TELEMETRY_CONFIGURED
    if _TELEMETRY_CONFIGURED or not settings.otel_enabled:
        return

    from opentelemetry.instrumentation.celery import CeleryInstrumentor
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

    from app.db.base import engine

    provider = _get_tracer_provider()
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine, tracer_provider=provider)
    CeleryInstrumentor().instrument(tracer_provider=provider)
    _TELEMETRY_CONFIGURED = True


def configure_worker_tracing() -> None:
    if not settings.otel_enabled:
        return
    from opentelemetry.instrumentation.celery import CeleryInstrumentor

    CeleryInstrumentor().instrument(tracer_provider=_get_tracer_provider())
