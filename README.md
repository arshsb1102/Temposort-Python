# TempoSort FastAPI

Production-grade FastAPI backend for the TempoSort platform, designed to mirror the operational pattern of the .NET implementation while remaining portable in a Python runtime.

## Project scope

This backend is built for a real SaaS-style workflow and includes:

- authentication with JWT
- email verification and resend flow
- task lifecycle management
- reminder scheduling and processing
- environment-driven deployment configuration
- provider abstraction for SMTP and Resend
- PostgreSQL-backed persistence for production parity with the .NET service

## Architectural pattern

The project is organized into distinct layers to keep the backend maintainable and production-friendly:

```bash
Temposort-Python/
├── app/
│   ├── api/
│   │   └── routes/
│   ├── core/
│   ├── services/
│   ├── storage/
│   ├── __init__.py
│   ├── db.py
│   ├── main.py
│   └── schemas.py
├── tests/
│   └── test_app.py
├── .env.example
├── requirements.txt
├── README.md
└── .gitignore
```

## API surface

### Authentication
- `POST /api/v1/auth/register` creates a new user and sends a verification email
- `POST /api/v1/auth/login` validates credentials and enforces verification
- `GET /api/v1/auth/verify-email` confirms the token from the email link
- `POST /api/v1/auth/resend-verification` re-sends verification instructions

### Tasks
- `POST /api/v1/tasks` creates a task
- `GET /api/v1/tasks` lists tasks
- `GET /api/v1/tasks/{task_id}` fetches one task
- `PUT /api/v1/tasks/{task_id}` updates a task
- `PATCH /api/v1/tasks/{task_id}/toggle-complete` toggles completion
- `DELETE /api/v1/tasks/{task_id}` removes a task

### Reminders
- `POST /api/v1/reminders` schedules a reminder
- `GET /api/v1/reminders` lists reminders
- `POST /api/v1/reminders/process` processes all due reminders

## Production-grade configuration

The service is configured through environment variables instead of hardcoded URLs or secrets.

```bash
cp .env.example .env
```

Example values:

```env
APP_ENV=production
JWT_SECRET=your-production-secret
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/temposort
API_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
MAIL_PROVIDER=console

# Production mail setup
# MAIL_PROVIDER=smtp
# SMTP_HOST=smtp.yourdomain.com
# SMTP_PORT=587
# SMTP_USERNAME=your-user
# SMTP_PASSWORD=your-password
# SMTP_FROM_EMAIL=no-reply@yourdomain.com
# SMTP_FROM_NAME=TempoSort
# SMTP_ENABLE_SSL=true

# Or use Resend
# MAIL_PROVIDER=resend
# RESEND_API_KEY=your_resend_key
```

Important: `MAIL_PROVIDER=console` is the safe default for local development and test environments. When you set a real provider and credentials, the app will deliver through that provider.

## Email provider behavior

This mirrors the .NET production pattern without making local development brittle:

- `MAIL_PROVIDER=smtp`: sends through the configured SMTP endpoint
- `MAIL_PROVIDER=resend`: sends via the Resend API
- `MAIL_PROVIDER=console`: queues the message output and avoids connection failures in non-configured environments

This prevents accidental crashes when SMTP secrets are not yet configured while still supporting real email delivery in production.

## Local startup

```bash
cd Temposort-Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Production readiness

This project is intended to be production-aligned and includes a Postgres-first data layer aligned with the .NET service. It can be extended with:

- Celery/RQ or APScheduler for reminder jobs
- Redis for distributed task queues
- structured logging and Prometheus metrics
- database migrations and CI verification
- deployment configuration for Docker/Kubernetes/Railway

## Quality standard

The backend follows the same operational pattern as the .NET version:

- environment-driven configuration
- explicit provider abstraction
- kept routes thin and feature-oriented
- business logic in service layer
- persisted domain state
- testable API behavior

This is no longer a toy learning project; it is a production-oriented backend foundation designed to mirror the TempoSort service architecture.
