"""Router for conversational chat with intent routing."""

from fastapi import APIRouter, Depends
from loguru import logger

from src.api.dependencies import (
    get_graph,
    get_checkpointer,
    get_user_store,
    get_current_user,
)
from src.api.schemas import ChatRequest, ChatResponse
from src.api.services.chat_service import handle_chat

router = APIRouter(tags=["chat"], dependencies=[Depends(get_current_user)])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: dict = Depends(get_current_user),
    graph=Depends(get_graph),
    checkpointer=Depends(get_checkpointer),
    user_store=Depends(get_user_store),
) -> ChatResponse:
    """
    Send a message to the agent for conversational interaction.

    The supervisor will classify the intent based on your message:
    - If you ask for a recommendation, you'll get cocktails
    - If you update your profile (e.g., "I like gin"), your profile will be updated

    If thread_id is omitted, a new session is created.
    """
    user_id = user["sub"]
    logger.info("POST /chat", extra={"user_id": user_id})
    return await handle_chat(request, user_id, graph, checkpointer, user_store)
