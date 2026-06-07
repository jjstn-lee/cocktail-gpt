"""Profile updater node: extracts and applies profile updates from user message."""

import json
from loguru import logger
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from src.llm import get_llm
from src.prompts.base import GENERAL_SYSTEM_PROMPT
from src.state import AgentState, Preferences, Constraints
from src.nodes.utils import extract_json_from_llm_response


class ExtractedPreferences(BaseModel):
    """Extracted preference fields."""
    preferred_spirits: list[str] | None = None
    preferred_flavors: list[str] | None = None
    abv_preference: str | None = None
    style_preferences: list[str] | None = None


class ExtractedConstraints(BaseModel):
    """Extracted constraint fields."""
    allergies: list[str] | None = None
    ingredients_on_hand: list[str] | None = None
    max_abv: float | None = None


class ProfileUpdate(BaseModel):
    """Extracted profile updates from user message."""
    preferences: ExtractedPreferences | None = None
    constraints: ExtractedConstraints | None = None
    conversational_response: str  # Warm conversational acknowledgment of what was learned


# prompt-version: 2.0

PROFILE_UPDATER_SYSTEM_PROMPT = f"""{GENERAL_SYSTEM_PROMPT}

When the user tells you something about their preferences or constraints, acknowledge it warmly and extract what they're telling you.

Examples:
- User: "I really like tequila" → Extract tequila as a preference and acknowledge warmly
- User: "I'm allergic to nuts" → Extract as a constraint with warm acknowledgment
- User: "I prefer light drinks" → Note for future recommendations
- User: "I love fruity flavors" → Show enthusiasm and extract the preference

Your job is to:
1. Extract their preferences and constraints accurately
2. Generate a warm acknowledgment of what they told you

Return JSON with:
- preferences: What they enjoy (spirits, flavors, styles, ABV levels)
  - preferred_spirits: specific liquors they like (e.g., ["tequila", "mezcal"])
  - preferred_flavors: flavor profiles they gravitate toward (e.g., ["fruity", "herbal"])
  - abv_preference: how strong they like it ("light", "moderate", "strong")
  - style_preferences: types of drinks they enjoy (e.g., ["margarita", "daiquiri"])
- constraints: Anything they can't or prefer to avoid
  - allergies: ingredients to never suggest
  - ingredients_on_hand: what they have available
  - max_abv: the strongest they'd go
- conversational_response: A warm acknowledgment of what they told you (1-2 sentences)

Only record what they actually said — don't invent. But be generous: if they mention liking something, take note of it."""


async def profile_updater(state: AgentState) -> dict:
    """
    Extract and apply profile updates from user message.

    Input: state["latest_message"], state["message_history"], state["preferences"], state["constraints"]
    Output: {
        "preferences": updated Preferences or None,
        "constraints": updated Constraints or None,
        "profile_update_summary": explanation string
    }
    """
    print("[PROFILE_UPDATER] Starting profile update extraction")
    logger.debug("profile_updater: extracting profile updates")

    latest_message = state.get("latest_message")
    message_history = state.get("message_history", [])
    print(f"[PROFILE_UPDATER] Latest message: {latest_message}")
    current_preferences = state.get("preferences")
    current_constraints = state.get("constraints")

    if not latest_message:
        logger.warning("profile_updater: no latest_message in state")
        return {
            "preferences": current_preferences,
            "constraints": current_constraints,
            "profile_update_summary": "No message provided.",
        }

    llm = get_llm()
    updater_llm = llm.with_structured_output(ProfileUpdate)

    # Build message list with conversation history
    messages = [SystemMessage(content=PROFILE_UPDATER_SYSTEM_PROMPT)]

    # Add message history (excluding the current message, which is included separately below)
    if message_history and len(message_history) > 1:
        for msg in message_history[:-1]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

    # Add the current message
    messages.append(HumanMessage(content=f"Current user message: {latest_message}"))

    try:
        result = await updater_llm.ainvoke(messages)
        print(f"[PROFILE_UPDATER] LLM result object: {result}")
        print(f"[PROFILE_UPDATER] LLM result.preferences: {result.preferences}")
        print(f"[PROFILE_UPDATER] LLM result.constraints: {result.constraints}")
        print(f"[PROFILE_UPDATER] LLM result.conversational_response: {result.conversational_response}")
        logger.debug("profile_updater: LLM response", extra={"result": result.model_dump()})

        # Merge updates into existing preferences and constraints
        updated_preferences = current_preferences or Preferences()
        updated_constraints = current_constraints or Constraints()

        logger.debug(
            "profile_updater: before merge",
            extra={
                "current_preferences": updated_preferences.model_dump(),
                "current_constraints": updated_constraints.model_dump(),
                "extracted_prefs": result.preferences,
                "extracted_constraints": result.constraints,
            },
        )

        if result.preferences:
            pref_dict = updated_preferences.model_dump()
            # Merge extracted preferences (filter out None values)
            extracted_dict = result.preferences.model_dump(exclude_none=True)
            pref_dict.update(extracted_dict)
            updated_preferences = Preferences(**pref_dict)
            logger.debug(
                "profile_updater: preferences merged",
                extra={"updated": updated_preferences.model_dump()},
            )

        if result.constraints:
            cons_dict = updated_constraints.model_dump()
            # Merge extracted constraints (filter out None values)
            extracted_dict = result.constraints.model_dump(exclude_none=True)
            cons_dict.update(extracted_dict)
            updated_constraints = Constraints(**cons_dict)
            logger.debug(
                "profile_updater: constraints merged",
                extra={"updated": updated_constraints.model_dump()},
            )

        logger.info(
            "profile_updater: returning updates",
            extra={
                "preferences": updated_preferences.model_dump(),
                "constraints": updated_constraints.model_dump(),
                "summary": result.explanation,
            },
        )

        output = {
            "preferences": updated_preferences,
            "constraints": updated_constraints,
            "profile_update_summary": result.conversational_response,
        }
        print(f"[PROFILE_UPDATER] Returning output: {output}")
        print(f"[PROFILE_UPDATER] Preferences type: {type(updated_preferences)}")
        print(f"[PROFILE_UPDATER] Preferences value: {updated_preferences.model_dump()}")
        return output

    except Exception as e:
        error_msg = str(e)
        print(f"[PROFILE_UPDATER] ERROR: {error_msg}")
        import traceback
        print(f"[PROFILE_UPDATER] Traceback: {traceback.format_exc()}")
        logger.error("profile_updater: error extracting updates", extra={"error": error_msg})
        output = {
            "preferences": current_preferences,
            "constraints": current_constraints,
            "profile_update_summary": "Got it! I'll remember that for next time.",
        }
        print(f"[PROFILE_UPDATER] Returning error output: {output}")
        return output
