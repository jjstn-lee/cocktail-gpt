"""Retrieve profile node: uses LLM to intelligently summarize user profile data."""

from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from src.llm import get_llm
from src.prompts.base import GENERAL_SYSTEM_PROMPT
from src.state import AgentState

RETRIEVE_PROFILE_SYSTEM_PROMPT = f"""{GENERAL_SYSTEM_PROMPT}

Your job is to summarize what you know about the customer based on saved preferences, constraints, and interaction history.

Be personal, like someone who's known this customer for a while. You can:
- Emphasize what's most relevant
- Omit trivial details
- Add context or observations based on the data
- Ask follow-up questions if their profile seems incomplete

Format the summary naturally as a conversational response.
If they have no saved data yet, mention that their profile is empty and suggest they can update it through profile changes."""


async def retrieve_profile(state: AgentState) -> dict:
    """
    Use LLM to create an intelligent summary of user profile data.

    Input: state["preferences"], state["constraints"], state["feedback"], state["session_count"], state["recommendation_history"]
    Output: {"profile_summary": str}
    """
    logger.debug("retrieve_profile: summarizing profile with LLM")

    preferences = state.get("preferences")
    constraints = state.get("constraints")
    feedback = state.get("feedback", [])
    session_count = state.get("session_count", 0)
    recommendation_history = state.get("recommendation_history", [])

    # Build data summary for the LLM
    profile_data_lines = []

    if preferences:
        if preferences.preferred_spirits:
            profile_data_lines.append(f"Favorite spirits: {', '.join(preferences.preferred_spirits)}")
        if preferences.preferred_flavors:
            profile_data_lines.append(f"Preferred flavors: {', '.join(preferences.preferred_flavors)}")
        if preferences.abv_preference:
            profile_data_lines.append(f"ABV preference: {preferences.abv_preference}")
        if preferences.style_preferences:
            profile_data_lines.append(f"Style preferences: {', '.join(preferences.style_preferences)}")

    if constraints:
        if constraints.allergies:
            profile_data_lines.append(f"Allergies: {', '.join(constraints.allergies)}")
        if constraints.ingredients_on_hand:
            profile_data_lines.append(f"Ingredients on hand: {', '.join(constraints.ingredients_on_hand)}")
        if constraints.max_abv is not None:
            profile_data_lines.append(f"Max ABV: {constraints.max_abv}%")

    if feedback:
        positive_count = sum(1 for f in feedback if f.rating == 5)
        negative_count = sum(1 for f in feedback if f.rating == 1)
        profile_data_lines.append(f"Feedback: {len(feedback)} ratings ({positive_count} thumbs up, {negative_count} thumbs down)")

    if session_count > 0:
        profile_data_lines.append(f"Sessions: {session_count} recommendation runs")

    if recommendation_history:
        profile_data_lines.append(f"Recommendation history: {len(recommendation_history)} past sessions")

    # Build the prompt for the LLM
    if profile_data_lines:
        profile_data_str = "\n".join(profile_data_lines)
        user_message = f"Here's what I know about this customer:\n\n{profile_data_str}\n\nPlease summarize their profile in a conversational way."
    else:
        user_message = "I have no saved profile data for this customer yet. Please respond warmly and invite them to share their preferences."

    llm = get_llm()

    # Build messages with conversation history
    message_history = state.get("message_history", [])
    messages = [SystemMessage(content=RETRIEVE_PROFILE_SYSTEM_PROMPT)]

    # Add message history (excluding current turn)
    if message_history and len(message_history) > 1:
        for msg in message_history[:-1]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=user_message))

    try:
        result = await llm.ainvoke(messages)
        profile_summary = result.content
        logger.info("retrieve_profile: LLM generated profile summary")
    except Exception as e:
        logger.error("retrieve_profile: error generating summary", extra={"error": str(e)})
        profile_summary = "I had trouble retrieving your profile. Please try again."

    return {"profile_summary": profile_summary}
