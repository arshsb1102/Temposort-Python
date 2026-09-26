from __future__ import annotations

from typing import Any

from sqlalchemy import delete, func, select

from app.db.base import AsyncSessionLocal
from app.db.models import User, VerificationToken


class UserRepository:
    def __init__(self, session_factory=AsyncSessionLocal) -> None:
        self.session_factory = session_factory

    @staticmethod
    def _to_dict(user: User | None) -> dict[str, Any] | None:
        if user is None:
            return None
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "password_hash": user.password_hash,
            "is_verified": user.is_verified,
            "created_at": user.created_at,
        }

    async def create_user(self, name: str, email: str, password_hash: str) -> dict[str, Any]:
        normalized_email = email.lower()
        async with self.session_factory() as session:
            existing = await session.scalar(select(User).where(func.lower(User.email) == normalized_email))
            if existing is not None:
                raise ValueError("Email already registered.")

            user = User(
                name=name,
                email=normalized_email,
                password_hash=password_hash,
                is_verified=False,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return self._to_dict(user)

    async def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        normalized_email = email.lower()
        async with self.session_factory() as session:
            result = await session.execute(select(User).where(func.lower(User.email) == normalized_email))
            user = result.scalar_one_or_none()
            return self._to_dict(user)

    async def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        async with self.session_factory() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            return self._to_dict(user)

    async def set_user_verified(self, email: str) -> dict[str, Any] | None:
        normalized_email = email.lower()
        async with self.session_factory() as session:
            result = await session.execute(select(User).where(func.lower(User.email) == normalized_email))
            user = result.scalar_one_or_none()
            if user is None:
                return None

            user.is_verified = True
            await session.commit()
            await session.refresh(user)
            return self._to_dict(user)

    async def create_verification_token(self, email: str, token: str) -> None:
        normalized_email = email.lower()
        async with self.session_factory() as session:
            session.add(VerificationToken(token=token, email=normalized_email))
            await session.commit()

    async def verify_email_token(self, token: str) -> str | None:
        async with self.session_factory() as session:
            result = await session.execute(select(VerificationToken).where(VerificationToken.token == token))
            token_record = result.scalar_one_or_none()
            if token_record is None:
                return None

            email = token_record.email
            await session.execute(delete(VerificationToken).where(VerificationToken.token == token))
            await session.commit()
            return email

    async def delete_user(self, email: str) -> bool:
        normalized_email = email.lower()
        async with self.session_factory() as session:
            result = await session.execute(select(User).where(func.lower(User.email) == normalized_email))
            user = result.scalar_one_or_none()
            if user is None:
                return False

            await session.execute(delete(VerificationToken).where(func.lower(VerificationToken.email) == normalized_email))
            await session.delete(user)
            await session.commit()
            return True
