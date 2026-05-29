"""Ingestion node: parallel collection of data from all sources."""

import asyncio
from typing import Any

from loguru import logger

from src.state import AgentState
from src.tools.base import SourcePayload, SourceUnavailableError
from src.tools.weather import fetch_weather


async def ingest_node(state: AgentState) -> dict[str, Any]:
    """Ingest data from all sources concurrently.

    Runs all source fetches in parallel. If a source fails, logs the error and
    continues gracefully. The agent should degrade gracefully, not crash.

    Args:
        state: The current agent state.

    Returns:
        A dict with "raw_sources" containing normalized payloads keyed by source name.
    """
    user_id: str = state.get("user_id", "")
    if not user_id:
        raise ValueError("user_id is required in state")
    logger.info(f"Ingesting data for user {user_id}")

    # Gather all source fetches concurrently
    # For now, only weather is active. Spotify, Gmail, and calendar are TBD.
    results = await asyncio.gather(
        fetch_weather(user_id),
        # fetch_spotify(user_id),    # TODO: re-enable when OAuth can run non-interactively
        # fetch_gmail(user_id),      # TODO: implement
        # fetch_calendar(user_id),   # TODO: implement
        return_exceptions=True,
    )

    raw_sources: dict[str, Any] = {}

    # Process results, handling exceptions gracefully
    for result in results:
        if isinstance(result, Exception):
            if isinstance(result, SourceUnavailableError):
                logger.warning(f"Source unavailable: {result}")
            else:
                logger.warning(f"Ingestion failed: {type(result).__name__}: {result}")
            # Continue without re-raising
        else:
            # result is a SourcePayload (dict-like)
            payload: Any = result
            source_name: str = payload.get("source", "unknown")
            raw_sources[source_name] = payload
            logger.debug(f"Stored {source_name} data")

    logger.info(f"Ingestion complete; sources available: {list(raw_sources.keys())}")

    return {"raw_sources": raw_sources}
