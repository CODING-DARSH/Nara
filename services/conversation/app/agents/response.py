"""
NARA — Response Generator
Template-based now. Swap to Flan-T5 later by changing config.response_model.
"""
import logging
import random
from typing import Optional

log = logging.getLogger("nara.conversation.response")


def generate_response(
    intent: str,
    entities: dict,
    recommendations: list,
    food_graph: dict,
    nutrition_facts: dict,
    user_name: str = "",
) -> str:
    """
    Generate natural language response based on intent and data.
    Template-based for now — swap to Flan-T5 when fine-tuned.
    """
    greeting = f"Hey{' ' + user_name if user_name else ''}! "

    if intent == "get_recommendation":
        return _recommendation_response(recommendations, entities)
    elif intent == "log_meal":
        return _log_meal_response(entities)
    elif intent == "ask_nutrition":
        return _nutrition_response(entities, nutrition_facts)
    elif intent == "check_food_graph":
        return _food_graph_response(food_graph)
    elif intent == "set_preference":
        return _preference_response(entities)
    elif intent == "order_food":
        return _order_response(recommendations, entities)
    else:
        return _general_response()


def _recommendation_response(recommendations: list, entities: dict) -> str:
    if not recommendations:
        return "I couldn't find recommendations right now. Try again in a moment."

    occasion = entities.get("time_context", "")
    occasion_str = f"for {occasion}" if occasion else ""

    top = recommendations[:3]
    dish_lines = []
    for i, r in enumerate(top, 1):
        dish  = r.get("dish_name", "").replace("_", " ").title()
        cal   = r.get("nutrition", {}).get("calories")
        gi    = r.get("nutrition", {}).get("gi")
        comp  = "✓" if r.get("health_compliant") else "⚠"
        cal_str = f"{int(cal)} kcal" if cal else ""
        gi_str  = f"GI {int(gi)}" if gi else ""
        meta    = " · ".join(filter(None, [cal_str, gi_str]))
        dish_lines.append(f"{i}. {dish} {comp}" + (f" ({meta})" if meta else ""))

    header = f"Here are my top picks {occasion_str}:\n\n"
    body   = "\n".join(dish_lines)
    footer = "\n\nWant more options or details on any dish?"
    return header + body + footer


def _log_meal_response(entities: dict) -> str:
    dishes = entities.get("dishes", [])
    if dishes:
        dish_str = ", ".join(d.title() for d in dishes[:3])
        responses = [
            f"Logged {dish_str}! I'll update your food graph.",
            f"Got it — {dish_str} added to your meal log.",
            f"Noted! {dish_str} logged successfully.",
        ]
        return random.choice(responses)
    return "Got it! Meal logged. Tell me what you had so I can track nutrition."


def _nutrition_response(entities: dict, nutrition_facts: dict) -> str:
    dishes = entities.get("dishes", [])
    if not dishes or not nutrition_facts:
        return "Which dish would you like nutrition info for? Just name it!"

    dish  = dishes[0]
    facts = nutrition_facts.get(dish, {})
    if not facts:
        return f"I don't have detailed nutrition data for {dish.title()} yet."

    cal  = facts.get("calories_kcal", "?")
    prot = facts.get("protein_g", "?")
    carb = facts.get("carbs_g", "?")
    fat  = facts.get("fat_g", "?")
    gi   = facts.get("glycemic_index", "?")

    return (
        f"{dish.title()} (per serving):\n\n"
        f"🔥 Calories: {cal} kcal\n"
        f"💪 Protein: {prot}g\n"
        f"🌾 Carbs: {carb}g\n"
        f"🫙 Fat: {fat}g\n"
        f"📊 Glycemic Index: {gi}\n\n"
        f"Want to log this meal?"
    )


def _food_graph_response(food_graph: dict) -> str:
    if not food_graph:
        return "No meal history yet! Start logging meals and I'll build your food graph."

    total   = food_graph.get("total_meals_logged", 0)
    last_24 = food_graph.get("last_24h", {})
    cal_24  = last_24.get("calories_kcal", 0)
    top     = food_graph.get("top_dishes", [])
    top_str = ", ".join(d.get("dish", "").title() for d in top[:3]) if top else "none yet"
    affinity= food_graph.get("cuisine_affinity", {})
    fav_cuisine = max(affinity, key=affinity.get) if affinity else "mixed"

    return (
        f"Here's your food summary:\n\n"
        f"📋 Total meals logged: {total}\n"
        f"🔥 Calories today: {int(cal_24 or 0)} kcal\n"
        f"🍽 Top dishes: {top_str}\n"
        f"🌏 Favourite cuisine: {fav_cuisine.replace('_', ' ').title()}\n\n"
        f"Want detailed insights or recommendations based on this?"
    )


def _preference_response(entities: dict) -> str:
    return "Got it! I've noted your preferences. They'll be applied to future recommendations."


def _order_response(recommendations: list, entities: dict) -> str:
    if recommendations:
        dish = recommendations[0].get("dish_name", "").title()
        return f"I'd recommend ordering {dish}! Restaurant ordering integration is coming soon."
    return "Restaurant ordering is coming soon! For now, I can help you find what to eat."


def _general_response() -> str:
    responses = [
        "I'm here to help you eat better! Ask me for recommendations, nutrition info, or log a meal.",
        "Tell me what you're craving or where you are and I'll suggest something perfect.",
        "I can recommend dishes, track your nutrition, or answer food questions. What do you need?",
    ]
    return random.choice(responses)
