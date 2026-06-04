"""Business logic for recommendations and clarifications."""

import uuid
from typing import Any
from loguru import logger
from langgraph.errors import GraphInterrupt
from langgraph.types import Command

from src.storage.user_store import UserStore
from src.state import AgentState, Feedback
from src.api.schemas import RecommendRequest, ClarifyRequest, RecommendResponse, CocktailOut
from src.nodes.recommender import recommender


async def get_recommendations(
    request: RecommendRequest,
    user_id: str,
    graph: Any,
    checkpointer: Any,
    user_store: UserStore | None = None,
) -> RecommendResponse:
    """
    Run the graph to generate recommendations for a user.

    If thread_id is None, generate a new one. Pass to graph.ainvoke() with config.
    user_id comes from the authenticated Google user, not the request.
    If no message is provided, defaults to "I'd like a recommendation" to trigger recommendation intent.
    """
    thread_id = request.thread_id or str(uuid.uuid4())
    # Default message for backward compatibility: if no message provided, indicate recommendation intent
    message = request.message or "I'd like a cocktail recommendation"

    logger.info(
        "recommendation_service: generating recommendations",
        extra={"user_id": user_id, "thread_id": thread_id, "message": message},
    )

    # Build initial state
    state: AgentState = {
        "user_id": user_id,
        "thread_id": thread_id,
        "latest_message": message,
        "raw_sources": {},
        "recommendations": [],
        "confidence_score": 0.0,
        "rationale": "",
        "clarification_answer": None,
        "session_count": 0,
        "session_clarification_used": False,
        "feedback": [],
        "recommendation_history": [],
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
            "recommendation_service: recommendations complete",
            extra={
                "user_id": user_id,
                "thread_id": thread_id,
                "recommendations_count": len(final_state.get("recommendations", [])),
                "confidence_score": final_state.get("confidence_score", 0.0),
            },
        )
    except GraphInterrupt as e:
        # Graph paused at clarify node; extract the clarification question from interrupt payload
        clarification_question = e.args[0] if e.args else None
        logger.info(
            "recommendation_service: graph paused at clarification",
            extra={
                "user_id": user_id,
                "thread_id": thread_id,
                "clarification_question": clarification_question,
            },
        )

    # Build response
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
        # Only save if we're returning final recommendations (not asking for clarification)
        cocktail_names = [c.name for c in final_state.get("recommendations", [])]
        user_store.save_session_recommendations(user_id, thread_id, cocktail_names)
        user_store.increment_session_count(user_id)

    needs_clarification = clarification_question is not None

    return RecommendResponse(
        thread_id=thread_id,
        recommendations=recommendations,
        confidence_score=final_state.get("confidence_score", 0.0),
        rationale=final_state.get("rationale", ""),
        needs_clarification=needs_clarification,
        clarification_question=clarification_question,
        degraded=False,  # TODO: detect source failures
    )


async def submit_clarification(
    request: ClarifyRequest,
    user_id: str,
    graph: Any,
    checkpointer: Any,
    user_store: UserStore | None = None,
) -> RecommendResponse:
    """
    Submit a clarification answer and re-run the recommender with the clarification.

    Load the saved state from the checkpointer and update it with the clarification_answer,
    then re-run only the recommender node (skip ingest and profile nodes by starting directly
    at recommender).
    user_id comes from the authenticated Google user, not the request.
    """
    logger.info(
        "recommendation_service: submitting clarification",
        extra={"user_id": user_id, "thread_id": request.thread_id, "answer": request.answer},
    )

    config = {"configurable": {"thread_id": request.thread_id}}

    # Load prior state from checkpointer
    prior_checkpoint = checkpointer.get_tuple(config)
    if prior_checkpoint and prior_checkpoint.checkpoint:
        # Extract the full state from the checkpoint
        prior_state = prior_checkpoint.checkpoint.get("channel_values", {})
    else:
        logger.error("No prior checkpoint found for clarification")
        raise ValueError(f"No prior session found for thread_id {request.thread_id}")

    # Update state with clarification answer - this is the key part!
    prior_state["clarification_answer"] = request.answer

    logger.info(
        "recommendation_service: running recommender with clarification",
        extra={
            "user_id": user_id,
            "thread_id": request.thread_id,
            "clarification_answer": request.answer,
        },
    )

    # Run only the recommender node - this uses the clarification_answer from state
    recommender_output = await recommender(prior_state)

    # Update the state with recommender output
    final_state = {**prior_state, **recommender_output}
    final_state["user_id"] = user_id
    final_state["thread_id"] = request.thread_id

    logger.info(
        "recommendation_service: clarification processed",
        extra={
            "user_id": user_id,
            "thread_id": request.thread_id,
            "recommendations_count": len(final_state.get("recommendations", [])),
            "confidence_score": final_state.get("confidence_score"),
        },
    )

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

    # Save session to cross-session memory after clarification
    if user_store:
        cocktail_names = [c.name for c in final_state.get("recommendations", [])]
        user_store.save_session_recommendations(user_id, request.thread_id, cocktail_names)
        user_store.increment_session_count(user_id)

    return RecommendResponse(
        thread_id=request.thread_id,
        recommendations=recommendations,
        confidence_score=final_state.get("confidence_score", 0.0),
        rationale=final_state.get("rationale", ""),
        needs_clarification=False,  # After clarification, always provide recommendations
        clarification_question=None,
        degraded=False,
    )
