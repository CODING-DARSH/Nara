import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.dependencies.auth import CurrentUserId
from app.models.auth import RefreshToken, User, UserCredential
from app.schemas.auth import (
    GoogleCallbackRequest,
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserProfile,
)

router = APIRouter(prefix="/v1/auth", tags=["auth"])
settings = get_settings()


def _make_token_response(user: User, access_token: str, refresh_token_raw: str) -> TokenResponse:
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_raw,
        expires_in=settings.access_token_expire_minutes * 60,
        user_id=user.id,
        email=user.email,
        tier=user.tier,
    )


async def _create_refresh_token_record(
    db: AsyncSession,
    user_id: uuid.UUID,
    request: Optional[Request] = None,
) -> tuple[str, str]:
    """Creates DB refresh token record. Returns (raw_token, hash)."""
    raw, hashed = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

    device_hint = None
    ip_address = None
    if request:
        ua = request.headers.get("user-agent", "")
        device_hint = ua[:200] if ua else None
        ip_address = request.client.host if request.client else None

    token_record = RefreshToken(
        user_id=user_id,
        token_hash=hashed,
        device_hint=device_hint,
        ip_address=ip_address,
        expires_at=expires_at,
    )
    db.add(token_record)
    await db.flush()
    return raw, hashed


# ── REGISTER ──────────────────────────────────────────────────

@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check duplicate email
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    user = User(email=body.email.lower())
    db.add(user)
    await db.flush()  # get user.id

    creds = UserCredential(
        user_id=user.id,
        password_hash=hash_password(body.password),
    )
    db.add(creds)
    await db.commit()
    await db.refresh(user)

    return RegisterResponse(user_id=user.id, email=user.email)


# ── LOGIN ─────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    # Fetch user with credentials
    result = await db.execute(
        select(User)
        .where(User.email == body.email.lower(), User.deleted_at.is_(None))
        .options(selectinload(User.credentials))
    )
    user = result.scalar_one_or_none()

    if not user or not user.credentials or not user.credentials.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(body.password, user.credentials.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(str(user.id), user.email)
    refresh_raw, _ = await _create_refresh_token_record(db, user.id, request)
    await db.commit()

    return _make_token_response(user, access_token, refresh_raw)


# ── REFRESH ───────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    token_hash = hash_refresh_token(body.refresh_token)

    result = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .options(selectinload(RefreshToken.user))
    )
    token_record = result.scalar_one_or_none()

    if not token_record or not token_record.is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Rotate: revoke old token, issue new pair
    token_record.revoked_at = datetime.now(timezone.utc)
    await db.flush()

    user = token_record.user
    access_token = create_access_token(str(user.id), user.email)
    refresh_raw, _ = await _create_refresh_token_record(db, user.id, request)
    await db.commit()

    return _make_token_response(user, access_token, refresh_raw)


# ── LOGOUT ────────────────────────────────────────────────────

@router.post("/logout", response_model=MessageResponse)
async def logout(
    body: LogoutRequest,
    current_user_id: CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    token_hash = hash_refresh_token(body.refresh_token)

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.user_id == current_user_id,
        )
    )
    token_record = result.scalar_one_or_none()

    if token_record and token_record.revoked_at is None:
        token_record.revoked_at = datetime.now(timezone.utc)
        await db.commit()

    return MessageResponse(message="Logged out successfully")


# ── LOGOUT ALL DEVICES ────────────────────────────────────────

@router.post("/logout-all", response_model=MessageResponse)
async def logout_all_devices(
    current_user_id: CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Revoke all active refresh tokens for this user."""
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == current_user_id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    tokens = result.scalars().all()
    now = datetime.now(timezone.utc)
    for t in tokens:
        t.revoked_at = now

    await db.commit()
    return MessageResponse(message=f"Revoked {len(tokens)} active sessions")


# ── ME ────────────────────────────────────────────────────────

@router.get("/me", response_model=UserProfile)
async def get_me(
    current_user_id: CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).where(User.id == current_user_id, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserProfile(
        user_id=user.id,
        email=user.email,
        email_verified=user.email_verified,
        tier=user.tier,
        created_at=user.created_at,
    )


# ── GOOGLE OAUTH ──────────────────────────────────────────────

@router.get("/google/authorize")
async def google_authorize():
    """Redirect to Google OAuth consent screen."""
    if not settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    import secrets
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{query}")


@router.get("/google/callback", response_model=TokenResponse)
async def google_callback(
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not settings.google_client_id:
        raise HTTPException(status_code=501, detail="Google OAuth not configured")

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange Google auth code")

        token_data = token_resp.json()
        id_token = token_data.get("id_token")

        # Get user info from Google
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {token_data['access_token']}"},
        )
        userinfo = userinfo_resp.json()

    google_sub = userinfo["sub"]
    email = userinfo["email"].lower()

    # Find or create user
    result = await db.execute(
        select(UserCredential).where(UserCredential.google_sub == google_sub)
    )
    cred = result.scalar_one_or_none()

    if cred:
        result2 = await db.execute(select(User).where(User.id == cred.user_id))
        user = result2.scalar_one()
    else:
        # Check if email exists (link accounts)
        result2 = await db.execute(
            select(User).where(User.email == email).options(selectinload(User.credentials))
        )
        user = result2.scalar_one_or_none()

        if user:
            # Link Google to existing account
            if user.credentials:
                user.credentials.google_sub = google_sub
            else:
                db.add(UserCredential(user_id=user.id, google_sub=google_sub))
        else:
            # Brand new user via Google
            user = User(email=email, email_verified=True)
            db.add(user)
            await db.flush()
            db.add(UserCredential(user_id=user.id, google_sub=google_sub))

    await db.flush()
    access_token = create_access_token(str(user.id), user.email)
    refresh_raw, _ = await _create_refresh_token_record(db, user.id, request)
    await db.commit()

    return _make_token_response(user, access_token, refresh_raw)