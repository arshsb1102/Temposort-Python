# Local API Demo

This walkthrough registers an email you control, verifies it, creates a task through the authenticated API, fetches the task back, and confirms the database row. The task is intentionally left in the database so you can inspect it.

## Start the stack

If `.env` does not exist yet, copy the example and configure an email provider before using registration:

```bash
cp .env.example .env
```

For actual email delivery, configure either Resend with a verified sender or SMTP credentials in `.env`. Do not put real credentials in this file in source control; `.env` is ignored and excluded from the Docker build context.

Start all services (the one-shot `init-db` service applies Alembic migrations first):

```bash
docker compose up -d --build
docker compose ps
```

Wait until the API health check reports `healthy`, then check it directly:

```bash
curl -i http://127.0.0.1:8000/api/v1/health
```

Expected health JSON includes `"redis_ok":true`, `"celery_ok":true`, `"worker_count":1` or greater, and `"queue_depth":0` when idle.

## Register and verify

Use an inbox you control. On a fresh local database, registration sends a verification email. If this account is already registered, skip registration and use its password; verified accounts can proceed straight to login.

```bash
export DEMO_EMAIL='your-address@example.com'
printf 'Choose a password for this local demo account: '
read -r -s DEMO_PASSWORD
printf '\n'
export DEMO_PASSWORD

curl -i -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d "$(python3 -c 'import json,os; print(json.dumps({"name":"API Demo","email":os.environ["DEMO_EMAIL"],"password":os.environ["DEMO_PASSWORD"]}))')"
```

Open the verification email, copy the token from its link, then:

```bash
export VERIFY_TOKEN='paste-the-token-from-your-email'
curl -i -G http://127.0.0.1:8000/api/v1/auth/verify-email \
  --data-urlencode "token=$VERIFY_TOKEN"
```

## Log in and create a task

The token stays in a shell variable and is not printed:

```bash
LOGIN_JSON="$(curl -fsS -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d "$(python3 -c 'import json,os; print(json.dumps({"email":os.environ["DEMO_EMAIL"],"password":os.environ["DEMO_PASSWORD"]}))')")"
export LOGIN_JSON
export ACCESS_TOKEN="$(python3 -c 'import json,os; print(json.loads(os.environ["LOGIN_JSON"])["access_token"])')"

TASK_JSON="$(curl -fsS -X POST http://127.0.0.1:8000/api/v1/tasks \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"title":"TempoSort API demo task","description":"Created with curl and stored in PostgreSQL.","priority":"high"}')"
export TASK_JSON
export TASK_ID="$(python3 -c 'import json,os; print(json.loads(os.environ["TASK_JSON"])["id"])')"
printf '%s\n' "$TASK_JSON"
```

Fetch the task and list the authenticated user's tasks:

```bash
curl -i "http://127.0.0.1:8000/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

curl -i http://127.0.0.1:8000/api/v1/tasks \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

The task-create endpoint supports `Idempotency-Key`. Retrying the same payload with the same key returns the existing task; reusing the key with a different body returns `409`:

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/tasks \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Idempotency-Key: demo-create-task-001' \
  -d '{"title":"Idempotent demo task","priority":"high"}'
```

Confirm the exact task row exists in PostgreSQL:

```bash
docker compose exec -T postgres psql -U postgres -d temposort -c \
  "SELECT t.id, u.email, t.title, t.priority, t.is_completed FROM tasks AS t JOIN users AS u ON u.id = t.user_id WHERE t.id = '$TASK_ID';"
```

The returned row should have the same task ID and email as the API response. Retrying the same payload with the same `Idempotency-Key` returns the existing task; changing the payload while reusing the key returns `409`.

## Queue check

Due-reminder processing is submitted to Celery and returns `202 Accepted`; the request does not also process reminders inline:

```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/reminders/process \
  -H "Authorization: Bearer $ACCESS_TOKEN"

docker compose logs --tail=100 worker beat
curl -sS http://127.0.0.1:8000/api/v1/health
```

## Test isolation

Tests use the dedicated PostgreSQL database `temposort_test` (override with `TEST_DATABASE_URL`). They clear that database between tests, not the app database configured in `.env`.

```bash
.venv/bin/pytest -q
```

Run the read-only API health load probe. It reports throughput and p50/p95/p99 latency; it does not represent task-write or email-provider throughput:

```bash
.venv/bin/python scripts/load_test_health.py --requests 100 --concurrency 10
```

For actual authenticated task-write throughput, the script removes successfully created probe tasks afterward:

```bash
DEMO_ACCESS_TOKEN="$ACCESS_TOKEN" .venv/bin/python scripts/load_test_tasks.py --requests 100 --concurrency 10
```

Enable OTEL trace export and dashboards by setting a strong local `GRAFANA_ADMIN_PASSWORD`, then:

```bash
OTEL_ENABLED=true docker compose --profile observability up -d --build
```

Open Grafana at http://127.0.0.1:3000 (`admin` plus `GRAFANA_ADMIN_PASSWORD`). The development-only fallback is `TempoSort-Local-Only-2026!`; replace it in `.env` before use beyond a local machine. Grafana provisions `TempoSort Production Overview` and `TempoSort Queue and Delivery Operations` automatically.

Final local readiness run (100 requests, concurrency 10, loopback, warm API; includes cached Celery inspection and PostgreSQL `SELECT 1`): 377.12 requests/sec, p50 20.95 ms, p95 54.18 ms, p99 59.22 ms. All 100 requests returned HTTP 200.

Final-schema local authenticated task-write run with the observability profile enabled (100 creates, concurrency 10): 223.48 requests/sec, p50 35.27 ms, p95 125.33 ms, p99 126.81 ms; all 100 returned 201 and all 100 temporary tasks were deleted. These are single-machine development measurements, not production capacity or email-provider throughput.

## Cleanup

To remove the demo task, use its authenticated delete endpoint:

```bash
curl -i -X DELETE "http://127.0.0.1:8000/api/v1/tasks/$TASK_ID" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Stop the local stack when finished:

```bash
docker compose down
```
