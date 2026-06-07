"""Manage restrictions node: generates cocktails respecting temporary session-only restrictions."""

from loguru import logger
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from src.llm import get_llm
from src.prompts.base import GENERAL_SYSTEM_PROMPT
from src.state import AgentState, Cocktail


class ManageRestrictionsOutput(BaseModel):
    """Output from manage_restrictions node."""

    extracted_restriction: str  # e.g., "no alcohol", "low ABV", "out of citrus"
    restriction_summary: str  # Friendly acknowledgment of the restriction
    recommendations: list[Cocktail]


MANAGE_RESTRICTIONS_SYSTEM_PROMPT = f"""{GENERAL_SYSTEM_PROMPT}

The supervisor has determined the user is setting a TEMPORARY, SESSION-ONLY restriction or limitation.
Your job is to acknowledge the restriction warmly and generate 3 cocktails that respect it.

IMPORTANT GUIDELINES:
1. This is a TEMPORARY restriction — it is NOT being saved to their profile
2. Acknowledge the restriction warmly (e.g., "Got it — keeping it alcohol-free tonight!")
3. Respect both the new restriction AND any stored hard constraints (allergies, max ABV)
4. Use their stored preferences as soft ranking signals, but don't skip good matches
5. Generate 3 cocktails that clearly respect the temporary restriction
6. Rank them by how well they fit within the restriction while matching stored preferences

Examples of restrictions:
- "I'm driving tonight, no alcohol" → Non-alcoholic cocktails
- "keep it low ABV for now" → Light ABV drinks (under 15%)
- "I'm out of citrus" → Cocktails without citrus ingredients
- "make it non-alcoholic" → Mocktails

Return JSON with:
- extracted_restriction: A brief label for the restriction (e.g., "alcohol-free", "low ABV", "no citrus")
- restriction_summary: A warm acknowledgment of the restriction
- recommendations: List of 3 cocktails that respect this restriction"""


async def manage_restrictions(state: AgentState) -> dict:
    """
    Generate cocktail recommendations respecting a temporary session-only restriction.
    Does NOT save the restriction to UserStore (it's session-only).

    Input: state["latest_message"], state.get("preferences"), state.get("constraints")
    Output: {"recommendations": list[Cocktail], "restriction_summary": str, "session_restriction": str}
    """
    logger.debug("manage_restrictions: generating restriction-aware recommendations")

    latest_message = state.get("latest_message")
    preferences = state.get("preferences")
    constraints = state.get("constraints")

    if not latest_message:
        logger.warning("manage_restrictions: no latest_message in state")
        return {
            "recommendations": [],
            "restriction_summary": "I couldn't understand your restriction. Could you clarify?",
            "session_restriction": "unknown",
        }

    # Build preference context for soft ranking (not filtering)
    pref_context = ""
    if preferences:
        if preferences.preferred_spirits:
            pref_context += f"Stored spirit preferences: {', '.join(preferences.preferred_spirits)}\n"
        if preferences.preferred_flavors:
            pref_context += f"Stored flavor preferences: {', '.join(preferences.preferred_flavors)}\n"
        if preferences.style_preferences:
            pref_context += f"Stored style preferences: {', '.join(preferences.style_preferences)}\n"

    # Build hard constraint context
    constraint_context = ""
    if constraints:
        if constraints.allergies:
            constraint_context += f"Stored allergies (hard avoid): {', '.join(constraints.allergies)}\n"
        if constraints.max_abv is not None:
            constraint_context += f"Stored max ABV: {constraints.max_abv}%\n"

    llm = get_llm()
    restrictions_llm = llm.with_structured_output(ManageRestrictionsOutput)

    context = f"""User restriction request: {latest_message}

{pref_context}

{constraint_context}

Generate cocktails that match this TEMPORARY restriction.
Use stored preferences as soft signals for ranking, but don't filter by them.
Respect both the new restriction AND stored hard constraints (allergies, max ABV).
Remember: this restriction is session-only and will NOT be saved."""

    # Build messages with conversation history
    message_history = state.get("message_history", [])
    messages = [SystemMessage(content=MANAGE_RESTRICTIONS_SYSTEM_PROMPT)]

    # Add message history (excluding current turn)
    if message_history and len(message_history) > 1:
        for msg in message_history[:-1]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=context))

    try:
        result = await restrictions_llm.ainvoke(messages)
        logger.info(
            "manage_restrictions: generated recommendations",
            extra={
                "restriction": result.extracted_restriction,
                "count": len(result.recommendations),
            },
        )

        return {
            "recommendations": result.recommendations,
            "restriction_summary": result.restriction_summary,
            "session_restriction": result.extracted_restriction,
        }

    except Exception as e:
        logger.error("manage_restrictions: error generating recommendations", extra={"error": str(e)})
        return {
            "recommendations": [],
            "restriction_summary": "Sorry, I had trouble processing that restriction.",
            "session_restriction": latest_message,
        }
