"""Supervisor node: routes user intent to appropriate subgraph."""

from enum import Enum
from loguru import logger
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm
from src.state import AgentState


class Intent(str, Enum):
    """Possible user intents."""
    RECOMMENDATION = "recommendation"
    PROFILE_UPDATE = "profile_update"


class SupervisorOutput(BaseModel):
    """Structured output from the supervisor node."""
    intent: Intent


SUPERVISOR_SYSTEM_PROMPT = """You are a routing supervisor for a cocktail recommendation agent.
Your job is to classify the user's intent based on their message.

Classify the user's message into one of these categories:

1. **recommendation** — The user wants cocktail recommendations. Examples:
   - "Give me a cocktail recommendation"
   - "What should I drink tonight?"
   - "I'd like a drink suggestion"
   - "What goes well with [mood/occasion]?"
   - User is answering a clarification question from a previous recommendation

2. **profile_update** — The user wants to update their profile (preferences or constraints). Examples:
   - "I like whiskey and gin"
   - "I'm allergic to nuts"
   - "I prefer light drinks"
   - "I have vodka and lime juice on hand"
   - "Update my profile to prefer fruity flavors"

Always respond with a JSON object containing only the "intent" field set to either "recommendation" or "profile_update"."""


async def supervisor(state: AgentState) -> dict:
    """
    Route user intent to the appropriate subgraph.

    Input: state["user_id"], state["latest_message"] (assumed to be in state)
    Output: {"intent": "recommendation" | "profile_update"}
    """
    logger.debug("supervisor: classifying user intent")

    user_id = state.get("user_id")
    latest_message = state.get("latest_message")

    if not latest_message:
        logger.warning("supervisor: no latest_message in state, defaulting to recommendation")
        return {"intent": Intent.RECOMMENDATION.value}

    llm = get_llm()

    # Use structured output to classify intent
    supervisor_llm = llm.with_structured_output(SupervisorOutput)

    messages = [
        SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
        HumanMessage(content=f"User message: {latest_message}"),
    ]

    try:
        result = await supervisor_llm.ainvoke(messages)
        intent = result.intent
        # Convert enum to string for storage in state
        intent_str = intent.value if isinstance(intent, Intent) else str(intent)
        logger.info("supervisor: classified intent", extra={"intent": intent_str})
        logger.debug(
            f"supervisor: classified '{latest_message}' as '{intent_str}'"
        )
        return {"intent": intent_str}
    except Exception as e:
        logger.error("supervisor: error classifying intent", extra={"error": str(e)})
        # Default to recommendation if classification fails
        return {"intent": Intent.RECOMMENDATION.value}
