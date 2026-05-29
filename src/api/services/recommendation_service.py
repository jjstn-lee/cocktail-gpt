"""Business logic for recommendations and clarifications."""

import uuid
from loguru import logger

from src.graph import CompiledGraph
from src.memory.checkpointer import Checkpointer
from src.state import AgentState
from src.api.schemas import RecommendRequest, ClarifyRequest, RecommendResponse, CocktailOut


async def get_recommendations(
    request: RecommendRequest,
    graph: CompiledGraph,
    checkpointer: Checkpointer,
) -> RecommendResponse:
    """
    Run the graph to generate recommendations for a user.

    If thread_id is None, generate a new one. Pass to graph.ainvoke() with config.
    """
    thread_id = request.thread_id or str(uuid.uuid4())
    logger.info(
        "recommendation_service: generating recommendations",
        extra={"user_id": request.user_id, "thread_id": thread_id},
    )

    # Build initial state
    state: AgentState = {
        "user_id": request.user_id,
        "thread_id": thread_id,
        "raw_sources": {},
        "recommendations": [],
        "confidence_score": 0.0,
        "clarification_question": None,
        "clarification_answer": None,
        "session_count": 0,
        "session_clarification_used": False,
        "feedback": [],
    }

    # Run the graph with persistence
    config = {"configurable": {"thread_id": thread_id}}
    final_state = await graph.ainvoke(state, config=config)

    logger.info(
        "recommendation_service: recommendations complete",
        extra={
            "user_id": request.user_id,
            "thread_id": thread_id,
            "recommendations_count": len(final_state.get("recommendations", [])),
            "confidence_score": final_state.get("confidence_score", 0.0),
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

    needs_clarification = final_state.get("clarification_question") is not None

    return RecommendResponse(
        thread_id=thread_id,
        recommendations=recommendations,
        confidence_score=final_state.get("confidence_score", 0.0),
        rationale=final_state.get("rationale", ""),
        needs_clarification=needs_clarification,
        clarification_question=final_state.get("clarification_question"),
        degraded=False,  # TODO: detect source failures
    )


async def submit_clarification(
    request: ClarifyRequest,
    graph: CompiledGraph,
    checkpointer: Checkpointer,
) -> RecommendResponse:
    """
    Submit a clarification answer and re-run the recommender node.

    Load the prior state from the checkpointer, update with clarification_answer,
    and resume the graph from the recommender node.
    """
    logger.info(
        "recommendation_service: submitting clarification",
        extra={"user_id": request.user_id, "thread_id": request.thread_id, "answer": request.answer},
    )

    # Query the checkpointer for the prior state
    # (This is a simplified approach; LangGraph's checkpointer API may vary)
    config = {"configurable": {"thread_id": request.thread_id}}

    # Resume the graph with the clarification answer
    state_update = {
        "user_id": request.user_id,
        "thread_id": request.thread_id,
        "clarification_answer": request.answer,
    }

    final_state = await graph.ainvoke(state_update, config=config)

    logger.info(
        "recommendation_service: clarification processed",
        extra={
            "user_id": request.user_id,
            "thread_id": request.thread_id,
            "recommendations_count": len(final_state.get("recommendations", [])),
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

    return RecommendResponse(
        thread_id=request.thread_id,
        recommendations=recommendations,
        confidence_score=final_state.get("confidence_score", 0.0),
        rationale=final_state.get("rationale", ""),
        needs_clarification=False,  # After clarification, always provide recommendations
        clarification_question=None,
        degraded=False,
    )
