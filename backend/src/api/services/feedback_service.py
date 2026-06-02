"""Business logic for feedback submission."""

from typing import Any
from datetime import datetime
from loguru import logger

from src.state import Feedback
from src.api.schemas import FeedbackRequest, FeedbackResponse
from src.storage.user_store import UserStore


async def submit_feedback(
    request: FeedbackRequest,
    user_id: str,
    checkpointer: Any,
    user_store: UserStore | None = None,
) -> FeedbackResponse:
    """
    Submit feedback on a cocktail recommendation.

    Append the feedback to the session state for future personalization.
    Persist to cross-session memory via user_store.
    user_id comes from the authenticated Google user, not the request.
    """
    logger.info(
        "feedback_service: submitting feedback",
        extra={
            "user_id": user_id,
            "thread_id": request.thread_id,
            "cocktail_name": request.cocktail_name,
            "rating": request.rating,
        },
    )

    # Convert rating string ("up"/"down") to feedback rating (5/1)
    rating_value = 5 if request.rating == "up" else 1

    feedback_entry = {
        "cocktail_name": request.cocktail_name,
        "session_id": request.thread_id,
        "rating": rating_value,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    # Save to cross-session memory if user_store is provided
    if user_store:
        user_store.save_feedback(user_id, feedback_entry)
        logger.debug("Feedback persisted to user_store", extra={"user_id": user_id})

    return FeedbackResponse(accepted=True)
