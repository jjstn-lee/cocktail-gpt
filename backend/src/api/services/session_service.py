"""Business logic for session queries."""

from loguru import logger

from src.api.schemas import SessionSummary


async def get_session_summary(user_id: str) -> SessionSummary:
    """
    Get a summary of the user's session history.

    Queries the checkpointer for all sessions by this user and aggregates stats.
    """
    logger.info("session_service: retrieving session summary", extra={"user_id": user_id})

    # In a real implementation, this would query the checkpointer for all
    # thread_ids associated with user_id and aggregate stats.
    # For now, return a placeholder.

    return SessionSummary(
        user_id=user_id,
        session_count=0,
        last_run_at=None,
        top_preferences={},
    )
