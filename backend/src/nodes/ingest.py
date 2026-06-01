"""Ingestion node: parallel collection of data from all sources."""

import asyncio
import time
from typing import Any

from loguru import logger

from src.state import AgentState
from src.storage.spotify_token_store import (
    get_spotify_tokens,
    is_token_expired,
    save_spotify_tokens,
)
from src.tools.base import SourcePayload, SourceUnavailableError
from src.tools.spotify import fetch_spotify
from src.tools.weather import fetch_weather


def make_ingest_node(user_store=None):
    """Factory function to create an ingest node with optional user_store for Spotify.

    Args:
        user_store: Optional UserStore instance for Spotify token management

    Returns:
        Async ingest node function
    """

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

        # Build tasks list starting with weather
        tasks = [fetch_weather(user_id)]

        # Add Spotify if user_store is available and user has connected their account
        spotify_token_data = None
        if user_store:
            print(f"[INGEST] Checking Spotify tokens for user {user_id}...")
            spotify_token_data = get_spotify_tokens(user_store, user_id)
            if spotify_token_data:
                print(f"[INGEST] ✓ Spotify tokens found for user {user_id}")
                # Check if token is expired and refresh if needed
                if is_token_expired(spotify_token_data):
                    print(f"[INGEST] ⚠ Spotify token expired, attempting refresh...")
                    logger.debug(f"Spotify token expired for user {user_id}, attempting refresh")
                    try:
                        from src.api.services.spotify_auth_service import refresh_spotify_token

                        refresh_token = spotify_token_data.get("refresh_token")
                        if refresh_token:
                            new_token_data = await refresh_spotify_token(refresh_token)
                            # Preserve original fields and merge new ones
                            new_token_data["refresh_token"] = refresh_token
                            new_token_data["scope"] = spotify_token_data.get("scope")
                            new_token_data["connected_at"] = spotify_token_data.get("connected_at")
                            save_spotify_tokens(user_store, user_id, new_token_data)
                            spotify_token_data = new_token_data
                            print(f"[INGEST] ✓ Spotify token refreshed successfully")
                            logger.info(f"Spotify token refreshed for user {user_id}")
                        else:
                            print(f"[INGEST] ✗ No refresh_token available")
                            logger.warning(f"No refresh_token available for user {user_id}")
                            spotify_token_data = None
                    except Exception as e:
                        print(f"[INGEST] ✗ Token refresh failed: {e}")
                        logger.warning(
                            f"Spotify token refresh failed for user {user_id}: {e}; skipping Spotify"
                        )
                        spotify_token_data = None
                else:
                    print(f"[INGEST] ✓ Spotify token is valid (not expired)")

                if spotify_token_data:
                    print(f"[INGEST] ✓ Adding Spotify to fetch tasks")
                    tasks.append(fetch_spotify(user_id, spotify_token_data))
            else:
                print(f"[INGEST] ✗ No Spotify tokens found for user {user_id} (account not connected?)")

        # Gather all source fetches concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

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

        print(f"[INGEST] ════════════════════════════════════════")
        print(f"[INGEST] FINAL SOURCES: {list(raw_sources.keys())}")
        for source_name, payload in raw_sources.items():
            confidence = payload.get("confidence", 0.0)
            signals = payload.get("signals", {})
            print(f"[INGEST]   - {source_name}: confidence={confidence:.2f}, signal_keys={list(signals.keys())}")
        print(f"[INGEST] ════════════════════════════════════════")
        logger.info(f"Ingestion complete; sources available: {list(raw_sources.keys())}")

        return {"raw_sources": raw_sources}

    return ingest_node
