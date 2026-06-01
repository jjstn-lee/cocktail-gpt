"""Spotify token storage layer using UserStore."""

import time
from loguru import logger

from src.storage.user_store import UserStore


def get_spotify_tokens(user_store: UserStore, user_id: str) -> dict | None:
    """
    Retrieve stored Spotify tokens for a user.

    Args:
        user_store: UserStore instance
        user_id: User ID

    Returns:
        Token dict with access_token, refresh_token, expires_at, etc., or None if not connected.
    """
    data = user_store._load_user_file(user_id)
    spotify_data = data.get("spotify")
    print(f"[SPOTIFY_TOKEN_STORE] get_spotify_tokens for user {user_id}: {'FOUND' if spotify_data else 'NOT FOUND'}")
    if spotify_data:
        print(f"[SPOTIFY_TOKEN_STORE] Token has: access_token={'✓' if spotify_data.get('access_token') else '✗'}, refresh_token={'✓' if spotify_data.get('refresh_token') else '✗'}, expires_at={spotify_data.get('expires_at')}")
    return spotify_data if spotify_data else None


def save_spotify_tokens(user_store: UserStore, user_id: str, token_data: dict) -> None:
    """
    Store Spotify tokens for a user.

    Args:
        user_store: UserStore instance
        user_id: User ID
        token_data: Token dict from Spotify (access_token, refresh_token, expires_at, etc.)
    """
    data = user_store._load_user_file(user_id)
    data["spotify"] = token_data
    user_store._save_user_file(user_id, data)
    logger.info("Spotify tokens saved", extra={"user_id": user_id})


def delete_spotify_tokens(user_store: UserStore, user_id: str) -> None:
    """
    Delete stored Spotify tokens for a user (disconnect).

    Args:
        user_store: UserStore instance
        user_id: User ID
    """
    data = user_store._load_user_file(user_id)
    if "spotify" in data:
        del data["spotify"]
        user_store._save_user_file(user_id, data)
    logger.info("Spotify tokens deleted", extra={"user_id": user_id})


def is_token_expired(token_data: dict, buffer_seconds: int = 60) -> bool:
    """
    Check if a Spotify token is expired (with buffer).

    Args:
        token_data: Token dict with expires_at timestamp
        buffer_seconds: Refresh if expiring within this many seconds (default 60)

    Returns:
        True if token is expired or will expire soon.
    """
    if not token_data:
        return True
    expires_at = token_data.get("expires_at")
    if expires_at is None:
        return True
    return time.time() >= (expires_at - buffer_seconds)
