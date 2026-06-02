"""Business logic for session queries."""

from loguru import logger

from src.api.schemas import SessionSummary
from src.storage.user_store import UserStore


async def get_session_summary(user_id: str, user_store: UserStore | None = None) -> SessionSummary:
    """
    Get a summary of the user's session history.

    Retrieves session count, last run timestamp, and top preferences from user_store.
    """
    logger.info("session_service: retrieving session summary", extra={"user_id": user_id})

    session_count = 0
    last_run_at = None
    top_preferences = {}

    if user_store:
        session_count = user_store.get_session_count(user_id)

        # Get last run timestamp from recommendation history
        history = user_store.load_recommendation_history(user_id)
        if history:
            last_run_at = history[-1].get("timestamp")

        # Get top preferences from stored preferences
        stored_prefs = user_store.get_preferences(user_id)
        if stored_prefs:
            top_preferences = {
                "preferred_spirits": stored_prefs.preferred_spirits,
                "preferred_flavors": stored_prefs.preferred_flavors,
                "style_preferences": stored_prefs.style_preferences,
            }

    return SessionSummary(
        user_id=user_id,
        session_count=session_count,
        last_run_at=last_run_at,
        top_preferences=top_preferences,
    )
