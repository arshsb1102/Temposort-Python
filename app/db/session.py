from __future__ import annotations

import asyncio
from contextlib import contextmanager
from typing import Any, Callable, Iterator

import psycopg
from psycopg.rows import dict_row


class DatabaseSession:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.connection = psycopg.connect(database_url, autocommit=False)
        self._create_tables()

    @contextmanager
    def cursor(self) -> Iterator[Any]:
        with self.connection.cursor(row_factory=dict_row) as cursor:
            yield cursor

    def _create_tables(self) -> None:
        with self.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    due_at TIMESTAMPTZ,
                    priority TEXT NOT NULL DEFAULT 'medium',
                    is_completed BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                );

                CREATE TABLE IF NOT EXISTS reminders (
                    id TEXT PRIMARY KEY,
                    user_email TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    channel TEXT NOT NULL,
                    scheduled_for TIMESTAMPTZ NOT NULL,
                    sent_at TIMESTAMPTZ,
                    is_sent BOOLEAN NOT NULL DEFAULT FALSE
                );

                CREATE TABLE IF NOT EXISTS verification_tokens (
                    token TEXT PRIMARY KEY,
                    email TEXT NOT NULL
                );
                """
            )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    async def run_async(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return await asyncio.to_thread(func, *args, **kwargs)
