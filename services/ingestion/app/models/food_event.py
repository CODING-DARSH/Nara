import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class FoodEvent(Base):
    __tablename__ = "food_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)

    # order / photo_log / manual_log / import / barcode_scan
    event_type: Mapped[str] = mapped_column(Text, nullable=False)

    # Actual time the meal was eaten (not when logged)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Source reference e.g. {"type": "swiggy", "order_id": "SW123"}
    source_ref: Mapped[dict] = mapped_column(JSONB, nullable=True)

    # Original raw data before enrichment
    raw_input: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # Meal context e.g. {"occasion": "dinner", "location_type": "office", "notes": ""}
    meal_context: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)

    # pending / processing / done / failed
    enrichment_status: Mapped[str] = mapped_column(Text, default="pending", nullable=False)
    enriched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
