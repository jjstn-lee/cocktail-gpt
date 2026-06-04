"""Business logic for conversational chat with intent routing."""

import uuid
from typing import Any
from loguru import logger
from langgraph.errors import GraphInterrupt

from src.storage.user_store import UserStore
from src.state import AgentState, Feedback, Preferences
from src.api.schemas import ChatRequest, ChatResponse, CocktailOut
from src.nodes.recommender import recommender


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

    user_id comes from the authenticated Google user, not the request.
    """
    thread_id = request.thread_id or str(uuid.uuid4())
    logger.info(
        "chat_service: handling chat message",
        extra={"user_id": user_id, "thread_id": thread_id, "message": request.message},
    )

    # Build initial state
    state: AgentState = {
        "user_id": user_id,
        "thread_id": thread_id,
        "latest_message": request.message,
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
    config = {"configurable": {"thread_id": thread_id}}
    clarification_question: str | None = None
    final_state: dict[str, Any] = {}

    try:
        final_state = await graph.ainvoke(state, config=config)
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

    # Build response based on intent
    if intent == "profile_update":
        # Profile update path: return the summary
        profile_update_summary = final_state.get("profile_update_summary", "Profile updated.")

        # Save updated preferences and constraints if user_store is available
        if user_store:
            prefs = final_state.get("preferences")
            if prefs:
                # Remove genre_spirits before saving (session-specific data)
                # Only save user-explicitly-set preferences to profile
                prefs_dict = prefs.model_dump()
                prefs_dict.pop("genre_spirits", None)  # Remove session-specific data
                clean_prefs = Preferences(**prefs_dict)
                user_store.save_preferences(user_id, clean_prefs)
                logger.info(
                    "chat_service: saved preferences",
                    extra={
                        "user_id": user_id,
                        "preferred_spirits": clean_prefs.preferred_spirits,
                        "preferred_flavors": clean_prefs.preferred_flavors,
                    },
                )

            constraints = final_state.get("constraints")
            if constraints:
                user_store.save_constraints(user_id, constraints)
                logger.info(
                    "chat_service: saved constraints",
                    extra={"user_id": user_id, "constraints": constraints.model_dump()},
                )

        return ChatResponse(
            thread_id=thread_id,
            intent="profile_update",
            profile_update_summary=profile_update_summary,
            degraded=False,
        )

    else:  # "recommendation" or default
        # Recommendation path: return recommendations
        recommendations = [
            CocktailOut(
                name=c.name,
                ingredients=c.ingredients,
                method=c.method,
                flavor_notes=c.flavor_notes,
                why_this_works=c.why_this_works,
            )
            for c in final_state.get("recommendations", [])
        ]

        # Save session to cross-session memory if user_store is provided and not asking for clarification
        if user_store and clarification_question is None:
            cocktail_names = [c.name for c in final_state.get("recommendations", [])]
            user_store.save_session_recommendations(user_id, thread_id, cocktail_names)
            user_store.increment_session_count(user_id)

        needs_clarification = clarification_question is not None

        return ChatResponse(
            thread_id=thread_id,
            intent="recommendation",
            recommendations=recommendations,
            confidence_score=final_state.get("confidence_score", 0.0),
            rationale=final_state.get("rationale", ""),
            needs_clarification=needs_clarification,
            clarification_question=clarification_question,
            degraded=False,
        )
