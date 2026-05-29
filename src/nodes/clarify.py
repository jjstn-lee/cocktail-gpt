"""Clarify node: asks a follow-up question when confidence is low."""

from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm
from src.state import AgentState
from src.prompts.clarify import CLARIFY_PROMPT, CLARIFY_SYSTEM_PROMPT


async def clarify(state: AgentState) -> dict:
    """
    Ask a clarification question to the user when confidence is low.

    Input: state["confidence_score"], state["user_profile"], state["preferences"]
    Output: {"clarification_question": str, "session_clarification_used": True}

    This node only runs if confidence_score < CLARIFY_THRESHOLD and this is the first clarification.
    """
    logger.debug("clarify: asking clarification question")

    llm = get_llm()
    messages = [
        SystemMessage(content=CLARIFY_SYSTEM_PROMPT),
        HumanMessage(content=CLARIFY_PROMPT),
    ]

    response = await llm.ainvoke(messages)
    clarification_question = response.content.strip()

    logger.info("clarify: clarification question generated", extra={"question": clarification_question})

    return {
        "clarification_question": clarification_question,
        "session_clarification_used": True,
    }
