# TempoSort FastAPI

TempoSort is a FastAPI backend for a productivity and reminder system. It handles authentication, task management, email verification, and scheduled reminder processing. The project is structured as a backend service with route handlers, service-layer logic, storage abstraction, and environment-driven configuration.

## What this app does

The application supports:

- user registration
- email verification before login
- JWT-based authentication
- protected authenticated routes
- task creation, listing, fetching, updating, toggling, and deletion
- reminder scheduling and processing
- PostgreSQL-backed persistence for a production-style setup
- scheduler-driven reminder checks

This is a backend-first product app, not a frontend app. The API is the main interface.

## Core business flow

1. A user registers with name, email, and password.
2. The app creates the user and sends a verification email.
3. The user verifies their email using the token in the verification link.
4. The user logs in and receives a JWT access token.
5. The JWT is required for task and reminder endpoints.
6. The user can create and manage tasks.
7. Due reminders are processed by a scheduler and delivered through the configured email channel.

## Architecture

The app is split into small layers:

- `app/api/routes` - HTTP endpoints
- `app/services` - business logic
- `app/storage` - persistence implementations
- `app/core` - configuration and security helpers
- `app/schemas` - request/response models
- `app/db.py` - store factory pointing to the active storage backend
- `app/main.py` - app entry point and startup lifecycle

## Tech stack

- Python 3.12+
- FastAPI
- Pydantic
- PostgreSQL
- psycopg
- JWT via PyJWT
- APScheduler for background reminder processing
- pytest for API testing
- python-dotenv for environment configuration

## Project layout

```bash
Temposort-Python/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── auth.py
│   │       ├── health.py
│   │       ├── reminders.py
│   │       └── tasks.py
│   ├── core/
│   │   ├── environment.py
│   │   └── security.py
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── email_service.py
│   │   ├── reminder_service.py
│   │   ├── scheduler.py
│   │   └── task_service.py
│   ├── storage/
│   │   ├── postgres_store.py
│   │   ├── sqlite_store.py
│   │   └── __init__.py
│   ├── __init__.py
│   ├── db.py
│   ├── main.py
│   └── schemas.py
├── tests/
│   └── test_app.py
├── .env
├── .env.example
├── docker-compose.yml
├── requirements.txt
├── pytest.ini
├── README.md
└── .gitignore
```

## Configuration

The app reads configuration from environment variables and `.env` files. The main config is in `app/core/environment.py`.

Key variables:

```env
APP_NAME=TempoSort FastAPI
APP_ENV=development
DEBUG=false
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/temposort
API_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
MAIL_PROVIDER=console
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=no-reply@temposort.local
SMTP_FROM_NAME=TempoSort
SMTP_ENABLE_SSL=false
RESEND_API_KEY=
```

Important:

- `DATABASE_URL` should point to Postgres in production.
- `MAIL_PROVIDER=console` is the safe default for local development and tests.
- Real SMTP or Resend settings are used when configured.

## Storage layer

The project supports a storage abstraction through the store object in `app/db.py`.

Current behavior:

- if `DATABASE_URL` starts with `sqlite`, the app uses `SQLiteStore`
- otherwise it uses `PostgresStore`

This makes the code usable in local development and production-like environments without changing route logic.

## Data model

### User

Fields include:

- `id`
- `name`
- `email`
- `password_hash`
- `is_verified`
- `created_at`

### Task

Fields include:

- `id`
- `user_id`
- `title`
- `description`
- `due_at`
- `priority`
- `is_completed`
- `created_at`
- `updated_at`

### Reminder

Fields include:

- `id`
- `user_email`
- `title`
- `message`
- `channel`
- `scheduled_for`
- `sent_at`
- `is_sent`

## API routes

### Health

- `GET /api/v1/health`
  - returns app health data

### Auth

- `POST /api/v1/auth/register`
  - creates a user
  - sends a verification email
  - returns a registration response

- `POST /api/v1/auth/login`
  - validates email and password
  - rejects unverified users with 403
  - returns JWT token

- `GET /api/v1/auth/verify-email?token=...`
  - verifies the email token
  - marks the user as verified

- `POST /api/v1/auth/resend-verification`
  - resends the verification email

- `GET /api/v1/auth/me`
  - returns the current user id from the JWT

### Tasks

- `POST /api/v1/tasks`
  - creates a task for the authenticated user

- `GET /api/v1/tasks`
  - lists all tasks for the current user

- `GET /api/v1/tasks/{task_id}`
  - fetches a single task

- `PUT /api/v1/tasks/{task_id}`
  - updates a task

- `PATCH /api/v1/tasks/{task_id}/toggle-complete`
  - toggles `is_completed`

- `DELETE /api/v1/tasks/{task_id}`
  - deletes the task for the authenticated user

### Reminders

- `POST /api/v1/reminders`
  - creates a reminder for a user email

- `GET /api/v1/reminders`
  - lists reminder records

- `POST /api/v1/reminders/process`
  - processes all due reminders and marks them sent

## Security model

The app uses bearer-token auth.

- `HTTPBearer` is configured in `app/core/security.py`
- JWT is created with `create_access_token()`
- routes depend on `get_current_user_id()`
- auth failures return 401 if token is missing or invalid
- login for unverified users returns 403

Password hashing is handled with bcrypt, and token verification is done with PyJWT.

## Email and reminder flow

The reminder pipeline is built around these components:

- `EmailService` - builds and stores emails
- `ReminderService` - checks due reminders and sends email notices
- `SchedulerService` - runs reminder processing with APScheduler

Reminder processing flow:

1. a reminder is scheduled with a user email and due time
2. scheduler checks due reminders periodically
3. matching user is looked up
4. reminder email is sent
5. reminder is marked as sent

## Local development

### Prerequisites

- Python
- pip or uv
- Docker for Postgres if using the production-style local database

### Setup

```bash
cd Temposort-Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Note: this project pins `httpx2` in [requirements.txt](requirements.txt) because the FastAPI/Starlette test client stack emits a deprecation warning when the older `httpx` compatibility path is used.

### Start Postgres

```bash
docker compose up -d postgres
```

### Start the app

```bash
uvicorn app.main:app --reload
```

Swagger UI:

- http://127.0.0.1:8000/docs

ReDoc:

- http://127.0.0.1:8000/redoc

## Testing

The app has tests covering:

- health endpoint
- registration and email verification
- login enforcement before verification
- task auth requirements
- due reminder processing
- task deletion

Run tests with:

```bash
uv run pytest -q
```

## Current status

This project is a working backend foundation for TempoSort. It has the key production traits expected from a SaaS-style API:

- layered architecture
- JWT auth
- task lifecycle
- verification flow
- reminder processing
- production-oriented configuration
- Postgres-ready storage setup

It is not a full deployable SaaS stack by itself yet. Real delivery services, migrations, monitoring, and deployment infrastructure still need to be added as the project expands.

## Practical summary

If you want the short version:

This project is a FastAPI backend for a task-driven productivity platform. It supports user registration, verification, secure login, task management, and reminder automation. It is structured for real-world backend work, uses environment-based configuration, and is designed to run with PostgreSQL in production-oriented environments.
