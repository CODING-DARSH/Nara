"""
NARA — Recommendation Service Database
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

neon_engine = create_async_engine(settings.neon_database_url, pool_size=5, pool_pre_ping=True)
local_engine = create_async_engine(settings.local_database_url, pool_size=5, pool_pre_ping=True)

NeonSession = async_sessionmaker(neon_engine, expire_on_commit=False)
LocalSession = async_sessionmaker(local_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def check_connections() -> dict:
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