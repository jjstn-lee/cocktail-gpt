"""Router for feedback submission."""

from fastapi import APIRouter, Depends
from loguru import logger

from src.api.dependencies import get_checkpointer
from src.api.schemas import FeedbackRequest, FeedbackResponse
from src.api.services.feedback_service import submit_feedback

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
async def feedback(
    request: FeedbackRequest,
    checkpointer=Depends(get_checkpointer),
) -> FeedbackResponse:
    """
    Submit feedback (thumbs up/down) on a cocktail recommendation.

    The feedback is appended to the user's session state for future personalization.
    """
    logger.info(
        "POST /feedback",
        extra={
            "user_id": request.user_id,
            "thread_id": request.thread_id,
            "cocktail_name": request.cocktail_name,
            "rating": request.rating,
        },
    )
    return await submit_feedback(request, checkpointer)
