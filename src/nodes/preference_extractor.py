"""Preference extractor node: extracts spirit and flavor preferences from user profile and sources."""

import json
from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm
from src.state import AgentState, Preferences


PREFERENCE_EXTRACTION_PROMPT = """Extract the user's spirit and flavor preferences from the provided profile and source signals.

Return JSON with:
- preferred_spirits: list of spirits/liqueurs the user likely enjoys (e.g., ["vodka", "gin", "tequila"]) based on music taste, previous data
- preferred_flavors: list of flavor profiles (e.g., ["citrus", "herbal", "spicy", "fruity", "floral"])
- abv_preference: one of "strong" (>20% ABV), "moderate" (15–20%), or "light" (<15%) based on context
- style_preferences: list of styles (e.g., ["sour", "salty", "sweet", "bitters-forward", "bubbly"])

Be data-driven: if Spotify shows tropical vibes, suggest rum over bourbon. If weather is cold, suggest warming spirits.
Only include preferences if signaled by the data. Return empty lists for unknown preferences."""

PREFERENCE_EXTRACTION_SYSTEM = """You are a mixologist analyzing user data to infer spirit and flavor preferences.
Your goal is to extract a pattern of the user's drink tastes from Spotify, weather, calendar, and other signals."""


async def preference_extractor(state: AgentState) -> dict:
    """
    Extract user preferences for spirits, flavors, and styles.

    Input: state["raw_sources"], state["user_profile"]
    Output: {"preferences": Preferences}
    """
    logger.debug("preference_extractor: extracting preferences")

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
        SystemMessage(content=PREFERENCE_EXTRACTION_SYSTEM),
        HumanMessage(content=f"""{PREFERENCE_EXTRACTION_PROMPT}

User Profile: {json.dumps(profile_dict)}
Source Signals: {sources_summary}"""),
    ]

    response = await llm.ainvoke(messages)
    logger.debug("preference_extractor: LLM response", extra={"response": response.content})

    try:
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        prefs_dict = json.loads(content)
        preferences = Preferences(**prefs_dict)
        logger.info("preference_extractor: preferences extracted", extra={"preferences": preferences})
        return {"preferences": preferences}
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("preference_extractor: failed to parse preferences", extra={"error": str(e)})
        return {"preferences": Preferences()}
