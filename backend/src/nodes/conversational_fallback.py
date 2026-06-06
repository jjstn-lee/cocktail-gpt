"""Conversational fallback node: handles ambiguous or unclear user messages with helpful guidance."""

from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm
from src.state import AgentState

CONVERSATIONAL_FALLBACK_SYSTEM_PROMPT = """You are a friendly, knowledgeable bartender assistant.
Your role is to help users have a great conversation about cocktails and guide them toward useful actions.

The user has sent a message that doesn't clearly fit our main capabilities (recommendations, profile updates, etc.).
Respond warmly and conversationally. You can:
- Greet them and introduce what you can do
- Ask clarifying questions about their mood or preferences
- Guide them toward actions like:
  * "Give me cocktail recommendations" (for personalized suggestions)
  * "Here's what I like..." (to update their preferences)
  * "What do you know about me?" (to view their profile)
  * "Show me something smoky/citrusy/etc" (to browse by flavor/attribute)

Keep it brief (1-2 sentences), friendly, and engaging. Act like a bartender who enjoys chatting."""


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

    # Build conversation context
    messages = [SystemMessage(content=CONVERSATIONAL_FALLBACK_SYSTEM_PROMPT)]

    # Add message history if available
    if message_history and len(message_history) > 1:
        for msg in message_history[:-1]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=f"User: {msg['content']}"))
            elif msg["role"] == "assistant":
                messages.append(HumanMessage(content=f"Assistant: {msg['content']}"))

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
