"""Self-information node: explains what the agent can and cannot do."""

from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from src.llm import get_llm
from src.prompts.base import GENERAL_SYSTEM_PROMPT
from src.prompts.self_info import SELF_INFO_CONTENT
from src.state import AgentState


def _get_self_information_system_prompt() -> str:
    """Build self-information system prompt."""
    node_specific = f"""Your role is to explain what you can and cannot do as a bartender recommendation assistant.

Reference this information about your capabilities:

{SELF_INFO_CONTENT}

When the user asks about your capabilities, provide a natural, conversational answer that highlights the most relevant features based on their question. You may emphasize certain capabilities over others based on context, but be honest about your limitations.

Examples:
- If they ask "what can you do?", give a brief overview
- If they ask "can you order drinks?", directly address that limitation
- If they ask "how do you work?", explain the personalization process

Keep responses concise and friendly. Use markdown formatting for lists if it helps clarity."""

    return f"{GENERAL_SYSTEM_PROMPT}\n\nOVERRIDE: You may explain your capabilities in this context (this is the only node where capability explanations are allowed).\n\n{node_specific}"


async def self_information(state: AgentState) -> dict:
    """
    Explain the agent's capabilities and limitations.

    Input: state["latest_message"] and state["message_history"]
    Output: {"self_information_message": str}
    """
    logger.debug("self_information: generating capability explanation")

    latest_message = state.get("latest_message", "")
    message_history = state.get("message_history", [])

    llm = get_llm()

    # Build conversation context with system prompt
    system_prompt = _get_self_information_system_prompt()
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
        self_info_message = result.content
        logger.info(
            "self_information: generated explanation",
            extra={"message": latest_message[:50], "response": self_info_message[:100]},
        )
        return {"self_information_message": self_info_message}
    except Exception as e:
        logger.error(
            "self_information: error generating explanation",
            extra={"error": str(e)},
        )
        # Fallback message if LLM fails
        return {
            "self_information_message": f"I can recommend cocktails based on your preferences, Spotify data, and feedback. "
            "I can also help you manage your profile, browse cocktails by style, and explain my recommendations. "
            "I cannot order drinks or provide medical/allergy advice."
        }
