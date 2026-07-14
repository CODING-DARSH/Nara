"""
ML Inference Service — Database
Two connections:
  - NeonDB  : food_events, food_event_nutrition  (user data)
  - LocalDB : nutrition_kb, restaurants          (reference data)
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# ── Neon (user data) ──────────────────────────────────────────
neon_engine = create_async_engine(
    settings.neon_database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False,
)
NeonSession: async_sessionmaker[AsyncSession] = async_sessionmaker(
    neon_engine, expire_on_commit=False
)

# ── Local Postgres (nutrition KB) ─────────────────────────────
local_engine = create_async_engine(
    settings.local_database_url,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    echo=False,
)
LocalSession: async_sessionmaker[AsyncSession] = async_sessionmaker(
    local_engine, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def check_db_connections() -> dict:
    """Health check — verify both DBs are reachable."""
    from sqlalchemy import text
    results = {}
    try:
        async with NeonSession() as s:
            await s.execute(text("SELECT 1"))
        results["neon"] = "ok"
    except Exception as e:
        results["neon"] = f"error: {e}"

    try:
        async with LocalSession() as s:
            await s.execute(text("SELECT 1"))
        results["local"] = "ok"
    except Exception as e:
        results["local"] = f"error: {e}"

    return results