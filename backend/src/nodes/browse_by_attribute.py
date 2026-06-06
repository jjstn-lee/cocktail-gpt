"""Browse by attribute node: generates cocktails matching a user-specified attribute or ingredient."""

from loguru import logger
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm
from src.state import AgentState, Cocktail


class BrowseByAttributeOutput(BaseModel):
    """Output from browse_by_attribute node."""

    attribute_label: str  # e.g., "smoky", "gin-based", "refreshing"
    recommendations: list[Cocktail]


BROWSE_BY_ATTRIBUTE_SYSTEM_PROMPT = """You are a knowledgeable bartender helping a customer explore cocktails.
The supervisor has determined the user wants to browse cocktails by a specific attribute, ingredient, flavor, or style.
Your job is to generate cocktail recommendations that match their request.

IMPORTANT GUIDELINES:
1. Treat the user's request as an exploration query, not a personal recommendation
2. Draw from encyclopedic cocktail knowledge to suggest classic and well-known cocktails
3. If the user mentions hard constraints (allergies, max ABV), respect them for safety
4. Do NOT apply the user's personal preferences - this is about what's available by that attribute
5. Generate 3-5 cocktails that clearly match the requested attribute
6. Rank them by how well they exemplify the attribute

Examples of attribute queries:
- "show me something smoky" → Smoky Old Fashioned, Peaty Daiquiri, etc.
- "what can I make with gin?" → Gin-based cocktails of various styles
- "I want something refreshing" → Light, citrusy, cooling drinks
- "show me rum drinks" → Various rum cocktails

Return JSON with:
- attribute_label: A brief label for what they're browsing (e.g., "smoky cocktails", "gin-based", "refreshing")
- recommendations: List of 3-5 cocktails that match this attribute"""


async def browse_by_attribute(state: AgentState) -> dict:
    """
    Generate cocktail recommendations based on a user-specified attribute, flavor, ingredient, or style.
    Does NOT apply personal preferences; purely attribute-led exploration.

    Input: state["latest_message"], state.get("constraints") (for hard constraint context only)
    Output: {"recommendations": list[Cocktail], "browse_attribute": str}
    """
    logger.debug("browse_by_attribute: generating attribute-driven recommendations")

    latest_message = state.get("latest_message")
    constraints = state.get("constraints")

    if not latest_message:
        logger.warning("browse_by_attribute: no latest_message in state")
        return {
            "recommendations": [],
            "browse_attribute": "unknown",
        }

    # Build constraint context for safety filtering (hard constraints only)
    constraint_context = ""
    if constraints:
        if constraints.allergies:
            constraint_context += f"User allergies (avoid): {', '.join(constraints.allergies)}\n"
        if constraints.max_abv is not None:
            constraint_context += f"Max ABV: {constraints.max_abv}%\n"

    llm = get_llm()
    browse_llm = llm.with_structured_output(BrowseByAttributeOutput)

    context = f"""User request: {latest_message}
{constraint_context}

Generate cocktails that match this attribute/ingredient/flavor/style request.
Focus on the attribute, not personal preferences. Include classic and well-known cocktails."""

    messages = [
        SystemMessage(content=BROWSE_BY_ATTRIBUTE_SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]

    try:
        result = await browse_llm.ainvoke(messages)
        logger.info(
            "browse_by_attribute: generated recommendations",
            extra={
                "attribute": result.attribute_label,
                "count": len(result.recommendations),
            },
        )

        return {
            "recommendations": result.recommendations,
            "browse_attribute": result.attribute_label,
        }

    except Exception as e:
        logger.error("browse_by_attribute: error generating recommendations", extra={"error": str(e)})
        return {
            "recommendations": [],
            "browse_attribute": "unknown",
        }
