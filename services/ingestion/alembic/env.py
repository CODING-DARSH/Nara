import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from app.models.food_event import FoodEvent
from app.core.database import Base
from app.core.config import get_settings

settings = get_settings()
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata

# FIX: ingestion shares its Neon database with auth, user-intelligence,
# recommendation, and conversation (all point at the same
# DATABASE_URL/NEON_DATABASE_URL per docker-compose.yml). Alembic's default
# version-tracking table name is "alembic_version" for every service, so
# without an explicit version_table, two services with independent
# migration histories collide on the same row — whichever applies a
# migration last "wins" and stamps a revision ID the OTHER service's
# versions/ folder has never heard of. That's exactly what happened here:
# user-intelligence applied add_profile_signal_fields, stamped the shared
# alembic_version row with that ID, then ingestion started up and failed
# because its own versions/ folder has no such revision.
# Giving each service its own version_table name fixes this permanently —
# every service that runs its own migrations against this shared DB needs
# the same treatment (see auth/alembic/env.py, user-intelligence/alembic/env.py).


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True,
        version_table="alembic_version_ingestion",
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection, target_metadata=target_metadata,
        version_table="alembic_version_ingestion",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()