"""Clarify node: asks a follow-up question when confidence is low."""

from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt

from src.llm import get_llm
from src.prompts.base import GENERAL_SYSTEM_PROMPT
from src.state import AgentState
from src.prompts.clarify import CLARIFY_PROMPT


async def clarify(state: AgentState) -> dict:
    """
    Ask a clarification question to the user when confidence is low.

    Input: state["confidence_score"], state["user_profile"], state["preferences"]
    Output: {"clarification_answer": str, "session_clarification_used": True}

    This node pauses at interrupt() and resumes when the user submits an answer via /clarify.
    """
    logger.debug("clarify: asking clarification question")
    print(f"\n[CLARIFY] Confidence too low, asking clarification question...")
    print(f"[CLARIFY] Confidence score: {state.get('confidence_score')}")
    print(f"[CLARIFY] Threshold: 0.65")

    llm = get_llm()
    messages = [
        SystemMessage(content=GENERAL_SYSTEM_PROMPT),
        HumanMessage(content=CLARIFY_PROMPT),
    ]

    response = await llm.ainvoke(messages)
    clarification_question = response.content.strip()

    logger.info("clarify: clarification question generated", extra={"question": clarification_question})
    print(f"[CLARIFY] LLM generated question:")
    print(f"{clarification_question}")

    # Pause graph execution and return the question to the caller
    # The graph will resume when Command(resume=answer) is invoked with the user's response
    answer = interrupt(clarification_question)

    logger.info("clarify: user provided answer", extra={"answer": answer})
    print(f"[CLARIFY] User answer received: {answer}")

    return {
        "clarification_answer": answer,
        "session_clarification_used": True,
    }
