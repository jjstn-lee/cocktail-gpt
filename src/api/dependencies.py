"""FastAPI dependency injection for graph and checkpointer."""

from fastapi import Request


def get_graph(request: Request):
    """Get the compiled LangGraph from app state."""
    return request.app.state.graph


def get_checkpointer(request: Request):
    """Get the checkpointer from app state."""
    return request.app.state.checkpointer
