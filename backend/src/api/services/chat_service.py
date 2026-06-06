"""Business logic for conversational chat with intent routing."""

import uuid
import json
from typing import Any, AsyncGenerator
from loguru import logger
from langgraph.errors import GraphInterrupt

from src.storage.user_store import UserStore
from src.state import AgentState, Feedback
from src.api.schemas import ChatRequest, ChatResponse
from src.nodes.recommender import recommender
from src.api.services.streaming_utils import get_status_message


async def handle_chat(
    request: ChatRequest,
    user_id: str,
    graph: Any,
    checkpointer: Any,
    user_store: UserStore | None = None,
) -> ChatResponse:
    """
    Handle a conversational chat message and route based on intent.

    The supervisor node will classify the intent based on the message:
    - "recommendation": generates cocktail recommendations
    - "profile_update": extracts and applies profile updates
    - "explain_recommendation", "rate_cocktail", etc.: lightweight follow-up intents that need prior state

    user_id comes from the authenticated Google user, not the request.
    """
    thread_id = request.thread_id or str(uuid.uuid4())
    logger.info(
        "chat_service: handling chat message",
        extra={"user_id": user_id, "thread_id": thread_id, "message": request.message},
    )

    print(f"[CHAT_SVC] request.thread_id: {request.thread_id}")
    print(f"[CHAT_SVC] using thread_id: {thread_id}")

    # Load prior state from checkpointer if this is a continuation (same thread_id)
    prior_state: AgentState | None = None
    config = {"configurable": {"thread_id": thread_id}}

    if request.thread_id:
        try:
            # Use graph's get_state method to load the prior state
            state_snapshot = await graph.aget_state(config)
            print(f"[CHAT_SVC] state_snapshot loaded: {state_snapshot is not None}")

            if state_snapshot and state_snapshot.values:
                prior_state = state_snapshot.values
                recs = prior_state.get("recommendations", [])
                print(f"[CHAT_SVC] Loaded prior state with {len(recs)} recommendations")
                logger.debug(
                    "chat_service: loaded prior state from graph",
                    extra={
                        "thread_id": thread_id,
                        "has_recommendations": bool(prior_state.get("recommendations")),
                    },
                )
            else:
                print(f"[CHAT_SVC] No prior state snapshot found")
        except Exception as e:
            print(f"[CHAT_SVC] Error loading state: {e}")
            logger.debug(
                "chat_service: no prior state in checkpointer",
                extra={"thread_id": thread_id, "error": str(e)},
            )

    # Build initial state
    if prior_state:
        # Continue from prior state: copy it and update latest_message.
        # This preserves prior recommendations, user profile, preferences, constraints, etc.
        # Important for follow-up intents like "explain_recommendation" that need prior context.
        state = prior_state.copy()
        state["latest_message"] = request.message
        state["intent"] = None  # Reset intent for new supervisor classification
        # Append message to conversation history
        if "message_history" not in state or state["message_history"] is None:
            state["message_history"] = []
        state["message_history"].append({"role": "user", "content": request.message})
        logger.debug(
            "chat_service: continuing from prior state",
            extra={
                "thread_id": thread_id,
                "has_prior_recommendations": bool(state.get("recommendations")),
                "message_history_length": len(state.get("message_history", [])),
            },
        )
    else:
        # New conversation: build fresh state
        state: AgentState = {
            "user_id": user_id,
            "thread_id": thread_id,
            "latest_message": request.message,
            "message_history": [{"role": "user", "content": request.message}],
            "intent": None,  # Will be set by supervisor
            "raw_sources": {},
            "recommendations": [],
            "confidence_score": 0.0,
            "rationale": "",
            "clarification_answer": None,
            "session_count": 0,
            "session_clarification_used": False,
            "feedback": [],
            "recommendation_history": [],
            "profile_update_summary": None,
        }

        # Merge stored user preferences, constraints, feedback, history, and session count
        if user_store:
            stored_prefs = user_store.get_preferences(user_id)
            if stored_prefs:
                state["preferences"] = stored_prefs
            stored_constraints = user_store.get_constraints(user_id)
            if stored_constraints:
                state["constraints"] = stored_constraints
            # Load cross-session memory
            stored_feedback = user_store.load_feedback(user_id)
            if stored_feedback:
                state["feedback"] = [Feedback(**fb) for fb in stored_feedback]
            stored_history = user_store.load_recommendation_history(user_id)
            if stored_history:
                state["recommendation_history"] = stored_history
            state["session_count"] = user_store.get_session_count(user_id)

    # Run the graph with persistence
    clarification_question: str | None = None
    final_state: dict[str, Any] = {}

    print(f"[CHAT_SVC] About to invoke graph with state containing {len(state.get('recommendations', []))} recommendations")
    print(f"[CHAT_SVC] State keys before graph: {list(state.keys())}")

    try:
        final_state = await graph.ainvoke(state, config=config)
        print(f"[CHAT_SVC] State keys after graph: {list(final_state.keys())}")
        print(f"[CHAT_SVC] Final state intent: {final_state.get('intent')}")
        if final_state.get('intent') == 'explain_recommendation':
            print(f"[CHAT_SVC] Explanation in final_state: {final_state.get('explanation', 'NOT FOUND')}")
        logger.info(
            "chat_service: chat processing complete",
            extra={
                "user_id": user_id,
                "thread_id": thread_id,
                "intent": final_state.get("intent"),
            },
        )
    except GraphInterrupt as e:
        # Graph paused at clarify node; extract the clarification question
        clarification_question = e.args[0] if e.args else None
        logger.info(
            "chat_service: graph paused at clarification",
            extra={
                "user_id": user_id,
                "thread_id": thread_id,
                "clarification_question": clarification_question,
            },
        )

    # Determine the intent that was routed to
    intent = final_state.get("intent", "recommendation")

    logger.info(
        "chat_service: graph completed",
        extra={
            "user_id": user_id,
            "intent": intent,
            "has_preferences": "preferences" in final_state,
            "preferences_value": final_state.get("preferences"),
            "has_profile_summary": "profile_update_summary" in final_state,
        },
    )

    # Build response using registry-driven dispatch
    from src.intent_registry import load_registry, get_default_intent

    registry = load_registry()
    if intent not in registry:
        logger.warning(
            "chat_service: unknown intent, using default",
            extra={"intent": intent, "default": get_default_intent()},
        )
        intent = get_default_intent()

    response_builder = registry[intent].response_builder
    response = await response_builder(
        final_state, thread_id, clarification_question, user_store, user_id
    )

    print(f"[CHAT_SVC] Returning response: intent={response.intent}")
    if hasattr(response, 'explanation') and response.explanation:
        print(f"[CHAT_SVC] Explanation in response: {response.explanation}")

    return response


