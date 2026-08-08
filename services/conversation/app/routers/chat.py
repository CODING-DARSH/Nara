"""
NARA — Chat Router
"""
import logging
from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional
import httpx

from app.core.config import get_settings
from app.agents.intent import classify_intent
from app.agents.ner import extract_entities
from app.agents.response import generate_response

log      = logging.getLogger("nara.conversation.chat")
router   = APIRouter(prefix="/v1/chat", tags=["chat"])
settings = get_settings()
bearer   = HTTPBearer()


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    from jose import jwt, JWTError
    from fastapi import HTTPException
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return {"user_id": payload.get("sub"), "email": payload.get("email"),
                "token": credentials.credentials}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/")
async def chat(
    body: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Main chat endpoint.
    Takes natural language message → returns response + structured data.
    """
    message = body.message.strip()
    token   = current_user["token"]
    user_id = current_user["user_id"]

    # Step 1: Classify intent
    intent_result = classify_intent(message)
    intent        = intent_result["intent"]

    # Step 2: Extract entities
    entities = extract_entities(message)

    # Step 3: Fetch data based on intent
    food_graph      = {}
    recommendations = []
    nutrition_facts = {}

    async with httpx.AsyncClient(timeout=5.0) as client:
        headers = {"Authorization": f"Bearer {token}"}

        # Always fetch food graph for context
        try:
            resp = await client.get(
                f"{settings.user_intelligence_url}/v1/food-graph",
                headers=headers,
            )
            if resp.status_code == 200:
                food_graph = resp.json()
        except Exception:
            pass

        # Fetch recommendations if needed
        if intent in ("get_recommendation", "order_food"):
            try:
                params = {}
                if entities.get("time_context"):
                    params["occasion"] = entities["time_context"]
                resp = await client.get(
                    f"{settings.recommendation_url}/v1/recommend/",
                    headers=headers,
                    params=params,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    recommendations = data.get("recommendations", [])
            except Exception as e:
                log.warning(f"Recommendation fetch failed: {e}")

        # Fetch nutrition if asked
        if intent == "ask_nutrition" and entities.get("dishes"):
            dish = entities["dishes"][0]
            try:
                resp = await client.get(
                    f"{settings.ml_inference_url}/debug/lookup",
                    json={"dish": dish},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("found"):
                        nutrition_facts[dish] = data.get("nutrition", {})
            except Exception:
                pass

    # Step 4: Generate response
    response_text = generate_response(
        intent=intent,
        entities=entities,
        recommendations=recommendations,
        food_graph=food_graph,
        nutrition_facts=nutrition_facts,
    )

    return {
        "message":        response_text,
        "intent":         intent,
        "intent_confidence": intent_result["confidence"],
        "intent_method":  intent_result["method"],
        "entities":       entities,
        "recommendations":recommendations[:3] if recommendations else [],
        "food_graph_summary": {
            "total_meals":   food_graph.get("total_meals_logged", 0),
            "calories_today":food_graph.get("last_24h", {}).get("calories_kcal", 0),
        } if food_graph else {},
    }


@router.get("/history")
async def chat_history(current_user: dict = Depends(get_current_user)):
    """Placeholder — conversation history stored in future sprint."""
    return {"history": [], "message": "Chat history coming soon"}
