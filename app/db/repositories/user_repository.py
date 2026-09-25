from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    def create_user(self, name: str, email: str, password_hash: str) -> dict[str, Any]:
        email_key = email.lower()
        if self.get_user_by_email(email_key) is not None:
            raise ValueError("Email already registered.")

        user_id = __import__("uuid").uuid4().hex
        now = datetime.now(timezone.utc)
        with self.session.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO users (id, name, email, password_hash, is_verified, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, name, email_key, password_hash, False, now),
            )
        self.session.connection.commit()
        return self.get_user_by_id(user_id)

    async def async_create_user(self, name: str, email: str, password_hash: str) -> dict[str, Any]:
        return await asyncio.to_thread(self.create_user, name, email, password_hash)

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        with self.session.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE lower(email) = lower(%s)", (email,))
            row = cursor.fetchone()
        return self._row_to_dict(row)

    async def async_get_user_by_email(self, email: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self.get_user_by_email, email)

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        with self.session.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
        return self._row_to_dict(row)

    async def async_get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self.get_user_by_id, user_id)

    def set_user_verified(self, email: str) -> dict[str, Any] | None:
        with self.session.cursor() as cursor:
            cursor.execute("UPDATE users SET is_verified = TRUE WHERE lower(email) = lower(%s)", (email,))
        self.session.connection.commit()
        return self.get_user_by_email(email)

    async def async_set_user_verified(self, email: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self.set_user_verified, email)

    def create_verification_token(self, email: str, token: str) -> None:
        with self.session.cursor() as cursor:
            cursor.execute(
                "INSERT INTO verification_tokens (token, email) VALUES (%s, %s)",
                (token, email.lower()),
            )
        self.session.connection.commit()

    async def async_create_verification_token(self, email: str, token: str) -> None:
        await asyncio.to_thread(self.create_verification_token, email, token)

    def verify_email_token(self, token: str) -> str | None:
        with self.session.cursor() as cursor:
            cursor.execute("SELECT email FROM verification_tokens WHERE token = %s", (token,))
            row = cursor.fetchone()
            if row is None:
                return None
            email = row["email"]
            cursor.execute("DELETE FROM verification_tokens WHERE token = %s", (token,))
        self.session.connection.commit()
        return email

    async def async_verify_email_token(self, token: str) -> str | None:
        return await asyncio.to_thread(self.verify_email_token, token)

    def delete_user(self, email: str) -> bool:
        user = self.get_user_by_email(email)
        if user is None:
            return False

        with self.session.cursor() as cursor:
            cursor.execute("DELETE FROM verification_tokens WHERE lower(email) = lower(%s)", (email,))
            cursor.execute("DELETE FROM reminders WHERE lower(user_email) = lower(%s)", (email,))
            cursor.execute("DELETE FROM tasks WHERE user_id = %s", (user["id"],))
            cursor.execute("DELETE FROM users WHERE lower(email) = lower(%s)", (email,))
        self.session.connection.commit()
        return True

    async def async_delete_user(self, email: str) -> bool:
        return await asyncio.to_thread(self.delete_user, email)
