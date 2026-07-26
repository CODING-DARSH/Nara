"""
NARA — Orders Router

Cart + checkout, backed by the orders/order_items tables in NEON (see
app/migrations/003_orders.sql for the full reasoning on why Neon and why
restaurant_id/dish_name are plain fields rather than DB-enforced FKs).

No payment processing anywhere in this file — direct order/checkout only,
per explicit instruction.

Lifecycle: ONE order row per cart, start to finish. Adding items creates
or updates a single status='cart' row; checkout transitions that SAME row
to status='placed'. There is never a second row for the same cart-to-order
flow — see get_or_create_cart() / checkout() below.

Every add-to-cart and checkout also feeds the existing feedback-loop
plumbing (core/redis.record_dish_interaction + Kafka
publish_feedback_event) — an order is the strongest possible reorder
signal, stronger than a bare "click" on a recommendation card, so it
should move future rankings at least as much.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from app.core.database import NeonSession, LocalSession
from app.core.security import get_current_user
from app.core.redis import record_dish_interaction, invalidate_recs_cache
from app.core.kafka import publish_feedback_event
from app.core.events import log_event

log    = logging.getLogger("nara.recommendation.orders")
router = APIRouter(prefix="/v1/orders", tags=["orders"])


class AddCartItemIn(BaseModel):
    restaurant_id: str
    dish_name:     str
    cuisine_type:  Optional[str] = None
    quantity:      int = 1
    session_id:    Optional[str] = None  # ties this click back to the
                                          # impression batch it came from —
                                          # see recommend.py's `/` and
                                          # `/with-restaurants` responses


async def _validate_dish_on_menu(restaurant_id: str, dish_name: str) -> bool:
    """
    Application-layer integrity check standing in for the FK Postgres can't
    enforce across databases — confirms the dish is actually on that
    restaurant's real menu (restaurant_menu_items, local Postgres) before
    any order row references it.
    """
    async with LocalSession() as db:
        result = await db.execute(
            text("""
                SELECT 1 FROM restaurant_menu_items
                WHERE restaurant_id = :restaurant_id AND dish_name = :dish_name
                LIMIT 1
            """),
            {"restaurant_id": restaurant_id, "dish_name": dish_name},
        )
        return result.first() is not None


async def _get_open_cart(db, user_id: str):
    result = await db.execute(
        text("SELECT * FROM orders WHERE user_id = :user_id AND status = 'cart' LIMIT 1"),
        {"user_id": user_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def _get_cart_items(db, order_id: str) -> list:
    result = await db.execute(
        text("SELECT dish_name, cuisine_type, quantity FROM order_items WHERE order_id = :order_id ORDER BY created_at"),
        {"order_id": order_id},
    )
    return [dict(r) for r in result.mappings().all()]


@router.get("/cart")
async def get_cart(current_user: dict = Depends(get_current_user)):
    """Fetch the current open cart (if any) — lets the frontend restore
    cart state after navigation/reload instead of holding it only in
    memory."""
    user_id = current_user["user_id"]
    async with NeonSession() as db:
        cart = await _get_open_cart(db, user_id)
        if not cart:
            return {"cart": None, "items": []}
        items = await _get_cart_items(db, cart["id"])
        return {"cart": cart, "items": items}


@router.post("/cart/items")
async def add_cart_item(body: AddCartItemIn, current_user: dict = Depends(get_current_user)):
    """
    Adds a dish to the user's cart, creating the cart order row if none
    exists yet. If the user already has an open cart for a DIFFERENT
    restaurant, this rejects with 409 rather than silently mixing
    restaurants into one order or silently discarding the existing cart —
    the frontend decides whether to clear the old cart and retry.
    """
    user_id = current_user["user_id"]

    if not await _validate_dish_on_menu(body.restaurant_id, body.dish_name):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail=f"'{body.dish_name}' is not on that restaurant's menu")

    async with NeonSession() as db:
        cart = await _get_open_cart(db, user_id)

        if cart and cart["restaurant_id"] != body.restaurant_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "You have an open cart for a different restaurant. "
                               "Clear it before ordering from a new one.",
                    "existing_cart_id":        str(cart["id"]),
                    "existing_restaurant_id":  str(cart["restaurant_id"]),
                },
            )

        if not cart:
            result = await db.execute(
                text("""
                    INSERT INTO orders (user_id, restaurant_id, status)
                    VALUES (:user_id, :restaurant_id, 'cart')
                    RETURNING *
                """),
                {"user_id": user_id, "restaurant_id": body.restaurant_id},
            )
            cart = dict(result.mappings().first())

        await db.execute(
            text("""
                INSERT INTO order_items (order_id, dish_name, cuisine_type, quantity)
                VALUES (:order_id, :dish_name, :cuisine_type, :quantity)
                ON CONFLICT (order_id, dish_name)
                DO UPDATE SET quantity = order_items.quantity + EXCLUDED.quantity
            """),
            {
                "order_id":     cart["id"],
                "dish_name":    body.dish_name,
                "cuisine_type": body.cuisine_type,
                "quantity":     body.quantity,
            },
        )
        await db.execute(
            text("UPDATE orders SET updated_at = now() WHERE id = :id"),
            {"id": cart["id"]},
        )
        await db.commit()

        items = await _get_cart_items(db, cart["id"])

    # Adding to cart is itself real interest signal — cheaper than a full
    # order but stronger than just viewing a card. Reuses the same
    # click-weight path as the recommendation-card /feedback endpoint.
    await record_dish_interaction(user_id, body.dish_name, "click")
    await publish_feedback_event({
        "event_type":   "feedback",
        "user_id":      user_id,
        "dish_name":    body.dish_name,
        "cuisine_type": body.cuisine_type,
        "action":       "click",
        "occasion":     None,
        "rank":         None,
    })
    await log_event(
        user_id=user_id,
        event_type="click",
        dish_name=body.dish_name,
        cuisine_type=body.cuisine_type,
        restaurant_id=body.restaurant_id,
        session_id=body.session_id,
    )

    return {"cart": cart, "items": items}


@router.delete("/cart/items/{dish_name}")
async def remove_cart_item(dish_name: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    async with NeonSession() as db:
        cart = await _get_open_cart(db, user_id)
        if not cart:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No open cart")

        await db.execute(
            text("DELETE FROM order_items WHERE order_id = :order_id AND dish_name = :dish_name"),
            {"order_id": cart["id"], "dish_name": dish_name},
        )
        items = await _get_cart_items(db, cart["id"])

        if not items:
            # Empty cart is just clutter — remove the shell order row too
            # rather than leaving a dangling empty status='cart' row that
            # would otherwise block starting a cart at a different
            # restaurant next time.
            await db.execute(text("DELETE FROM orders WHERE id = :id"), {"id": cart["id"]})
            await db.commit()
            return {"cart": None, "items": []}

        await db.execute(text("UPDATE orders SET updated_at = now() WHERE id = :id"), {"id": cart["id"]})
        await db.commit()
        return {"cart": cart, "items": items}


@router.delete("/cart")
async def clear_cart(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    async with NeonSession() as db:
        cart = await _get_open_cart(db, user_id)
        if cart:
            await db.execute(text("DELETE FROM orders WHERE id = :id"), {"id": cart["id"]})
            await db.commit()
    return {"cart": None, "items": []}


@router.post("/checkout")
async def checkout(current_user: dict = Depends(get_current_user)):
    """
    Transitions the user's open cart to status='placed' — the SAME order
    row throughout, never a second row. No payment step: this just
    finalizes the order.
    """
    user_id = current_user["user_id"]
    async with NeonSession() as db:
        cart = await _get_open_cart(db, user_id)
        if not cart:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No open cart to check out")

        items = await _get_cart_items(db, cart["id"])
        if not items:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

        result = await db.execute(
            text("""
                UPDATE orders
                SET status = 'placed', placed_at = now(), updated_at = now()
                WHERE id = :id
                RETURNING *
            """),
            {"id": cart["id"]},
        )
        placed_order = dict(result.mappings().first())
        await db.commit()

    # An actual order is the strongest reorder signal there is — stronger
    # than a bare recommendation-card click, matching
    # core/redis.DISH_INTERACTION_WEIGHTS["order"] = 1.5 vs "click" = 0.5.
    for item in items:
        await record_dish_interaction(user_id, item["dish_name"], "order")
        await publish_feedback_event({
            "event_type":   "feedback",
            "user_id":      user_id,
            "dish_name":    item["dish_name"],
            "cuisine_type": item["cuisine_type"],
            "action":       "order",
            "occasion":     None,
            "rank":         None,
        })
        await log_event(
            user_id=user_id,
            event_type="order",
            dish_name=item["dish_name"],
            cuisine_type=item["cuisine_type"],
            restaurant_id=str(placed_order["restaurant_id"]),
        )

    await invalidate_recs_cache(user_id)

    return {"order": placed_order, "items": items}


@router.get("/history")
async def order_history(current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    async with NeonSession() as db:
        result = await db.execute(
            text("""
                SELECT * FROM orders
                WHERE user_id = :user_id AND status = 'placed'
                ORDER BY placed_at DESC
                LIMIT 50
            """),
            {"user_id": user_id},
        )
        orders = [dict(r) for r in result.mappings().all()]
        for o in orders:
            items = await _get_cart_items(db, o["id"])
            o["items"] = items
        return {"orders": orders}