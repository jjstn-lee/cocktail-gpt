"""Router for feedback submission."""

from fastapi import APIRouter, Depends
from loguru import logger

from src.api.dependencies import get_checkpointer, get_current_user
from src.api.schemas import FeedbackRequest, FeedbackResponse
from src.api.services.feedback_service import submit_feedback

router = APIRouter(tags=["feedback"], dependencies=[Depends(get_current_user)])


@router.post("/feedback", response_model=FeedbackResponse)
async def feedback(
    request: FeedbackRequest,
    user: dict = Depends(get_current_user),
    checkpointer=Depends(get_checkpointer),
) -> FeedbackResponse:
    """
    Submit feedback (thumbs up/down) on a cocktail recommendation.

    The feedback is appended to the user's session state for future personalization.
    """
    user_id = user["sub"]
    logger.info(
        "POST /feedback",
        extra={
            "user_id": user_id,
            "thread_id": request.thread_id,
            "cocktail_name": request.cocktail_name,
            "rating": request.rating,
        },
    )
    return await submit_feedback(request, user_id, checkpointer)
