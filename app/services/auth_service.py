from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException, status

from app.core.security import create_access_token, hash_password, verify_password
from app.db.repositories.user_repository import UserRepository
from app.schemas import TokenResponse, UserLogin, UserRegister, VerificationStatus
from app.services.email_service import email_service


class AuthService:
    def __init__(self) -> None:
        self.repo = UserRepository()

    async def register_user(self, payload: UserRegister) -> dict:
        user = await self.repo.get_user_by_email(payload.email)
        if user is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")

        created_user = await self.repo.create_user(
            name=payload.name,
            email=payload.email,
            password_hash=hash_password(payload.password),
        )
        token = str(uuid4())
        await self.repo.create_verification_token(created_user["email"], token)
        delivery = email_service.send_verification_email(created_user["email"], created_user["name"], token)

        return {
            "id": created_user["id"],
            "name": created_user["name"],
            "email": created_user["email"],
            "verification_required": True,
            "email_delivery": delivery.get("delivery", {}),
        }

    async def login_user(self, payload: UserLogin) -> TokenResponse:
        user = await self.repo.get_user_by_email(payload.email)
        if user is None or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
        if not user.get("is_verified", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email before logging in.",
            )

        token = create_access_token(str(user["id"]), email=user["email"], name=user["name"])
        return TokenResponse(access_token=token, token_type="bearer")

    async def verify_email(self, token: str) -> VerificationStatus:
        email = await self.repo.verify_email_token(token)
        if email is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification link.")

        user = await self.repo.set_user_verified(email)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not registered.")

        return VerificationStatus(
            verified=True,
            email=user["email"],
            message="Your email has been verified successfully.",
        )

    async def resend_verification_email(self, email: str) -> dict[str, str]:
        user = await self.repo.get_user_by_email(email)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not registered.")
        if user.get("is_verified"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already verified.")

        token = str(uuid4())
        await self.repo.create_verification_token(user["email"], token)
        delivery = email_service.send_verification_email(user["email"], user["name"], token)
        return {
            "message": "Verification email resent successfully.",
            "email_delivery": delivery.get("delivery", {}),
        }

    async def delete_user(self, email: str, password: str) -> dict[str, bool]:
        user = await self.repo.get_user_by_email(email)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Email not registered.")
        if not verify_password(password, user["password_hash"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

        deleted = await self.repo.delete_user(email)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User could not be deleted.")
        return {"deleted": True}


auth_service = AuthService()
