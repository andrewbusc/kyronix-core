import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.db.models.password_reset_token import PasswordResetToken
from app.db.models.user import User
from app.schemas.auth import PasswordResetConfirm, PasswordResetRequest, PasswordResetResponse, Token
from app.schemas.user import UserRead

router = APIRouter()


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")
    access_token = create_access_token(subject=str(user.id), role=user.role)
    return Token(access_token=access_token)


@router.get("/me", response_model=UserRead)
def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/password-reset/request", response_model=PasswordResetResponse)
def request_password_reset(payload: PasswordResetRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    reset_token = None

    if user and user.is_active:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.password_reset_expire_minutes
        )
        reset_record = PasswordResetToken(
            token=token,
            user_id=user.id,
            expires_at=expires_at,
        )
        db.add(reset_record)
        db.commit()
        if settings.environment != "production":
            reset_token = token

    return PasswordResetResponse(
        message="If the account exists, a reset token has been generated.",
        reset_token=reset_token,
    )


@router.post("/password-reset/confirm", response_model=PasswordResetResponse)
def confirm_password_reset(payload: PasswordResetConfirm, db: Session = Depends(get_db)):
    record = (
        db.query(PasswordResetToken).filter(PasswordResetToken.token == payload.token).first()
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token"
        )
    if record.used_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token has already been used"
        )
    if record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token has expired"
        )

    user = db.get(User, record.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is inactive")

    try:
        user.hashed_password = get_password_hash(payload.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    record.used_at = datetime.now(timezone.utc)
    db.add(user)
    db.add(record)
    db.commit()

    return PasswordResetResponse(message="Password updated successfully.")
