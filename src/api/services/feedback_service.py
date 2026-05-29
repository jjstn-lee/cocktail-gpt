"""Business logic for feedback submission."""

from loguru import logger

from src.memory.checkpointer import Checkpointer
from src.state import Feedback
from src.api.schemas import FeedbackRequest, FeedbackResponse


async def submit_feedback(
    request: FeedbackRequest,
    checkpointer: Checkpointer,
) -> FeedbackResponse:
    """
    Submit feedback on a cocktail recommendation.

    Append the feedback to the session state for future personalization.
    """
    logger.info(
        "feedback_service: submitting feedback",
        extra={
            "user_id": request.user_id,
            "thread_id": request.thread_id,
            "cocktail_name": request.cocktail_name,
            "rating": request.rating,
        },
    )

    # In a real implementation, this would:
    # 1. Load the prior state from checkpointer using thread_id
    # 2. Append feedback to the feedback list
    # 3. Save back to checkpointer
    # For now, we log and return success

    return FeedbackResponse(accepted=True)
