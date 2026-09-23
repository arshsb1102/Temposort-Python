# TempoSort FastAPI Learning Project

This folder is a beginner-friendly FastAPI version of the TempoSort backend. It is meant to help you learn FastAPI by mirroring the same core ideas from the main C# project: authentication, task management, health checks, and clean API design.

## Why this exists

The main TempoSort project is built with ASP.NET Core and .NET services. This Python folder is a simplified learning version that lets you study the same business flow in a lighter framework.

The goal is to understand:

- route definitions in FastAPI
- request/response schemas with Pydantic
- in-memory persistence for learning
- auth and task endpoints
- API testing with pytest
- how a real API is structured in a simple project

## Project structure

```bash
Temposort-Python/
├── app/
│   ├── __init__.py
│   ├── db.py
│   ├── main.py
│   └── schemas.py
├── tests/
│   └── test_app.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Included endpoints

- `GET /api/v1/health` — service status check
- `POST /api/v1/auth/register` — create a user
- `POST /api/v1/auth/login` — demo login flow
- `POST /api/v1/tasks` — create a task
- `GET /api/v1/tasks` — list tasks
- `GET /api/v1/tasks/{task_id}` — fetch one task
- `PUT /api/v1/tasks/{task_id}` — update a task
- `PATCH /api/v1/tasks/{task_id}/toggle-complete` — toggle task completion

## Quick start

```bash
cd Temposort-Python

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

uvicorn app.main:app --reload
```

Then open:

- `http://127.0.0.1:8000/docs` for Swagger UI
- `http://127.0.0.1:8000/redoc` for ReDoc

## Example request

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Learn FastAPI",
    "description": "Build the first API draft for TempoSort",
    "due_at": "2026-10-01T10:00:00Z",
    "priority": "high"
  }'
```

## Learning goals

By working through this project, you will learn:

1. How FastAPI apps are organized
2. How request validation works with Pydantic
3. How to structure routes by feature
4. How to model a domain with simple in-memory services
5. How to test API behavior with pytest

## Next steps

Once you are comfortable here, the next progression is to add:

- real database integration with SQLAlchemy or SQLModel
- JWT authentication with `python-jose` or `PyJWT`
- password hashing with `passlib`
- background jobs for reminders
- project structure split into routers, services, and repos

This starter is intentionally simple so you can focus on learning the FastAPI patterns before moving into a production-grade backend.
