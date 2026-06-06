"""Supervisor node: routes user intent to appropriate subgraph."""

from enum import Enum
from loguru import logger
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm
from src.state import AgentState


class Intent(str, Enum):
    """Possible user intents. Must stay in sync with src/intent_registry.py."""

    RECOMMENDATION = "recommendation"
    PROFILE_UPDATE = "profile_update"
    RATE_COCKTAIL = "rate_cocktail"
    EXPLAIN_RECOMMENDATION = "explain_recommendation"
    BROWSE_BY_ATTRIBUTE = "browse_by_attribute"
    MANAGE_RESTRICTIONS = "manage_restrictions"
    RETRIEVE_PROFILE = "retrieve_profile"
    CONVERSATIONAL_FALLBACK = "conversational_fallback"


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

2. **profile_update** — The user wants to update their profile (preferences or constraints) PERMANENTLY. Examples:
   - "I like whiskey and gin"
   - "I'm allergic to nuts"
   - "I prefer light drinks"
   - "I have vodka and lime juice on hand"
   - "Update my profile to prefer fruity flavors"
   - Language: permanent/enduring (I'm allergic, I like, I prefer)

3. **rate_cocktail** — The user is rating/providing feedback on a previous recommendation. Examples:
   - "I loved that last one!"
   - "That was too bitter"
   - "Not my style"
   - "That was perfect, thanks!"
   - "I didn't like that one"

4. **explain_recommendation** — The user wants to understand why a cocktail was recommended. Examples:
   - "Why did you recommend that?"
   - "Tell me more about that choice"
   - "Why would that work for me?"
   - "What's the reasoning behind that?"

5. **browse_by_attribute** — The user wants to explore cocktails by a specific attribute, flavor, ingredient, or style (NOT personal recommendations). Examples:
   - "show me something smoky"
   - "what can I make with gin?"
   - "I want something refreshing"
   - "show me rum drinks"
   - "what are some fruity cocktails?"

6. **manage_restrictions** — The user is setting a TEMPORARY, SESSION-ONLY restriction or limitation. Examples:
   - "I'm driving tonight, no alcohol"
   - "keep it low ABV for now"
   - "I'm out of citrus"
   - "make it non-alcoholic"
   - Language: temporal/contextual (tonight, right now, I'm out of, for now)

7. **retrieve_profile** — The user wants to see what you know about them (their saved preferences, constraints, feedback history). Examples:
   - "What do you know about me?"
   - "Show me my preferences"
   - "What's my profile?"
   - "What have I liked?"
   - "Tell me what you remember"

8. **conversational_fallback** — The user's message is ambiguous, unclear, or doesn't fit the above categories. Examples:
   - "Hello"
   - "What can you do?"
   - "Hi there"
   - "Tell me a joke"
   - Any vague chitchat or greeting

Always respond with a JSON object containing only the "intent" field set to one of: "recommendation", "profile_update", "rate_cocktail", "explain_recommendation", "browse_by_attribute", "manage_restrictions", "retrieve_profile", or "conversational_fallback"."""


async def supervisor(state: AgentState) -> dict:
    """
    Route user intent to the appropriate subgraph.

    Input: state["latest_message"] and state["message_history"] (assumed to be in state)
    Output: {"intent": "recommendation" | "profile_update" | ...}
    """
    logger.debug("supervisor: classifying user intent")

    latest_message = state.get("latest_message")
    message_history = state.get("message_history", [])

    if not latest_message:
        logger.warning("supervisor: no latest_message in state, defaulting to conversational_fallback")
        return {"intent": Intent.CONVERSATIONAL_FALLBACK.value}

    llm = get_llm()

    # Use structured output to classify intent
    supervisor_llm = llm.with_structured_output(SupervisorOutput)

    # Build message list with conversation history
    messages = [SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT)]

    # Add message history (excluding the current message, which is included separately below)
    if message_history and len(message_history) > 1:
        for msg in message_history[:-1]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(SystemMessage(content=f"Assistant: {msg['content']}"))

    # Add the current message
    messages.append(HumanMessage(content=f"Current user message: {latest_message}"))

    try:
        result = await supervisor_llm.ainvoke(messages)
        intent = result.intent
        # Convert enum to string for storage in state
        intent_str = intent.value if isinstance(intent, Intent) else str(intent)
        logger.info("supervisor: classified intent", extra={"intent": intent_str})
        logger.debug(
            f"supervisor: classified '{latest_message}' as '{intent_str}' (history length: {len(message_history)})"
        )
        return {"intent": intent_str}
    except Exception as e:
        logger.error("supervisor: error classifying intent", extra={"error": str(e)})
        # Default to conversational_fallback if classification fails
        return {"intent": Intent.CONVERSATIONAL_FALLBACK.value}


def _assert_intent_matches_registry():
    """Fail fast if the Intent enum drifts from the intent registry.

    This is called at module load time. If Intent enum and registry are out of sync,
    the application fails to start with a clear error message.
    """
    from src.intent_registry import load_registry

    registry_keys = set(load_registry().keys())
    enum_values = {e.value for e in Intent}

    if registry_keys != enum_values:
        raise RuntimeError(
            f"Intent enum out of sync with registry.\n"
            f"  Enum values:    {sorted(enum_values)}\n"
            f"  Registry keys:  {sorted(registry_keys)}"
        )


# Validate on module import
_assert_intent_matches_registry()
