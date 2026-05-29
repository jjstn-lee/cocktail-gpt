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


def _make_client(user_id: str) -> spotipy.Spotify:
    """Build a per-user Spotify client with cached OAuth token.

    Raises:
        SourceUnavailableError: If OAuth fails or env vars are missing.
    """
    try:
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        redirect_uri = os.getenv(
            "SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback"
        )

        if not client_id or not client_secret:
            raise SourceUnavailableError(
                "spotify",
                "Missing SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET",
            )

        cache_path = SPOTIFY_CACHE_DIR / f".spotify_cache_{user_id}"
        auth = spotipy.SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=SPOTIFY_SCOPES,
            cache_path=str(cache_path),
            open_browser=False,
        )
        return spotipy.Spotify(auth_manager=auth)
    except SpotifyOauthError as e:
        raise SourceUnavailableError(
            "spotify", f"OAuth initialization failed: {str(e)}", original=e
        )


def _fetch_recently_played(
    sp: spotipy.Spotify, limit: int = 50
) -> list[dict[str, Any]]:
    """Fetch recently played tracks."""
    results = sp.current_user_recently_played(limit=limit)
    return list(results.get("items", []))


def _fetch_audio_features(
    sp: spotipy.Spotify, track_ids: list[str]
) -> list[dict[str, Any] | None]:
    """Fetch audio features for track IDs. Returns None entries for unresolvable IDs."""
    if not track_ids:
        return []
    # Spotipy's audio_features batches internally (max 100 per call)
    return list(sp.audio_features(*track_ids))


def _fetch_top_artists(sp: spotipy.Spotify, limit: int = 20) -> list[dict[str, Any]]:
    """Fetch top artists (short_term)."""
    results = sp.current_user_top_artists(time_range="short_term", limit=limit)
    return list(results.get("items", []))


def _fetch_current_playback(sp: spotipy.Spotify) -> dict[str, Any] | None:
    """Fetch current playback or None if nothing is playing."""
    result = sp.current_playback()
    return result if isinstance(result, dict) or result is None else None


def _fetch_playlists(sp: spotipy.Spotify, limit: int = 20) -> list[dict[str, Any]]:
    """Fetch user's playlists."""
    results = sp.current_user_playlists(limit=limit)
    return list(results.get("items", []))


def _extract_audio_signal(
    recently_played: list[dict[str, Any]], audio_features: list[dict[str, Any] | None]
) -> dict[str, Any]:
    """Extract aggregated audio signal from recently played and audio features.

    Uses decay weighting — recent tracks weighted more.
    """
    if not audio_features:
        return {
            "avg_energy": 0.0,
            "avg_valence": 0.0,
            "avg_danceability": 0.0,
            "avg_tempo": 0.0,
            "avg_acousticness": 0.0,
            "avg_instrumentalness": 0.0,
            "track_count": 0,
        }

    # Filter out None entries
    valid_features = [f for f in audio_features if f is not None]
    if not valid_features:
        return {
            "avg_energy": 0.0,
            "avg_valence": 0.0,
            "avg_danceability": 0.0,
            "avg_tempo": 0.0,
            "avg_acousticness": 0.0,
            "avg_instrumentalness": 0.0,
            "track_count": 0,
        }

    n = len(valid_features)
    # Linear decay: most recent (index 0) gets weight n/n, oldest gets 1/n
    weights = [(n - i) / n for i in range(n)]

    total_weight = sum(weights)
    weighted_energy = sum(
        f.get("energy", 0) * w for f, w in zip(valid_features, weights)
    )
    weighted_valence = sum(
        f.get("valence", 0) * w for f, w in zip(valid_features, weights)
    )
    weighted_danceability = sum(
        f.get("danceability", 0) * w for f, w in zip(valid_features, weights)
    )
    weighted_tempo = sum(f.get("tempo", 0) * w for f, w in zip(valid_features, weights))
    weighted_acousticness = sum(
        f.get("acousticness", 0) * w for f, w in zip(valid_features, weights)
    )
    weighted_instrumentalness = sum(
        f.get("instrumentalness", 0) * w for f, w in zip(valid_features, weights)
    )

    return {
        "avg_energy": weighted_energy / total_weight,
        "avg_valence": weighted_valence / total_weight,
        "avg_danceability": weighted_danceability / total_weight,
        "avg_tempo": weighted_tempo / total_weight,
        "avg_acousticness": weighted_acousticness / total_weight,
        "avg_instrumentalness": weighted_instrumentalness / total_weight,
        "track_count": len(recently_played),
    }


