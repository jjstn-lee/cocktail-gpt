"""Router for conversational chat with intent routing."""

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from loguru import logger

from src.api.dependencies import (
    get_graph,
    get_checkpointer,
    get_user_store,
    get_current_user,
)
from src.api.schemas import ChatRequest
from src.api.services.chat_service import stream_chat

router = APIRouter(tags=["chat"], dependencies=[Depends(get_current_user)])


@router.post("/chat")
async def chat(
    request: ChatRequest,
    user: dict = Depends(get_current_user),
    graph=Depends(get_graph),
    checkpointer=Depends(get_checkpointer),
    user_store=Depends(get_user_store),
):
    """
    Send a message to the agent for conversational interaction with streaming status updates.

    The supervisor will classify the intent based on your message:
    - If you ask for a recommendation, you'll get cocktails
    - If you update your profile (e.g., "I like gin"), your profile will be updated

    Streams intermediate status messages followed by the final response.
    Each line is line-delimited JSON: {"type": "status"/"response", ...}

    If thread_id is omitted, a new session is created.
    """
    user_id = user["sub"]
    logger.info("POST /chat", extra={"user_id": user_id})

    return StreamingResponse(
        stream_chat(request, user_id, graph, checkpointer, user_store),
        media_type="application/x-ndjson",
    )
