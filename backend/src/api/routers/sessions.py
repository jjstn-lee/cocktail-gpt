"""Router for session management endpoints."""

from fastapi import APIRouter, Depends
from loguru import logger

from src.api.dependencies import get_current_user, get_user_store
from src.api.schemas import SessionSummary
from src.api.services.session_service import get_session_summary

router = APIRouter(tags=["sessions"], dependencies=[Depends(get_current_user)])


@router.get("/sessions", response_model=SessionSummary)
async def get_session(
    user: dict = Depends(get_current_user),
    user_store=Depends(get_user_store),
) -> SessionSummary:
    """
    Get a summary of the user's session history.

    Returns session count, last run timestamp, and inferred top preferences.
    Does not run the graph.
    """
    user_id = user["sub"]
    logger.info("GET /sessions", extra={"user_id": user_id})
    return await get_session_summary(user_id, user_store)
