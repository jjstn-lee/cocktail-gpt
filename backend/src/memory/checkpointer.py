"""Memory persistence for agent state using LangGraph checkpointers."""

import os

from langgraph.checkpoint.memory import MemorySaver
from loguru import logger


def get_checkpointer():
    """
    Get the appropriate checkpointer for within-session state persistence.

    Uses MemorySaver for within-session checkpoints (per-thread state across turns).
    Cross-session memory (feedback, recommendations, session_count) is persisted via user_store JSON files.

    For production with multi-process deployments, consider upgrading to langgraph version
    with SqliteSaver or PostgresSaver support.
    """
    database_url = os.getenv("DATABASE_URL", "memory://")
    logger.info("Initializing MemorySaver for within-session state checkpointing", extra={"database_url": database_url})

    # Within-session state uses MemorySaver; cross-session memory via user_store
    return MemorySaver()
