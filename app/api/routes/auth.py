from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_current_user_id
from app.schemas import TokenResponse, UserLogin, UserRegister, VerificationStatus
from app.services.auth_service import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register_user(payload: UserRegister) -> dict[str, str | dict[str, str] | bool]:
    try:
        user = auth_service.register_user(payload)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "message": "User registered successfully. Please verify your email to log in.",
        "verification_required": True,
        "user": {"id": user["id"], "name": user["name"], "email": user["email"]},
    }


@router.post("/login", response_model=TokenResponse)
def login_user(payload: UserLogin) -> TokenResponse:
    return auth_service.login_user(payload)


@router.get("/verify-email", response_model=VerificationStatus)
def verify_email(token: str = Query(..., description="Verification token from the email link")) -> VerificationStatus:
    return auth_service.verify_email(token)


@router.post("/resend-verification")
def resend_verification(payload: dict[str, str]) -> dict[str, str]:
    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is required.")
    return auth_service.resend_verification_email(email)


@router.get("/me")
def get_me(user_id: str = Depends(get_current_user_id)) -> dict[str, str]:
    return {"user_id": user_id}
