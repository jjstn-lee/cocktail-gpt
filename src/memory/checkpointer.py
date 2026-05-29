"""Memory persistence for agent state using LangGraph checkpointers."""

import os

from langgraph.checkpoint.memory import MemorySaver

# For now, use MemorySaver. In production, use PostgresSaver with proper database setup.
# SqliteSaver is not available in this version of langgraph.


def get_checkpointer():
    """
    Get the appropriate checkpointer based on DATABASE_URL env var.

    For this version, returns MemorySaver (in-memory, session-only).
    TODO: When upgraded to langgraph with database support, implement persistent storage.
    """
    database_url = os.getenv("DATABASE_URL", "memory://")

    # For now, always use MemorySaver
    # Production should use PostgresSaver when available
    return MemorySaver()
