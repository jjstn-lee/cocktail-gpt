"""Preference extractor node: extracts spirit and flavor preferences from user profile and sources."""

import json
from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm
from src.state import AgentState, Preferences
from src.nodes.utils import extract_json_from_llm_response


PREFERENCE_EXTRACTION_PROMPT = """Extract the user's spirit and flavor preferences from the provided profile and Spotify signals.

## Mapping Spotify Data to Spirit & Flavor Preferences:
- **Genres** → Spirit archetypes:
  - Electronic, hip-hop, dance → vodka, tequila (crisp, modern)
  - Jazz, soul, R&B → bourbon, cognac (smooth, warm)
  - Reggae, tropical → rum (light, fruity)
  - Rock, metal → whiskey, rye (bold, complex)
  - Indie, pop → gin, vodka (versatile)
  - Country → whiskey, bourbon (traditional)
- **Audio Features** → Flavor & ABV:
  - High energy (>0.7) + high danceability → bold spirits, citrus/spicy, energetic drinks
  - Low energy (<0.4) + high acousticness → light spirits, smooth/herbal, sipping drinks
  - High valence (>0.7, upbeat) → sweet/fruity flavors, refreshing
  - Low valence (<0.4, moody) → herbal/bitter, complex
  - High tempo (>120 BPM) → strong ABV (>20%), exciting drinks
  - Low tempo (<90 BPM) → light ABV (<15%), contemplative drinks

Return JSON with:
- preferred_spirits: list of spirits/liqueurs (e.g., ["vodka", "gin", "rum"]) mapped from genres and audio mood
- preferred_flavors: list of flavor profiles (e.g., ["citrus", "herbal", "spicy", "fruity", "floral", "smoky"])
- abv_preference: one of "strong" (>20%), "moderate" (15–20%), or "light" (<15%) based on tempo and energy
- style_preferences: list of styles (e.g., ["sour", "salty", "sweet", "bitters-forward", "bubbly", "spirit-forward"])

Be data-driven: trust Spotify audio features more than any other signal. Only include preferences if clearly signaled. Return empty lists for unknowns."""

PREFERENCE_EXTRACTION_SYSTEM = """You are a mixologist analyzing Spotify data to infer spirit and flavor preferences.
Your goal is to map the user's music taste (genres, audio features, energy) into drink preferences.
Use Spotify audio features (energy, valence, tempo, acousticness) as the primary signal for spirit selection and ABV preference."""


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
        # Extract JSON from response (handles markdown code blocks and explanations)
        prefs_dict = extract_json_from_llm_response(response.content)
        inferred = Preferences(**prefs_dict)

        # Merge with existing state preferences: user-set values win, LLM fills blanks
        existing = state.get("preferences") or Preferences()
        merged = Preferences(
            preferred_spirits=existing.preferred_spirits or inferred.preferred_spirits,
            preferred_flavors=existing.preferred_flavors or inferred.preferred_flavors,
            abv_preference=existing.abv_preference or inferred.abv_preference,
            style_preferences=existing.style_preferences or inferred.style_preferences,
        )

        logger.info(
            "preference_extractor: preferences extracted and merged",
            extra={"preferences": merged},
        )
        return {"preferences": merged}
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("preference_extractor: failed to parse preferences", extra={"error": str(e)})
        return {"preferences": state.get("preferences") or Preferences()}