async def stream_chat(
    request: ChatRequest,
    user_id: str,
    graph: Any,
    checkpointer: Any,
    user_store: UserStore | None = None,
) -> AsyncGenerator[str, None]:
    """
    Stream chat response with intermediate node status updates.

    Yields line-delimited JSON with status updates and final response.
    Each line is a JSON object: {"type": "status", "message": "..."} or {"type": "response", "data": {...}}
    """
    thread_id = request.thread_id or str(uuid.uuid4())

    # Load/build initial state (same as handle_chat)
    prior_state: AgentState | None = None
    config = {"configurable": {"thread_id": thread_id}}

    if request.thread_id:
        try:
            state_snapshot = await graph.aget_state(config)
            if state_snapshot and state_snapshot.values:
                prior_state = state_snapshot.values
        except Exception as e:
            logger.debug(f"No prior state: {e}")

    if prior_state:
        state = prior_state.copy()
        state["latest_message"] = request.message
        state["intent"] = None
        if "message_history" not in state or state["message_history"] is None:
            state["message_history"] = []
        state["message_history"].append({"role": "user", "content": request.message})
    else:
        state: AgentState = {
            "user_id": user_id,
            "thread_id": thread_id,
            "latest_message": request.message,
            "message_history": [{"role": "user", "content": request.message}],
            "intent": None,
            "raw_sources": {},
            "recommendations": [],
            "confidence_score": 0.0,
            "rationale": "",
            "clarification_answer": None,
            "session_count": 0,
            "session_clarification_used": False,
            "feedback": [],
            "recommendation_history": [],
            "profile_update_summary": None,
        }

        if user_store:
            stored_prefs = user_store.get_preferences(user_id)
            if stored_prefs:
                state["preferences"] = stored_prefs
            stored_constraints = user_store.get_constraints(user_id)
            if stored_constraints:
                state["constraints"] = stored_constraints
            stored_feedback = user_store.load_feedback(user_id)
            if stored_feedback:
                state["feedback"] = [Feedback(**fb) for fb in stored_feedback]
            stored_history = user_store.load_recommendation_history(user_id)
            if stored_history:
                state["recommendation_history"] = stored_history
            state["session_count"] = user_store.get_session_count(user_id)

    # Stream graph execution with status updates
    clarification_question: str | None = None
    final_state: dict[str, Any] = {}
    seen_nodes = set()

    try:
        # Stream events for status updates while graph executes
        async for event in graph.astream_events(state, config=config, version="v1"):
            # Get node start events
            if event.get("event") == "on_chain_start":
                # Get the node/chain name
                node_name = event.get("name", "").lower()

                # Skip duplicate status messages (multiple calls to same node in one run)
                if node_name and node_name not in seen_nodes and node_name in [
                    "supervisor", "ingest", "profile_builder", "preference_extractor",
                    "constraint_checker", "recommender", "clarify", "output",
                    "profile_updater", "rate_cocktail", "explain_recommendation",
                    "browse_by_attribute", "manage_restrictions", "retrieve_profile"
                ]:
                    seen_nodes.add(node_name)
                    status_msg = get_status_message(node_name)
                    yield json.dumps({"type": "status", "message": status_msg}) + "\n"
                    logger.debug(f"Status: {status_msg}")

    except GraphInterrupt as e:
        # Graph paused for clarification - this is expected and normal
        clarification_question = e.args[0] if e.args else None
        logger.info(
            "chat_service: graph paused at clarification",
            extra={
                "user_id": user_id,
                "thread_id": thread_id,
                "clarification_question": clarification_question,
            },
        )
    except Exception as e:
        logger.error(f"Graph streaming error: {e}")
        yield json.dumps({"type": "error", "message": str(e)}) + "\n"
        return

    # Get final state from checkpointer
    try:
        final_state_snapshot = await graph.aget_state(config)
        if final_state_snapshot and final_state_snapshot.values:
            final_state = final_state_snapshot.values
            logger.debug("Got final state from aget_state", extra={"keys": list(final_state.keys())})
        else:
            logger.error("No state snapshot returned from aget_state")
    except Exception as e:
        logger.error(f"Error getting final state: {e}")

    # Build response
    intent = final_state.get("intent", "recommendation")

    logger.info(
        "chat_service: graph completed",
        extra={
            "user_id": user_id,
            "intent": intent,
            "has_recommendations": bool(final_state.get("recommendations")),
        },
    )

    # Build response using registry
    from src.intent_registry import load_registry, get_default_intent

    registry = load_registry()
    if intent not in registry:
        intent = get_default_intent()

    response_builder = registry[intent].response_builder
    response = await response_builder(
        final_state, thread_id, clarification_question, user_store, user_id
    )

    logger.debug(
        "Built response",
        extra={
            "intent": response.intent,
            "status": response.status,
            "has_recommendations": len(getattr(response, "recommendations", [])) > 0,
        },
    )

    # Yield final response
    response_dict = response.model_dump()
    yield json.dumps({
        "type": "response",
        "data": response_dict
    }) + "\n"

    logger.info("Streamed final response", extra={"intent": intent})
