"""FastAPI dependency injection for graph, checkpointer, and user store."""

from fastapi import Request

from src.storage.user_store import UserStore


def get_graph(request: Request):
    """Get the compiled LangGraph from app state."""
    return request.app.state.graph


def get_checkpointer(request: Request):
    """Get the checkpointer from app state."""
    return request.app.state.checkpointer


def get_user_store(request: Request) -> UserStore:
    """Get the user store from app state."""
    return request.app.state.user_store
