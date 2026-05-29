"""Constraint checker node: extracts user constraints (allergies, ABV limits, etc.)."""

import json
from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm
from src.state import AgentState, Constraints


CONSTRAINT_PROMPT = """Identify any constraints the user may have for cocktail recommendations.

Return JSON with:
- allergies: list of ingredients to avoid (e.g., ["nuts", "dairy", "citrus"])
- ingredients_on_hand: list of spirits/mixers available at home (if discernible from data)
- max_abv: maximum ABV tolerance, or null if no limit inferred

Be conservative: only flag allergies if explicitly signaled or strongly inferred from calendar/email patterns
(e.g., "allergy clinic visit" might suggest nut allergies). Never assume allergies.
If no constraints, return empty lists and null for max_abv."""

CONSTRAINT_SYSTEM = """You are a mixologist and safety advisor. Your job is to identify potential drink constraints
(allergies, ingredient restrictions) from user data. Be cautious: never fabricate allergies. Only flag what's signaled."""


async def constraint_checker(state: AgentState) -> dict:
    """
    Extract user constraints (allergies, max ABV, available ingredients).

    Input: state["raw_sources"], state["user_profile"]
    Output: {"constraints": Constraints}
    """
    logger.debug("constraint_checker: checking constraints")

    raw_sources = state.get("raw_sources", {})
    user_profile = state.get("user_profile")

    sources_summary = json.dumps(
        {
            name: {
                "signals": payload.get("signals", {}),
                "confidence": payload.get("confidence", 0.0),
            }
            for name, payload in raw_sources.items()
        },
        indent=2,
    )

    profile_dict = user_profile.model_dump() if user_profile else {}

    llm = get_llm()
    messages = [
        SystemMessage(content=CONSTRAINT_SYSTEM),
        HumanMessage(content=f"""{CONSTRAINT_PROMPT}

User Profile: {json.dumps(profile_dict)}
Source Signals: {sources_summary}"""),
    ]

    response = await llm.ainvoke(messages)
    logger.debug("constraint_checker: LLM response", extra={"response": response.content})

    try:
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        constraints_dict = json.loads(content)
        constraints = Constraints(**constraints_dict)
        logger.info("constraint_checker: constraints identified", extra={"constraints": constraints})
        return {"constraints": constraints}
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("constraint_checker: failed to parse constraints", extra={"error": str(e)})
        return {"constraints": Constraints()}
