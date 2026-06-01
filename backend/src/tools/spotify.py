import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import spotipy  # type: ignore
from loguru import logger
from spotipy.exceptions import SpotifyException, SpotifyOauthError  # type: ignore

from .base import SourcePayload, SourceUnavailableError

# Configuration
SPOTIFY_CACHE_DIR = Path(os.getenv("SPOTIFY_CACHE_DIR", ".spotify_cache"))
SPOTIFY_CACHE_DIR.mkdir(exist_ok=True)

SPOTIFY_SCOPES = [
    "user-read-recently-played",
    "user-top-read",
    "user-read-playback-state",
    "playlist-read-private",
    "playlist-read-collaborative",
]


def _make_client_from_tokens(token_data: dict) -> spotipy.Spotify:
    """Build a Spotify client from stored access token.

    Args:
        token_data: Dict with 'access_token', 'refresh_token', 'expires_at', etc.

    Returns:
        Authenticated Spotify client

    Raises:
        SourceUnavailableError: If token is invalid or missing.
    """
    try:
        access_token = token_data.get("access_token")
        if not access_token:
            raise SourceUnavailableError("spotify", "No access_token in token_data")
        return spotipy.Spotify(auth=access_token)
    except Exception as e:
        raise SourceUnavailableError(
            "spotify", f"Failed to create Spotify client: {str(e)}", original=e
        )


def _fetch_recently_played(
    sp: spotipy.Spotify, limit: int = 50
) -> list[dict[str, Any]]:
    """Fetch recently played tracks."""
    results = sp.current_user_recently_played(limit=limit)
    tracks = list(results.get("items", []))
    print(f"[SPOTIFY_FETCH] _fetch_recently_played: {len(tracks)} tracks returned")
    return tracks




def _fetch_top_artists(sp: spotipy.Spotify, limit: int = 20) -> list[dict[str, Any]]:
    """Fetch top artists (medium_term: ~last 6 months)."""
    results = sp.current_user_top_artists(time_range="medium_term", limit=limit)
    artists = list(results.get("items", []))
    print(f"[SPOTIFY_FETCH] _fetch_top_artists: {len(artists)} artists returned")
    return artists


def _fetch_top_tracks(sp: spotipy.Spotify, limit: int = 20) -> list[dict[str, Any]]:
    """Fetch top tracks (medium_term: ~last 6 months)."""
    results = sp.current_user_top_tracks(time_range="medium_term", limit=limit)
    tracks = list(results.get("items", []))
    print(f"[SPOTIFY_FETCH] _fetch_top_tracks: {len(tracks)} tracks returned")
    return tracks


def _fetch_current_playback(sp: spotipy.Spotify) -> dict[str, Any] | None:
    """Fetch current playback or None if nothing is playing."""
    result = sp.current_playback()
    return result if isinstance(result, dict) or result is None else None


def _fetch_playlists(sp: spotipy.Spotify, limit: int = 20) -> list[dict[str, Any]]:
    """Fetch user's playlists."""
    results = sp.current_user_playlists(limit=limit)
    return list(results.get("items", []))






def _extract_playback_signal(playback: dict[str, Any] | None) -> dict[str, Any]:
    """Extract playback signal from current playback or None."""
    if not playback or not playback.get("item"):
        return {
            "is_active": False,
            "track_name": None,
            "artist_name": None,
            "context_type": None,
            "context_uri": None,
        }

    item = playback["item"]
    artists = item.get("artists", [])
    artist_name = artists[0].get("name") if artists else None
    context = playback.get("context", {})

    return {
        "is_active": playback.get("is_playing", False),
        "track_name": item.get("name"),
        "artist_name": artist_name,
        "context_type": context.get("type"),
        "context_uri": context.get("uri"),
    }


