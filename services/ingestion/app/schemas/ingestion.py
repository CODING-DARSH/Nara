from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, field_validator


VALID_OCCASIONS = {"breakfast", "lunch", "dinner", "snack", "brunch", "late_night"}
VALID_LOCATION_TYPES = {"home", "office", "restaurant", "street_food", "cafe", "other"}


class MealContext(BaseModel):
    occasion: str = "lunch"
    location_type: str = "other"
    notes: str = ""

    @field_validator("occasion")
    @classmethod
    def validate_occasion(cls, v):
        if v not in VALID_OCCASIONS:
            raise ValueError(f"occasion must be one of: {VALID_OCCASIONS}")
        return v

    @field_validator("location_type")
    @classmethod
    def validate_location(cls, v):
        if v not in VALID_LOCATION_TYPES:
            raise ValueError(f"location_type must be one of: {VALID_LOCATION_TYPES}")
        return v


# ── Text Log ───────────────────────────────────────────────────

class TextLogRequest(BaseModel):
    """
    Log a meal by typing what you ate.
    e.g. "Had biryani and raita for lunch"
    """
    description: str
    occurred_at: Optional[datetime] = None   # defaults to now if not provided
    context: MealContext = MealContext()

    @field_validator("description")
    @classmethod
    def validate_description(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("Description too short")
        if len(v) > 500:
            raise ValueError("Description too long (max 500 chars)")
        return v.strip()


# ── Barcode Scan ───────────────────────────────────────────────

class BarcodeScanRequest(BaseModel):
    barcode: str
    occurred_at: Optional[datetime] = None
    context: MealContext = MealContext()


# ── Zomato / Swiggy Import ─────────────────────────────────────

class OrderImportItem(BaseModel):
    """Single order from Zomato/Swiggy order history."""
    order_id: str
    restaurant_name: str
    items: list[dict]            # [{"name": "Biryani", "quantity": 1, "price": 180}]
    ordered_at: datetime
    total_amount: int
    platform: str               # "zomato" or "swiggy"


class OrderImportRequest(BaseModel):
    orders: list[OrderImportItem]

    @field_validator("orders")
    @classmethod
    def validate_orders(cls, v):
        if len(v) > 500:
            raise ValueError("Cannot import more than 500 orders at once")
        return v


# ── Responses ──────────────────────────────────────────────────

class FoodEventResponse(BaseModel):
    event_id: UUID
    status: str
    message: str
    occurred_at: datetime


class EventStatusResponse(BaseModel):
    event_id: UUID
    enrichment_status: str
    enriched_at: Optional[datetime]
    message: str


class ImportJobResponse(BaseModel):
    job_id: str
    total_orders: int
    message: str


class FoodEventListResponse(BaseModel):
    events: list[dict]
    total: int
    page: int
    page_size: int
