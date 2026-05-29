"""Router for session management endpoints."""

from fastapi import APIRouter
from loguru import logger

from src.api.schemas import SessionSummary
from src.api.services.session_service import get_session_summary

router = APIRouter(tags=["sessions"])


@router.get("/sessions/{user_id}", response_model=SessionSummary)
async def get_session(user_id: str) -> SessionSummary:
    """
    Get a summary of the user's session history.

    Returns session count, last run timestamp, and inferred top preferences.
    Does not run the graph.
    """
    logger.info("GET /sessions/{user_id}", extra={"user_id": user_id})
    return await get_session_summary(user_id)
