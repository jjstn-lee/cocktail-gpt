"""Router for recommendation and clarification endpoints."""

from fastapi import APIRouter, Depends
from loguru import logger

from src.api.dependencies import get_graph, get_checkpointer, get_user_store
from src.api.schemas import RecommendRequest, ClarifyRequest, RecommendResponse
from src.api.services.recommendation_service import get_recommendations, submit_clarification

router = APIRouter(tags=["recommendations"])


@router.post("/recommend", response_model=RecommendResponse)
async def recommend(
    request: RecommendRequest,
    graph=Depends(get_graph),
    checkpointer=Depends(get_checkpointer),
    user_store=Depends(get_user_store),
) -> RecommendResponse:
    """
    Generate cocktail recommendations for a user.

    If thread_id is omitted, a new session is created.
    If needs_clarification is true, call POST /clarify with the thread_id and user's answer.
    """
    logger.info("POST /recommend", extra={"user_id": request.user_id})
    return await get_recommendations(request, graph, checkpointer, user_store)


@router.post("/clarify", response_model=RecommendResponse)
async def clarify(
    request: ClarifyRequest,
    graph=Depends(get_graph),
    checkpointer=Depends(get_checkpointer),
) -> RecommendResponse:
    """
    Submit an answer to a clarification question.

    The graph resumes from its checkpoint and re-runs the recommender node
    with the new information. Always returns recommendations (never clarification).
    """
    logger.info("POST /clarify", extra={"user_id": request.user_id, "thread_id": request.thread_id})
    return await submit_clarification(request, graph, checkpointer)
