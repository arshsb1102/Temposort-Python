from fastapi import HTTPException, status

from app.core.security import create_access_token, hash_password, verify_password
from app.db import store
from app.schemas import TokenResponse, UserLogin, UserRegister


class AuthService:
    def __init__(self) -> None:
        self.repo = store

    def register_user(self, payload: UserRegister) -> dict:
        user = self.repo.get_user_by_email(payload.email)
        if user is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered.")

        created_user = self.repo.create_user(
            name=payload.name,
            email=payload.email,
            password_hash=hash_password(payload.password),
        )
        return {
            "id": created_user["id"],
            "name": created_user["name"],
            "email": created_user["email"],
        }

    def login_user(self, payload: UserLogin) -> TokenResponse:
        user = self.repo.get_user_by_email(payload.email)
        if user is None or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

        token = create_access_token(str(user["id"]))
        return TokenResponse(access_token=token, token_type="bearer")


auth_service = AuthService()