def _extract_genre_signal(top_artists: list[dict[str, Any]]) -> dict[str, Any]:
    """Extract genre signal from top artists."""
    genre_freq: dict[str, int] = {}
    for artist in top_artists:
        for genre in artist.get("genres", []):
            genre_freq[genre] = genre_freq.get(genre, 0) + 1

    # Sort by frequency, take top 10
    sorted_genres = sorted(genre_freq.items(), key=lambda x: x[1], reverse=True)
    top_genres = [genre for genre, _ in sorted_genres[:10]]

    return {"top_genres": top_genres, "artist_count": len(top_artists)}


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


async def fetch_spotify(user_id: str) -> SourcePayload:
    """Main entry point: fetch and normalize Spotify data.

    Runs all Spotify API calls concurrently. Logs failures but continues gracefully.
    """
    loop = asyncio.get_event_loop()

    # Step 1: Make client
    try:
        sp = await loop.run_in_executor(None, _make_client, user_id)
    except SourceUnavailableError:
        raise

    # Step 2: Run all 4 endpoint fetches concurrently
    logger.debug(f"Fetching Spotify data for user {user_id}")
    recently_played, top_artists, current_playback, playlists = await asyncio.gather(
        loop.run_in_executor(None, _fetch_recently_played, sp),
        loop.run_in_executor(None, _fetch_top_artists, sp),
        loop.run_in_executor(None, _fetch_current_playback, sp),
        loop.run_in_executor(None, _fetch_playlists, sp),
        return_exceptions=True,
    )

    # Step 3: Check for exceptions and log
    recently_played_success = not isinstance(recently_played, Exception)
    top_artists_success = not isinstance(top_artists, Exception)
    current_playback_success = not isinstance(current_playback, Exception)
    playlists_success = not isinstance(playlists, Exception)

    if isinstance(recently_played, Exception):
        logger.warning(f"Spotify recently_played failed: {recently_played}")
        recently_played = []
    if isinstance(top_artists, Exception):
        logger.warning(f"Spotify top_artists failed: {top_artists}")
        top_artists = []
    if isinstance(current_playback, Exception):
        logger.warning(f"Spotify current_playback failed: {current_playback}")
        current_playback = None
    if isinstance(playlists, Exception):
        logger.warning(f"Spotify playlists failed: {playlists}")
        playlists = []

    # Step 4: Fetch audio features if recently_played succeeded
    audio_features_success = False
    audio_features = []
    if recently_played_success:
        track_ids = [
            item["track"]["id"] for item in recently_played if item.get("track")
        ]
        try:
            audio_features = await loop.run_in_executor(
                None, _fetch_audio_features, sp, track_ids
            )
            audio_features_success = True
            logger.debug(f"Fetched audio features for {len(audio_features)} tracks")
        except SpotifyException as e:
            logger.warning(f"Spotify audio_features failed: {e}")
            audio_features = []

    # Step 5: Extract signals
    signals = {
        "audio": _extract_audio_signal(recently_played, audio_features),
        "genre": _extract_genre_signal(top_artists),
        "playback": _extract_playback_signal(current_playback),
        "playlist": _extract_playlist_signal(playlists),
    }

    # Step 6: Calculate confidence
    confidence = _calculate_confidence(
        recently_played_success,
        audio_features_success,
        top_artists_success,
        current_playback_success,
        playlists_success,
    )

    logger.info(
        f"Spotify fetch complete for user {user_id}; confidence={confidence:.2f}, "
        f"sources=[recently_played={recently_played_success}, audio_features={audio_features_success}, "
        f"top_artists={top_artists_success}, playback={current_playback_success}, playlists={playlists_success}]"
    )

    return SourcePayload(
        source="spotify",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        signals=signals,
        confidence=confidence,
    )