def _extract_playlist_signal(playlists: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract playlist signal."""
    playlist_names = [p.get("name") for p in playlists if p.get("name")]
    return {"playlist_names": playlist_names, "playlist_count": len(playlists)}


def _calculate_confidence(
    recently_played_success: bool,
    audio_features_success: bool,
    top_artists_success: bool,
    current_playback_success: bool,
    playlists_success: bool,
) -> float:
    """Calculate weighted confidence based on which endpoints succeeded.

    Confidence weights:
    - Recently played + audio features: 0.50 (halved to 0.25 if audio features fail)
    - Top artists / genres: 0.25
    - Current playback: 0.15
    - Playlists: 0.10
    """
    confidence = 0.0

    if recently_played_success:
        if audio_features_success:
            confidence += 0.50
        else:
            logger.debug(
                "Audio features failed; reducing recently_played confidence to 0.25"
            )
            confidence += 0.25
    if top_artists_success:
        confidence += 0.25
    if current_playback_success:
        confidence += 0.15
    if playlists_success:
        confidence += 0.10

    return min(confidence, 1.0)


async def fetch_spotify(user_id: str, token_data: dict) -> SourcePayload:
    """Main entry point: fetch and normalize Spotify data.

    Runs all Spotify API calls concurrently. Logs failures but continues gracefully.

    Args:
        user_id: User ID (for logging)
        token_data: Stored token dict with access_token, refresh_token, etc.

    Returns:
        SourcePayload with Spotify data

    Raises:
        SourceUnavailableError: If token is invalid or API calls fail critically
    """
    print(f"[SPOTIFY] Starting fetch_spotify for user {user_id}")
    loop = asyncio.get_event_loop()

    # Step 1: Make client from stored token
    try:
        sp = await loop.run_in_executor(None, _make_client_from_tokens, token_data)
        print(f"[SPOTIFY] ✓ Client created successfully")
    except SourceUnavailableError as e:
        print(f"[SPOTIFY] ✗ Failed to create client: {e}")
        raise

    # Step 2: Run all 5 endpoint fetches concurrently
    print(f"[SPOTIFY] Fetching from 5 endpoints...")
    logger.debug(f"Fetching Spotify data for user {user_id}")
    recently_played, top_artists, top_tracks, current_playback, playlists = await asyncio.gather(
        loop.run_in_executor(None, _fetch_recently_played, sp),
        loop.run_in_executor(None, _fetch_top_artists, sp),
        loop.run_in_executor(None, _fetch_top_tracks, sp),
        loop.run_in_executor(None, _fetch_current_playback, sp),
        loop.run_in_executor(None, _fetch_playlists, sp),
        return_exceptions=True,
    )

    # Step 3: Check for exceptions and log
    recently_played_success = not isinstance(recently_played, Exception)
    top_artists_success = not isinstance(top_artists, Exception)
    top_tracks_success = not isinstance(top_tracks, Exception)
    current_playback_success = not isinstance(current_playback, Exception)
    playlists_success = not isinstance(playlists, Exception)

    if isinstance(recently_played, Exception):
        logger.warning(f"Spotify recently_played failed: {recently_played}")
        recently_played = []
    if isinstance(top_artists, Exception):
        logger.warning(f"Spotify top_artists failed: {top_artists}")
        top_artists = []
    if isinstance(top_tracks, Exception):
        logger.warning(f"Spotify top_tracks failed: {top_tracks}")
        top_tracks = []
    if isinstance(current_playback, Exception):
        logger.warning(f"Spotify current_playback failed: {current_playback}")
        current_playback = None
    if isinstance(playlists, Exception):
        logger.warning(f"Spotify playlists failed: {playlists}")
        playlists = []

    # Step 4: Extract signals
    # Note: audio_features and genres endpoints deprecated by Spotify
    signals = {
        "top_artists": {
            "artist_count": len(top_artists),
            "artist_names": [artist.get("name") for artist in top_artists[:10]],
        },
        "top_tracks": {
            "track_count": len(top_tracks),
            "track_names": [track.get("name") for track in top_tracks[:10]],
        },
        "playback": _extract_playback_signal(current_playback),
        "playlist": _extract_playlist_signal(playlists),
        "recently_played_tracks": {
            "track_count": len(recently_played),
            "track_names": [item["track"]["name"] for item in recently_played[:10] if item.get("track")],
        },
    }

    # Step 5: Calculate confidence
    confidence = _calculate_confidence(
        recently_played_success,
        top_tracks_success,  # using top_tracks instead of audio_features
        top_artists_success,
        current_playback_success,
        playlists_success,
    )

    print(f"[SPOTIFY] ════════════════════════════════════════")
    print(f"[SPOTIFY] Fetch Results:")
    print(f"[SPOTIFY]   - recently_played: {recently_played_success} ({len(recently_played)} tracks)")
    print(f"[SPOTIFY]   - top_artists: {top_artists_success} ({len(top_artists)} artists)")
    print(f"[SPOTIFY]   - top_tracks: {top_tracks_success} ({len(top_tracks)} tracks)")
    print(f"[SPOTIFY]   - current_playback: {current_playback_success}")
    print(f"[SPOTIFY]   - playlists: {playlists_success} ({len(playlists)} playlists)")
    print(f"[SPOTIFY]   - overall_confidence: {confidence:.2f}")
    print(f"[SPOTIFY] Signal breakdown:")
    for signal_type, signal_data in signals.items():
        if signal_type == "recently_played_tracks":
            print(f"[SPOTIFY]   - {signal_type}: {signal_data['track_count']} total, showing first 10")
        else:
            print(f"[SPOTIFY]   - {signal_type}: {signal_data}")
    print(f"[SPOTIFY] ════════════════════════════════════════")

    logger.info(
        f"Spotify fetch complete for user {user_id}; confidence={confidence:.2f}, "
        f"sources=[recently_played={recently_played_success}, top_artists={top_artists_success}, "
        f"top_tracks={top_tracks_success}, playback={current_playback_success}, playlists={playlists_success}]"
    )

    return SourcePayload(
        source="spotify",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        signals=signals,
        confidence=confidence,
    )
