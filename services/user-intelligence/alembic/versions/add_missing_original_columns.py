"""add missing original columns to user_health_profiles

Discovered via services/user-intelligence/check_columns.py: the real DB
table was missing 7 columns that the SQLAlchemy model has declared since
before this round of work even started — cuisine_preferences,
budget_preferences, activity_level, age, weight_kg, height_cm, gender.
These predate everything in add_profile_signal_fields.py; they were never
migrated because alembic/versions/ was completely empty until that file
was added, and that migration only knew about the 6 fields it introduced,
not these 7 pre-existing gaps.

Caught because GET /v1/health-profile does a SELECT * style query against
the ORM model, which includes every declared column — so a previously
"working" PUT-then-discard flow never surfaced this, but a real round-trip
read does.

Revision ID: add_missing_original_columns
Revises: add_profile_signal_fields
Create Date: 2026-06-22

NOTE: if this conflicts with your real down_revision chain (e.g. you
already had migration history I haven't seen), adjust down_revision below.
This assumes add_profile_signal_fields is the only prior migration, which
matches what was confirmed running in your logs.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "add_missing_original_columns"
down_revision = "add_profile_signal_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_health_profiles",
        sa.Column("cuisine_preferences", JSONB(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "user_health_profiles",
        sa.Column("budget_preferences", JSONB(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "user_health_profiles",
        sa.Column("activity_level", sa.Text(), nullable=False, server_default="moderately_active"),
    )
    op.add_column("user_health_profiles", sa.Column("age", sa.Integer(), nullable=True))
    op.add_column("user_health_profiles", sa.Column("weight_kg", sa.Float(), nullable=True))
    op.add_column("user_health_profiles", sa.Column("height_cm", sa.Float(), nullable=True))
    op.add_column("user_health_profiles", sa.Column("gender", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_health_profiles", "gender")
    op.drop_column("user_health_profiles", "height_cm")
    op.drop_column("user_health_profiles", "weight_kg")
    op.drop_column("user_health_profiles", "age")
    op.drop_column("user_health_profiles", "activity_level")
    op.drop_column("user_health_profiles", "budget_preferences")
    op.drop_column("user_health_profiles", "cuisine_preferences")
