"""
Order Import Router
Handles bulk import of Zomato / Swiggy order history.
Each order becomes a food_event with enrichment_status=pending.
Kafka carries each one to the enrichment pipeline.
"""
import uuid
from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.kafka import emit
from app.models.food_event import FoodEvent
from app.schemas.ingestion import OrderImportRequest, ImportJobResponse
from app.routers.meals import CurrentUserId

router = APIRouter(prefix="/v1/meals", tags=["import"])


@router.post("/import", response_model=ImportJobResponse, status_code=status.HTTP_202_ACCEPTED)
async def import_order_history(
    body: OrderImportRequest,
    current_user_id: CurrentUserId,
    db: AsyncSession = Depends(get_db),
):
    """
    Bulk import order history from Zomato or Swiggy.
    Accepts up to 500 orders per request.
    Each order is saved as a food_event and queued for enrichment.
    Returns job_id immediately — processing happens in background.
    """
    job_id = str(uuid.uuid4())
    saved = 0

    for order in body.orders:
        # Build description from order items
        item_names = [
            f"{item.get('quantity', 1)}x {item.get('name', 'Unknown')}"
            for item in order.items
        ]
        description = f"Order from {order.restaurant_name}: {', '.join(item_names)}"

        # Ensure timezone aware
        occurred_at = order.ordered_at
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)

        event = FoodEvent(
            user_id=current_user_id,
            event_type="import",
            occurred_at=occurred_at,
            source_ref={
                "type": order.platform,
                "order_id": order.order_id,
                "restaurant_name": order.restaurant_name,
                "total_amount": order.total_amount,
            },
            raw_input={
                "description": description,
                "items": order.items,
                "platform": order.platform,
                "job_id": job_id,
            },
            meal_context={
                "occasion": _guess_occasion(occurred_at.hour),
                "location_type": "restaurant",
                "notes": f"Imported from {order.platform}",
            },
            enrichment_status="pending",
        )
        db.add(event)
        saved += 1

        # Batch commit every 50 events
        if saved % 50 == 0:
            await db.commit()

    await db.commit()

    # Emit all to Kafka for enrichment
    # Re-query events by job_id to get their IDs
    from sqlalchemy import select, cast
    from sqlalchemy.dialects.postgresql import JSONB

    result = await db.execute(
        select(FoodEvent).where(
            FoodEvent.user_id == current_user_id,
            FoodEvent.raw_input["job_id"].astext == job_id,
        )
    )
    events = result.scalars().all()

    for event in events:
        await emit(
            topic="food.events.raw",
            payload={
                "event_id": str(event.id),
                "user_id": str(current_user_id),
                "event_type": "import",
                "description": event.raw_input.get("description", ""),
                "job_id": job_id,
            },
            key=str(current_user_id),
        )

    return ImportJobResponse(
        job_id=job_id,
        total_orders=saved,
        message=f"Importing {saved} orders from your history. Nutritional analysis running in background.",
    )


def _guess_occasion(hour: int) -> str:
    """Guess meal occasion from hour of day."""
    if 5 <= hour <= 10:
        return "breakfast"
    elif 11 <= hour <= 15:
        return "lunch"
    elif 16 <= hour <= 17:
        return "snack"
    elif 18 <= hour <= 23:
        return "dinner"
    else:
        return "late_night"

