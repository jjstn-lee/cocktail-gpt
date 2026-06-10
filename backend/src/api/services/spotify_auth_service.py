"""Spotify OAuth flow business logic."""

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from typing import Any

import httpx
import spotipy  # type: ignore
from loguru import logger

from src.storage.spotify_token_store import save_spotify_tokens, is_token_expired


def _encode_state_payload(user_id: str, ttl_seconds: int = 600) -> tuple[str, str]:
    """
    Generate a stateless, HMAC-signed state token.

    State format: base64url(json_payload) + "." + hex_hmac

    Args:
        user_id: User ID to encode
        ttl_seconds: Time to live for the state token (default 10 minutes)

    Returns:
        (payload_b64, state_token) where state_token is the full signed state
    """
    payload = {
        "user_id": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + ttl_seconds,
    }
    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")

    secret = os.getenv("SPOTIFY_STATE_SECRET", "default-secret-key")
    hmac_digest = hmac.new(
        secret.encode(),
        payload_b64.encode(),
        hashlib.sha256,
    ).hexdigest()

    state_token = f"{payload_b64}.{hmac_digest}"
    return payload_b64, state_token


def _verify_state_token(state: str) -> str:
    """
    Verify and extract user_id from a state token.

    Args:
        state: State token from Spotify callback

    Returns:
        user_id if valid

    Raises:
        ValueError if invalid or expired
    """
    try:
        parts = state.split(".")
        if len(parts) != 2:
            raise ValueError("Invalid state format (expected 2 parts)")

        payload_b64, provided_hmac = parts
        print(f"[STATE_VERIFY] Payload (first 30 chars): {payload_b64[:30]}...")
        print(f"[STATE_VERIFY] HMAC (first 20 chars): {provided_hmac[:20]}...")

        # Verify HMAC
        secret = os.getenv("SPOTIFY_STATE_SECRET", "default-secret-key")
        expected_hmac = hmac.new(
            secret.encode(),
            payload_b64.encode(),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(provided_hmac, expected_hmac):
            print(f"[STATE_VERIFY] ✗ HMAC mismatch!")
            print(f"[STATE_VERIFY]   Expected: {expected_hmac[:20]}...")
            print(f"[STATE_VERIFY]   Got:      {provided_hmac[:20]}...")
            raise ValueError("Invalid state signature")

        print(f"[STATE_VERIFY] ✓ HMAC verified")

        # Decode payload
        try:
            payload_json = base64.urlsafe_b64decode(payload_b64 + "==").decode()
            payload = json.loads(payload_json)
            print(f"[STATE_VERIFY] ✓ Payload decoded: user_id={payload.get('user_id')}")
        except Exception as e:
            print(f"[STATE_VERIFY] ✗ Failed to decode payload: {e}")
            raise ValueError(f"Failed to decode payload: {str(e)}")

        # Check expiry
        now = int(time.time())
        exp = payload.get("exp", 0)
        if now > exp:
            print(f"[STATE_VERIFY] ✗ Token expired! Now={now}, Exp={exp}, Diff={now-exp}s")
            raise ValueError(f"State token expired (expired {now-exp} seconds ago)")

        print(f"[STATE_VERIFY] ✓ Token valid (expires in {exp-now}s)")
        return payload["user_id"]
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        logger.warning(f"_verify_state_token failed: {e}")
        raise ValueError(f"Invalid or expired state: {str(e)}")


def generate_spotify_connect_url(user_id: str) -> str:
    """
    Generate a Spotify authorization URL with signed state.

    Args:
        user_id: User ID to embed in state

    Returns:
        Spotify authorization URL
    """
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8000/api/spotify/callback")

    if not client_id:
        raise ValueError("SPOTIFY_CLIENT_ID not configured")

    _, state = _encode_state_payload(user_id)

    scopes = [
        "user-read-recently-played",
        "user-top-read",
        "user-read-playback-state",
        "playlist-read-private",
        "playlist-read-collaborative",
    ]

    auth = spotipy.SpotifyOAuth(
        client_id=client_id,
        client_secret=os.getenv("SPOTIFY_CLIENT_SECRET", ""),
        redirect_uri=redirect_uri,
        scope=scopes,
        open_browser=False,
    )

    # Use SpotifyOAuth to build the URL, but pass our custom state
    url = auth.get_authorize_url(state=state)
    logger.debug(f"generate_spotify_connect_url: generated URL for user {user_id}")
    return url


def validate_state_token(state: str) -> str:
    """
    Validate state token and return user_id.

    Args:
        state: State from Spotify callback

    Returns:
        user_id

    Raises:
        ValueError if invalid
    """
    return _verify_state_token(state)


async def exchange_code_for_tokens(code: str, state: str) -> dict[str, Any]:
    """
    Exchange authorization code for access token.

    Args:
        code: Authorization code from Spotify callback
        state: State token (used only for validation in this function, not for exchange)

    Returns:
        Token dict with access_token, refresh_token, expires_at, etc.

    Raises:
        ValueError if exchange fails
    """
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8000/api/spotify/callback")

    if not client_id or not client_secret:
        raise ValueError("SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET not configured")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://accounts.spotify.com/api/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                timeout=10,
            )

            if response.status_code != 200:
                logger.error(
                    f"Spotify token exchange failed: {response.status_code}",
                    extra={"response": response.text},
                )
                raise ValueError(f"Token exchange failed: {response.status_code}")

            token_data = response.json()

            # Convert expires_in (seconds) to expires_at (unix timestamp)
            expires_in = token_data.get("expires_in", 3600)
            token_data["expires_at"] = int(time.time()) + expires_in
            token_data["connected_at"] = datetime.now(timezone.utc).isoformat()

            access_token = token_data.get('access_token', '')
            refresh_token = token_data.get('refresh_token', '')

            print(f"[SPOTIFY_AUTH] Token exchanged:")
            print(f"[SPOTIFY_AUTH]   - access_token: {access_token}")
            print(f"[SPOTIFY_AUTH]   - refresh_token: {refresh_token}")
            print(f"[SPOTIFY_AUTH]   - token_type: {token_data.get('token_type')}")
            print(f"[SPOTIFY_AUTH]   - expires_in: {expires_in}s")
            print(f"[SPOTIFY_AUTH]   - scope: {token_data.get('scope')}")

            logger.info("Spotify token exchanged successfully")
            return token_data
    except httpx.RequestError as e:
        logger.error(f"Spotify token exchange request failed: {e}")
        raise ValueError(f"Token exchange request failed: {str(e)}")


async def refresh_spotify_token(refresh_token: str) -> dict[str, Any]:
    """
    Refresh an expired Spotify access token.

    Args:
        refresh_token: Refresh token from previous authentication

    Returns:
        New token dict with access_token, expires_at, etc.

    Raises:
        ValueError if refresh fails
    """
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError("SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET not configured")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://accounts.spotify.com/api/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
                timeout=10,
            )

            if response.status_code != 200:
                logger.error(
                    f"Spotify token refresh failed: {response.status_code}",
                    extra={"response": response.text},
                )
                raise ValueError(f"Token refresh failed: {response.status_code}")

            token_data = response.json()

            # Update expires_at
            expires_in = token_data.get("expires_in", 3600)
            token_data["expires_at"] = int(time.time()) + expires_in

            logger.info("Spotify token refreshed successfully")
            return token_data
    except httpx.RequestError as e:
        logger.error(f"Spotify token refresh request failed: {e}")
        raise ValueError(f"Token refresh request failed: {str(e)}")
