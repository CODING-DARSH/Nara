import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from app.models.intelligence import UserHealthProfile, FoodGraph
from app.core.database import Base
from app.core.config import get_settings

settings = get_settings()
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata

# FIX: see services/ingestion/alembic/env.py for the full explanation.
# user-intelligence shares its Neon database with auth, ingestion,
# recommendation, and conversation. Without an isolated version_table,
# all services fight over the same "alembic_version" row.
#
# IMPORTANT one-time step if you already ran `alembic upgrade head` BEFORE
# this fix existed (you did — add_profile_signal_fields already applied
# and stamped the old shared "alembic_version" table): this new
# "alembic_version_user_intelligence" table starts empty, so Alembic will
# think nothing has been applied yet and will try to re-run
# add_profile_signal_fields, which will fail with "column already exists"
# since it really did already run. Before starting this service again,
# manually seed the new table once:
#
#   INSERT INTO alembic_version_user_intelligence (version_num)
#   VALUES ('add_profile_signal_fields');
#
# (run via Adminer's SQL command box, or psql against the Neon DB directly)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True,
        version_table="alembic_version_user_intelligence",
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection, target_metadata=target_metadata,
        version_table="alembic_version_user_intelligence",
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
