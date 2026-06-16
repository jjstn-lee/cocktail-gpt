"""Browse by attribute node: picks cocktails from the KB matching a user-specified attribute."""

from loguru import logger
from pydantic import BaseModel, ConfigDict
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from src.llm import get_llm
from src.prompts.base import GENERAL_SYSTEM_PROMPT
from src.state import AgentState, Cocktail
from src.tools.cocktail_kb import (
    apply_hard_filters,
    filter_by_attribute,
    format_for_prompt,
    load_cocktails,
)


class BrowseByAttributeOutput(BaseModel):
    """Output from browse_by_attribute node."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
    attribute_label: str
    recommendations: list[Cocktail]


BROWSE_BY_ATTRIBUTE_SYSTEM_PROMPT = f"""{GENERAL_SYSTEM_PROMPT}

The user wants to browse cocktails by an attribute, ingredient, flavor, or style.
You will be given a CANDIDATE LIST of cocktails drawn from the curated knowledgebase.

RULES:
1. Pick exactly 3 cocktails from the candidate list. Do not invent cocktails or use cocktails
   not in the candidate list — names must match the candidate list exactly.
2. If fewer than 3 candidates are present, return as many as are available.
3. Rank by how clearly each cocktail exemplifies the requested attribute.
4. Do NOT apply the user's personal preferences — this is an attribute query, not a recommendation.
   Hard safety constraints (allergies, max ABV) have already been applied to the candidate list.
5. Extract a clear `attribute_label` from the user's request (e.g., "smoky", "gin-based",
   "refreshing"). Never return "unknown" — pick the most defensible label.

Return JSON with:
- attribute_label: A brief, meaningful label for what they're browsing
- recommendations: Exactly 3 cocktails (or fewer if candidate list is shorter) from the candidate list"""


async def browse_by_attribute(state: AgentState) -> dict:
    """
    Pick KB-grounded cocktails matching the user's attribute query.

    Input: state["latest_message"], state.get("constraints"), state.get("message_history")
    Output: {"recommendations": list[Cocktail], "browse_attribute": str}
    """
    logger.debug("browse_by_attribute: KB-grounded attribute pick")

    latest_message = state.get("latest_message")
    constraints = state.get("constraints")

    if not latest_message:
        logger.warning("browse_by_attribute: no latest_message in state")
        return {"recommendations": [], "browse_attribute": "unknown"}

    all_cocktails = load_cocktails()

    candidates = filter_by_attribute(all_cocktails, latest_message, constraints)
    if not candidates:
        candidates = apply_hard_filters(all_cocktails, constraints)

    candidate_names = {c.get("name", "") for c in candidates}
    kb_block = format_for_prompt(candidates)

    constraint_context = ""
    if constraints:
        if constraints.allergies:
            constraint_context += f"User allergies (avoid): {', '.join(constraints.allergies)}\n"
        if constraints.max_abv is not None:
            constraint_context += f"Max ABV: {constraints.max_abv}%\n"

    context = f"""User request: {latest_message}
{constraint_context}
CANDIDATES (pick from these only):
{kb_block}"""

    message_history = state.get("message_history", [])
    messages: list = [SystemMessage(content=BROWSE_BY_ATTRIBUTE_SYSTEM_PROMPT)]
    if message_history and len(message_history) > 1:
        for msg in message_history[:-1]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))
    messages.append(HumanMessage(content=context))

    llm = get_llm()
    browse_llm = llm.with_structured_output(BrowseByAttributeOutput)

    try:
        result = await browse_llm.ainvoke(messages)

        if isinstance(result, BrowseByAttributeOutput):
            attribute_label = result.attribute_label
            recommendations = result.recommendations
        elif isinstance(result, dict):
            attribute_label = result.get("attribute_label", "unknown")
            recommendations = result.get("recommendations", [])
        else:
            logger.warning(f"browse_by_attribute: unexpected result type {type(result)}")
            return {"recommendations": [], "browse_attribute": "unknown"}

        valid: list[Cocktail] = []
        for cocktail in recommendations:
            if cocktail.name in candidate_names:
                valid.append(cocktail)
            else:
                logger.warning(
                    "browse_by_attribute: LLM returned cocktail outside KB; dropping",
                    extra={"name": cocktail.name},
                )

        logger.info(
            "browse_by_attribute: KB-grounded picks",
            extra={
                "attribute": attribute_label,
                "candidates": len(candidates),
                "returned": len(valid),
            },
        )
        return {"recommendations": valid, "browse_attribute": attribute_label}

    except Exception as e:
        logger.error(
            "browse_by_attribute: error generating recommendations",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        return {"recommendations": [], "browse_attribute": "unknown"}
