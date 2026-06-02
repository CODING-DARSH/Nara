from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


# ── Register ───────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class RegisterResponse(BaseModel):
    user_id: UUID
    email: str
    message: str = "Registration successful. Please verify your email."


# ── Login ──────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int        # seconds until access token expires
    user_id: UUID
    email: str
    tier: str


# ── Refresh ────────────────────────────────────────────────────

class RefreshRequest(BaseModel):
    refresh_token: str


# ── Logout ─────────────────────────────────────────────────────

class LogoutRequest(BaseModel):
    refresh_token: str


# ── User profile (returned from /me) ───────────────────────────

class UserProfile(BaseModel):
    user_id: UUID
    email: str
    email_verified: bool
    tier: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Google OAuth ───────────────────────────────────────────────

class GoogleCallbackRequest(BaseModel):
    code: str
    state: Optional[str] = None


# ── Generic responses ──────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str

class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None