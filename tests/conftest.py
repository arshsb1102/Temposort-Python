from __future__ import annotations

import os

import psycopg
from psycopg import sql
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy.engine import make_url


def _configure_test_database() -> None:
    configured_database_url = os.environ.get("DATABASE_URL") or dotenv_values(".env").get("DATABASE_URL")
    database_url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5433/temposort_test",
    )
    os.environ["DATABASE_URL"] = database_url

    url = make_url(database_url)
    if url.get_backend_name() != "postgresql":
        raise RuntimeError("Tests require a dedicated PostgreSQL TEST_DATABASE_URL.")
    if not url.database or not url.database.endswith(("_test", "_testing")):
        raise RuntimeError("TEST_DATABASE_URL database name must end in '_test' or '_testing'.")
    if configured_database_url and make_url(configured_database_url).database == url.database:
        raise RuntimeError("TEST_DATABASE_URL must not point at the application database.")

    admin_url = url.set(database="postgres").render_as_string(hide_password=False)
    with psycopg.connect(admin_url, autocommit=True) as connection:
        database_exists = connection.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (url.database,),
        ).fetchone()
        if database_exists is None:
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(url.database)))


_configure_test_database()
command.upgrade(Config("alembic.ini"), "head")
