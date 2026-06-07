"""Conversational fallback node: handles ambiguous or unclear user messages with helpful guidance."""

from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from src.llm import get_llm
from src.prompts.base import GENERAL_SYSTEM_PROMPT
from src.state import AgentState

def _get_conversational_fallback_system_prompt() -> str:
    """Build conversational fallback system prompt."""
    node_specific = """Your role is to guide the user toward the right action without making promises about what will happen next.

Simply acknowledge their message and guide them to the most relevant action:
- "Give me cocktail recommendations" — Gets personalized recommendations based on their Spotify data and preferences
- "Here's what I like..." — Lets them save permanent preferences and constraints
- "What do you know about me?" — Shows their saved profile
- "Show me something smoky/citrusy/etc" — Explores cocktails by flavor or style (no personalization)

Do NOT:
- Promise that there will be interactive back-and-forth questions (there won't be in the recommendation flow)
- Make up details about what will happen when they choose an action
- Ask clarifying questions yourself (just guide them to the right feature)

Keep it brief, friendly, and honest about what each action does."""

    return f"{GENERAL_SYSTEM_PROMPT}\n\n{node_specific}"


async def conversational_fallback(state: AgentState) -> dict:
    """
    Handle ambiguous or unclear user messages with a helpful conversational response.

    Input: state["latest_message"] and state["message_history"]
    Output: {"fallback_message": str}
    """
    logger.debug("conversational_fallback: generating response for ambiguous message")

    latest_message = state.get("latest_message", "")
    message_history = state.get("message_history", [])

    llm = get_llm()

    # Build conversation context with system prompt
    system_prompt = _get_conversational_fallback_system_prompt()
    messages = [SystemMessage(content=system_prompt)]

    # Add message history if available
    if message_history and len(message_history) > 1:
        for msg in message_history[:-1]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

    # Add the current message
    messages.append(HumanMessage(content=latest_message if latest_message else ""))

    try:
        result = await llm.ainvoke(messages)
        fallback_message = result.content
        logger.info(
            "conversational_fallback: generated response",
            extra={"message": latest_message[:50], "response": fallback_message[:100]},
        )
        return {"fallback_message": fallback_message}
    except Exception as e:
        logger.error(
            "conversational_fallback: error generating response",
            extra={"error": str(e)},
        )
        # Fallback message if LLM fails
        return {
            "fallback_message": "I'm here to help! You can ask me for cocktail recommendations, "
            "update your preferences, or ask what I know about you. What would you like to do?"
        }
