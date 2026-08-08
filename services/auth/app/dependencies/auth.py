from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.core.redis import get_redis

bearer_scheme = HTTPBearer()


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> UUID:
    """
    Validates JWT access token.
    Returns user_id UUID if valid.
    Raises 401 if token is invalid, expired, or blacklisted.
    """
    token = credentials.credentials

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check token blacklist (tokens invalidated on logout)
    redis = await get_redis()
    blacklisted = await redis.get(f"blacklist:token:{token[:16]}")  # prefix check
    if blacklisted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UUID(payload["sub"])


# Shorthand type alias for use in route signatures
CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
