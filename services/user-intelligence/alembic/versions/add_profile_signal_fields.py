"""add profile signal fields

Adds 6 columns to user_health_profiles (income_tier, region, occupation,
living_situation, stress_level, is_wfh) and 1 column to food_graphs
(total_meals_pending). These replace constants that were previously
hardcoded in recommendation/app/routers/recommend.py (_build_user,
_build_context) for every user, every request.

Revision ID: add_profile_signal_fields
Revises:
Create Date: 2026-06-21

NOTE: alembic/versions/ was empty (only a .gitkeep) when this was written —
no prior revision files existed in what I read. If your real database
already has migration history not included in that, set down_revision
below to your actual current head revision before running this, or
`alembic upgrade head` may fail or try to recreate tables that already
exist.

If you'd rather have Alembic generate this file itself against your real
migration history, run:
    alembic revision -m "add profile signal fields"
and paste the upgrade()/downgrade() bodies below into the generated file
instead of using this one directly.
"""
from alembic import op
import sqlalchemy as sa

revision = "add_profile_signal_fields"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_health_profiles", sa.Column("income_tier", sa.Text(), nullable=True))
    op.add_column("user_health_profiles", sa.Column("region", sa.Text(), nullable=True))
    op.add_column("user_health_profiles", sa.Column("occupation", sa.Text(), nullable=True))
    op.add_column("user_health_profiles", sa.Column("living_situation", sa.Text(), nullable=True))
    op.add_column("user_health_profiles", sa.Column("stress_level", sa.Text(), nullable=True))
    op.add_column("user_health_profiles", sa.Column("is_wfh", sa.Boolean(), nullable=True))

    op.add_column(
        "food_graphs",
        sa.Column("total_meals_pending", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("food_graphs", "total_meals_pending")

    op.drop_column("user_health_profiles", "is_wfh")
    op.drop_column("user_health_profiles", "stress_level")
    op.drop_column("user_health_profiles", "living_situation")
    op.drop_column("user_health_profiles", "occupation")
    op.drop_column("user_health_profiles", "region")
    op.drop_column("user_health_profiles", "income_tier")