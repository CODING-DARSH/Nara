import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.kafka import emit
from app.core.security import decode_access_token
from app.core.storage import upload_photo, generate_presigned_url
from app.models.food_event import FoodEvent
from app.schemas.ingestion import (
    TextLogRequest,
    BarcodeScanRequest,
    FoodEventResponse,
    EventStatusResponse,
    FoodEventListResponse,
    MealContext,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Annotated

settings = get_settings()
router = APIRouter(prefix="/v1/meals", tags=["meals"])
bearer_scheme = HTTPBearer()


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
) -> uuid.UUID:
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return uuid.UUID(payload["sub"])


CurrentUserId = Annotated[uuid.UUID, Depends(get_current_user_id)]


# ── TEXT LOG ──────────────────────────────────────────────────

@router.post("/log", response_model=FoodEventResponse, status_code=status.HTTP_202_ACCEPTED)
async def log_meal_text(
    body: TextLogRequest,
    current_user_id: CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """
    Log a meal by text description.
    Returns 202 immediately. Enrichment (NER + nutrition lookup) happens async.
    """
    occurred_at = body.occurred_at or datetime.now(timezone.utc)

    event = FoodEvent(
        user_id=current_user_id,
        event_type="manual_log",
        occurred_at=occurred_at,
        raw_input={
            "description": body.description,
            "input_type": "text",
        },
        meal_context=body.context.model_dump(),
        enrichment_status="pending",
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    # Emit to Kafka for async enrichment
    await emit(
        topic="food.events.raw",
        payload={
            "event_id": str(event.id),
            "user_id": str(current_user_id),
            "event_type": "manual_log",
            "description": body.description,
        },
        key=str(current_user_id),  # partition by user_id
    )

    return FoodEventResponse(
        event_id=event.id,
        status="pending",
        message="Meal logged. Analysing nutritional content...",
        occurred_at=occurred_at,
    )


# ── PHOTO LOG ─────────────────────────────────────────────────

@router.post("/photo", response_model=FoodEventResponse, status_code=status.HTTP_202_ACCEPTED)
async def log_meal_photo(
    current_user_id: CurrentUserId,
    photo: UploadFile = File(...),
    occasion: str = Form(default="lunch"),
    location_type: str = Form(default="other"),
    notes: str = Form(default=""),
    occurred_at_str: Optional[str] = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Log a meal by uploading a photo.
    Photo → S3 → Kafka → Vision model → Nutrition lookup → Food graph update.
    Returns 202 immediately.
    """
    # Validate file
    if photo.content_type not in settings.allowed_photo_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {settings.allowed_photo_types}"
        )

    file_bytes = await photo.read()
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > settings.max_photo_size_mb:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.max_photo_size_mb}MB"
        )

    # Parse occurred_at
    if occurred_at_str:
        try:
            occurred_at = datetime.fromisoformat(occurred_at_str)
        except ValueError:
            occurred_at = datetime.now(timezone.utc)
    else:
        occurred_at = datetime.now(timezone.utc)

    # Generate unique S3 key
    event_id = uuid.uuid4()
    ext = photo.filename.rsplit(".", 1)[-1] if "." in (photo.filename or "") else "jpg"
    s3_key = f"{current_user_id}/{event_id}.{ext}"

    # Upload to MinIO
    try:
        upload_photo(file_bytes, s3_key, photo.content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Photo upload failed: {str(e)}")

    # Create event record
    event = FoodEvent(
        id=event_id,
        user_id=current_user_id,
        event_type="photo_log",
        occurred_at=occurred_at,
        raw_input={
            "s3_key": s3_key,
            "original_filename": photo.filename,
            "content_type": photo.content_type,
            "size_bytes": len(file_bytes),
        },
        meal_context={
            "occasion": occasion,
            "location_type": location_type,
            "notes": notes,
        },
        enrichment_status="pending",
    )
    db.add(event)
    await db.commit()

    # Emit to Kafka for vision inference
    await emit(
        topic="photo.upload.pending",
        payload={
            "event_id": str(event_id),
            "user_id": str(current_user_id),
            "s3_key": s3_key,
        },
        key=str(current_user_id),
    )

    return FoodEventResponse(
        event_id=event_id,
        status="pending",
        message="Photo uploaded. Identifying dish and analysing nutrition...",
        occurred_at=occurred_at,
    )


# ── BARCODE SCAN ──────────────────────────────────────────────

@router.post("/barcode", response_model=FoodEventResponse, status_code=status.HTTP_202_ACCEPTED)
async def log_meal_barcode(
    body: BarcodeScanRequest,
    current_user_id: CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """
    Log a packaged food item by barcode.
    Looks up OpenFoodFacts / USDA database for exact nutrition.
    """
    occurred_at = body.occurred_at or datetime.now(timezone.utc)

    event = FoodEvent(
        user_id=current_user_id,
        event_type="barcode_scan",
        occurred_at=occurred_at,
        raw_input={
            "barcode": body.barcode,
            "input_type": "barcode",
        },
        meal_context=body.context.model_dump(),
        enrichment_status="pending",
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)

    await emit(
        topic="food.events.raw",
        payload={
            "event_id": str(event.id),
            "user_id": str(current_user_id),
            "event_type": "barcode_scan",
            "barcode": body.barcode,
        },
        key=str(current_user_id),
    )

    return FoodEventResponse(
        event_id=event.id,
        status="pending",
        message="Barcode received. Looking up nutritional information...",
        occurred_at=occurred_at,
    )


# ── EVENT STATUS ──────────────────────────────────────────────

@router.get("/{event_id}/status", response_model=EventStatusResponse)
async def get_event_status(
    event_id: uuid.UUID,
    current_user_id: CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """Poll enrichment status of a food event."""
    result = await db.execute(
        select(FoodEvent).where(
            FoodEvent.id == event_id,
            FoodEvent.user_id == current_user_id,
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    messages = {
        "pending": "In queue for analysis...",
        "processing": "Analysing nutritional content...",
        "done": "Analysis complete.",
        "failed": "Analysis failed. Please try logging again.",
    }

    return EventStatusResponse(
        event_id=event.id,
        enrichment_status=event.enrichment_status,
        enriched_at=event.enriched_at,
        message=messages.get(event.enrichment_status, "Unknown status"),
    )


# ── MEAL HISTORY ──────────────────────────────────────────────

@router.get("/history", response_model=FoodEventListResponse)
async def get_meal_history(
    current_user_id: CurrentUserId,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """Get paginated meal history for the current user."""
    if page_size > 100:
        page_size = 100

    offset = (page - 1) * page_size

    # Total count
    count_result = await db.execute(
        select(func.count(FoodEvent.id)).where(FoodEvent.user_id == current_user_id)
    )
    total = count_result.scalar()

    # Fetch page
    result = await db.execute(
        select(FoodEvent)
        .where(FoodEvent.user_id == current_user_id)
        .order_by(FoodEvent.occurred_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    events = result.scalars().all()

    return FoodEventListResponse(
        events=[
            {
                "event_id": str(e.id),
                "event_type": e.event_type,
                "occurred_at": e.occurred_at.isoformat(),
                "enrichment_status": e.enrichment_status,
                "meal_context": e.meal_context,
                "description": e.raw_input.get("description", ""),
            }
            for e in events
        ],
        total=total,
        page=page,
        page_size=page_size,
    )
