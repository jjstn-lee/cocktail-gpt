"""Recommender node: generates cocktail recommendations based on profile, preferences, and constraints."""

import json
from loguru import logger
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm
from src.state import AgentState, Cocktail
from src.prompts.recommender import RECOMMENDER_PROMPT, RECOMMENDER_SYSTEM_PROMPT
from src.tools.cocktail_kb import load_cocktails, apply_hard_filters, format_for_prompt


class RecommenderOutput(BaseModel):
    """Structured output from the recommender node."""

    recommendations: list[Cocktail]
    confidence_score: float
    rationale: str


async def recommender(state: AgentState) -> dict:
    """
    Generate cocktail recommendations based on user profile, preferences, constraints, and memory.

    Input: state["user_profile"], state["preferences"], state["constraints"],
           state.get("latest_message"), state.get("message_history"), state.get("feedback"), state.get("recommendation_history")
    Output: {"recommendations": list[Cocktail], "confidence_score": float, "rationale": str}
    """
    logger.debug("recommender: generating recommendations")

    user_profile = state.get("user_profile")
    preferences = state.get("preferences")
    constraints = state.get("constraints")
    latest_message = state.get("latest_message")
    message_history = state.get("message_history", [])
    feedback = state.get("feedback", [])
    recommendation_history = state.get("recommendation_history", [])

    profile_dict = user_profile.model_dump() if user_profile else {}
    preferences_dict = preferences.model_dump() if preferences else {}
    constraints_dict = constraints.model_dump() if constraints else {}

    # Build memory context from feedback and history
    memory_context = ""
    if feedback:
        liked = [fb.cocktail_name for fb in feedback if fb.rating == 5]
        disliked = [fb.cocktail_name for fb in feedback if fb.rating == 1]
        memory_context = "\n## Memory Context (Cross-Session):"
        if liked:
            memory_context += f"\nCocktails the user LIKED: {', '.join(liked)}"
        if disliked:
            memory_context += f"\nCocktails the user DISLIKED (avoid recommending): {', '.join(disliked)}"

    if recommendation_history:
        # Get cocktails from last 2 sessions
        recent_cocktails = []
        for session in recommendation_history[-2:]:
            recent_cocktails.extend(session.get("cocktails", []))
        if recent_cocktails:
            memory_context += f"\nRecently recommended cocktails (avoid unless user rated them up): {', '.join(recent_cocktails)}"

    all_cocktails = load_cocktails()
    filtered = apply_hard_filters(all_cocktails, constraints)

    spirits_in_kb = list(set(c.get("spirit_category", "mixed") for c in filtered))
    logger.info(
        "recommender: full KB with constraint filters only",
        extra={
            "total": len(all_cocktails),
            "filtered": len(filtered),
            "spirits_available": sorted(spirits_in_kb),
        },
    )
    print(f"[RECOMMENDER] Knowledgebase: {len(filtered)} cocktails available")
    if latest_message:
        print(f"[RECOMMENDER] User's Current Request: {latest_message}")
    print(f"[RECOMMENDER] Spirits in KB: {sorted(spirits_in_kb)}")

    kb_context = format_for_prompt(filtered)

    # Format preferences clearly with spirit types separated
    prefs_display = preferences_dict.copy()
    user_set_spirits = preferences_dict.get("preferred_spirits", [])
    genre_inferred_spirits = preferences_dict.get("genre_spirits", [])
    if user_set_spirits or genre_inferred_spirits:
        prefs_display["_spirits_note"] = f"preferred_spirits={user_set_spirits} (user-set), genre_spirits={genre_inferred_spirits} (inferred from music)"

    # Build conversation context from message history
    conversation_context = ""
    if message_history and len(message_history) > 1:
        conversation_context = "\n## Conversation History:"
        for msg in message_history[:-1]:
            if msg["role"] == "user":
                conversation_context += f"\nUser: {msg['content']}"
            elif msg["role"] == "assistant":
                conversation_context += f"\nAssistant: {msg['content']}"

    context = f"""User Profile: {json.dumps(profile_dict)}
Preferences: {json.dumps(prefs_display, indent=2)}
Constraints: {json.dumps(constraints_dict)}{memory_context}{conversation_context}

Knowledgebase (select from these only):
{kb_context}"""

    if latest_message:
        context += f"\n\nUser's Current Request: {latest_message}"

    llm = get_llm()
    llm_with_structured = llm.with_structured_output(RecommenderOutput)

    messages = [
        SystemMessage(content=RECOMMENDER_SYSTEM_PROMPT),
        HumanMessage(content=f"{RECOMMENDER_PROMPT}\n\n{context}"),
    ]

    response = await llm_with_structured.ainvoke(messages)
    logger.info(
        "recommender: recommendations generated",
        extra={
            "count": len(response.recommendations),
            "confidence_score": response.confidence_score,
        },
    )
    print(f"\n[RECOMMENDER] LLM Response:")
    print(f"[RECOMMENDER] Confidence: {response.confidence_score}")
    print(f"[RECOMMENDER] Rationale: {response.rationale}")
    print(f"[RECOMMENDER] Recommendations ({len(response.recommendations)}):")
    for i, cocktail in enumerate(response.recommendations, 1):
        print(f"  {i}. {cocktail.name}")
        print(f"     Ingredients: {cocktail.ingredients}")
        print(f"     Method: {cocktail.method}")
        print(f"     Flavors: {cocktail.flavor_notes}")
        print(f"     Why: {cocktail.why_this_works}")

    return {
        "recommendations": response.recommendations,
        "confidence_score": response.confidence_score,
        "rationale": response.rationale,
    }
