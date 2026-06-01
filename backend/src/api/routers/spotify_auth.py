"""Spotify OAuth endpoints."""

import os
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from loguru import logger

from src.api.dependencies import get_current_user, get_user_store
from src.api.schemas import SpotifyStatusResponse
from src.api.services.spotify_auth_service import (
    generate_spotify_connect_url,
    validate_state_token,
    exchange_code_for_tokens,
)
from src.storage.spotify_token_store import (
    get_spotify_tokens,
    delete_spotify_tokens,
    save_spotify_tokens,
)
from src.storage.user_store import UserStore


router = APIRouter(tags=["spotify"])


@router.get("/api/spotify/connect-url")
async def get_spotify_connect_url(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Generate a Spotify OAuth authorization URL.

    Returns:
        JSON with "url" field containing the Spotify auth URL
    """
    user_id = current_user["sub"]
    try:
        url = generate_spotify_connect_url(user_id)
        logger.debug(f"Generated Spotify connect URL for user {user_id}")
        return {"url": url}
    except Exception as e:
        logger.error(f"Failed to generate Spotify connect URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate auth URL")


@router.get("/api/spotify/callback")
async def spotify_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    user_store: UserStore = Depends(get_user_store),
) -> RedirectResponse:
    """
    Handle Spotify OAuth callback.

    No auth required (browser redirect from Spotify).

    Args:
        code: Authorization code from Spotify
        state: State token (HMAC-signed, contains user_id)
        error: Error from Spotify if auth failed
        user_store: UserStore for token persistence

    Returns:
        RedirectResponse to frontend callback page with status parameter
    """
    frontend_redirect = os.getenv(
        "SPOTIFY_FRONTEND_REDIRECT_URL", "http://localhost:3000/spotify-callback"
    )

    if error:
        logger.warning(f"Spotify callback received error: {error}")
        return RedirectResponse(
            url=f"{frontend_redirect}?status=error&reason={error}",
            status_code=302,
        )

    if not code or not state:
        logger.warning("Spotify callback missing code or state")
        return RedirectResponse(
            url=f"{frontend_redirect}?status=error&reason=missing_code_or_state",
            status_code=302,
        )

    try:
        # Validate state and extract user_id
        user_id = validate_state_token(state)
        print(f"[SPOTIFY_CALLBACK] ✓ State validated, user_id={user_id}")

        # Exchange code for tokens
        token_data = await exchange_code_for_tokens(code, state)
        print(f"[SPOTIFY_CALLBACK] ✓ Token exchanged successfully")

        # Save tokens
        save_spotify_tokens(user_store, user_id, token_data)
        print(f"[SPOTIFY_CALLBACK] ✓ Tokens saved to UserStore")

        logger.info(f"Spotify OAuth completed for user {user_id}")

        redirect_url = f"{frontend_redirect}?status=success"
        print(f"[SPOTIFY_CALLBACK] ✓ Redirecting to: {redirect_url}")
        return RedirectResponse(
            url=redirect_url,
            status_code=302,
        )
    except ValueError as e:
        logger.warning(f"Spotify callback validation failed: {e}")
        return RedirectResponse(
            url=f"{frontend_redirect}?status=error&reason=invalid_state",
            status_code=302,
        )
    except Exception as e:
        logger.error(f"Spotify callback error: {e}")
        return RedirectResponse(
            url=f"{frontend_redirect}?status=error&reason=unknown",
            status_code=302,
        )


@router.get("/api/spotify/status")
async def get_spotify_status(
    current_user: dict = Depends(get_current_user),
    user_store: UserStore = Depends(get_user_store),
) -> SpotifyStatusResponse:
    """
    Get Spotify connection status for the current user.

    Returns:
        SpotifyStatusResponse with connected status and metadata
    """
    user_id = current_user["sub"]
    token_data = get_spotify_tokens(user_store, user_id)

    if not token_data:
        return SpotifyStatusResponse(connected=False)

    # Extract scopes if available
    scopes = token_data.get("scope", "").split() if token_data.get("scope") else []

    return SpotifyStatusResponse(
        connected=True,
        connected_at=token_data.get("connected_at"),
        scopes=scopes,
    )


@router.delete("/api/spotify/disconnect")
async def disconnect_spotify(
    current_user: dict = Depends(get_current_user),
    user_store: UserStore = Depends(get_user_store),
) -> dict:
    """
    Disconnect Spotify account (delete stored tokens).

    Returns:
        JSON with "disconnected": true
    """
    user_id = current_user["sub"]
    delete_spotify_tokens(user_store, user_id)
    logger.info(f"Spotify disconnected for user {user_id}")
    return {"disconnected": True}
