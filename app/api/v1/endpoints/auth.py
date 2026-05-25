from datetime import timedelta
from urllib.parse import quote

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.api.v1.dependencies.auth import get_current_active_user
from app.config.settings import settings
from app.core.audit import log_activity
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token, create_refresh_token, decode_token, hash_password,
    new_jti, new_random_token, now_utc, verify_password,
)
from app.database.database import get_db
from app.models import (
    EmailVerificationToken, PasswordResetToken, Patient, RefreshToken, User,
)
from app.schemas import (
    EmailVerifyConfirm, LoginRequest, PasswordResetConfirm, PasswordResetRequest,
    RefreshRequest, RegisterRequest, Token, UserOut,
)
from app.services import totp_service
from app.services.notification_service import (
    send_email_verification, send_password_reset,
)

router = APIRouter()

LOCKOUT_THRESHOLD = 5
LOCKOUT_MINUTES = 15


class LoginWith2FA(LoginRequest):
    totp_code: str | None = None


def _issue_tokens(db: Session, user: User, request: Request) -> Token:
    jti = new_jti()
    refresh, expires_at = create_refresh_token(user.id, jti)
    db.add(RefreshToken(
        user_id=user.id, jti=jti, expires_at=expires_at,
        user_agent=(request.headers.get("user-agent") if request else None),
        ip=(request.client.host if request and request.client else None),
    ))
    db.commit()
    return Token(
        access_token=create_access_token(user.id, user.role, getattr(user, "tenant_id", None)),
        refresh_token=refresh,
    )


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit("20/hour")
def register(request: Request, payload: RegisterRequest, background: BackgroundTasks,
             db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(
        email=payload.email, full_name=payload.full_name, phone=payload.phone,
        hashed_password=hash_password(payload.password), role="patient",
    )
    db.add(user); db.flush()
    db.add(Patient(user_id=user.id))

    token = new_random_token()
    db.add(EmailVerificationToken(
        user_id=user.id, token=token,
        expires_at=now_utc() + timedelta(days=2),
    ))
    db.commit(); db.refresh(user)

    verify_url = f"{settings.PUBLIC_FRONTEND_URL}/verify-email?token={quote(token)}"
    background.add_task(send_email_verification, user.email, user.full_name, verify_url, user.id)

    log_activity(db, user_id=user.id, action="user.register",
                 entity="user", entity_id=user.id, request=request)
    return _issue_tokens(db, user, request)


@router.post("/login", response_model=Token)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login(request: Request, payload: LoginWith2FA, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    if not user or user.deleted_at is not None:
        raise invalid
    if user.is_blocked:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User is blocked")
    if user.locked_until and user.locked_until > now_utc():
        raise HTTPException(status.HTTP_423_LOCKED, "Account temporarily locked")
    if not verify_password(payload.password, user.hashed_password):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= LOCKOUT_THRESHOLD:
            user.locked_until = now_utc() + timedelta(minutes=LOCKOUT_MINUTES)
            user.failed_login_attempts = 0
        db.commit()
        raise invalid
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Inactive user")

    if user.two_factor_enabled:
        if not payload.totp_code:
            raise HTTPException(401, "TOTP code required")
        if not totp_service.verify_code(db, user, payload.totp_code):
            raise HTTPException(401, "Invalid TOTP code")

    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    log_activity(db, user_id=user.id, action="user.login",
                 entity="user", entity_id=user.id, request=request)
    return _issue_tokens(db, user, request)


@router.post("/refresh", response_model=Token)
@limiter.limit("60/hour")
def refresh(request: Request, payload: RefreshRequest, db: Session = Depends(get_db)):
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise invalid
        jti = data.get("jti")
    except Exception:
        raise invalid
    rt = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if not rt or rt.revoked or rt.expires_at < now_utc():
        raise invalid
    user = db.query(User).get(rt.user_id)
    if not user or not user.is_active:
        raise invalid
    rt.revoked = True
    new_jti_val = new_jti()
    rt.replaced_by = new_jti_val
    new_refresh, expires_at = create_refresh_token(user.id, new_jti_val)
    db.add(RefreshToken(
        user_id=user.id, jti=new_jti_val, expires_at=expires_at,
        user_agent=(request.headers.get("user-agent") if request else None),
        ip=(request.client.host if request and request.client else None),
    ))
    db.commit()
    return Token(access_token=create_access_token(user.id, user.role, getattr(user, "tenant_id", None)), refresh_token=new_refresh)


@router.post("/logout", status_code=204)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        data = decode_token(payload.refresh_token)
        jti = data.get("jti")
    except Exception:
        return
    rt = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()
    if rt:
        rt.revoked = True; db.commit()


@router.post("/password/forgot", status_code=202)
@limiter.limit("5/hour")
def password_forgot(request: Request, payload: PasswordResetRequest,
                    background: BackgroundTasks, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if user:
        token = new_random_token()
        db.add(PasswordResetToken(
            user_id=user.id, token=token, expires_at=now_utc() + timedelta(hours=1),
        ))
        db.commit()
        url = f"{settings.PUBLIC_FRONTEND_URL}/reset-password?token={quote(token)}"
        background.add_task(send_password_reset, user.email, user.full_name, url, user.id)
    return {"detail": "If the email exists, a reset link was sent"}


@router.post("/password/reset", status_code=200)
def password_reset(payload: PasswordResetConfirm, request: Request, db: Session = Depends(get_db)):
    tok = db.query(PasswordResetToken).filter(PasswordResetToken.token == payload.token).first()
    if not tok or tok.used or tok.expires_at < now_utc():
        raise HTTPException(400, "Invalid or expired token")
    user = db.query(User).get(tok.user_id)
    if not user:
        raise HTTPException(400, "Invalid token")
    user.hashed_password = hash_password(payload.new_password)
    user.failed_login_attempts = 0
    user.locked_until = None
    tok.used = True
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False))\
        .update({"revoked": True})
    db.commit()
    log_activity(db, user_id=user.id, action="user.password_reset",
                 entity="user", entity_id=user.id, request=request)
    return {"detail": "Password updated"}


@router.post("/email/verify", status_code=200)
def email_verify(payload: EmailVerifyConfirm, db: Session = Depends(get_db)):
    tok = db.query(EmailVerificationToken).filter(EmailVerificationToken.token == payload.token).first()
    if not tok or tok.used or tok.expires_at < now_utc():
        raise HTTPException(400, "Invalid or expired token")
    user = db.query(User).get(tok.user_id)
    if not user:
        raise HTTPException(400, "Invalid token")
    user.email_verified = True
    tok.used = True; db.commit()
    return {"detail": "Email verified"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_active_user)):
    return user
