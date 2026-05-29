import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.tools.base import SourceUnavailableError
from src.tools.spotify import (
    _calculate_confidence,
    _extract_audio_signal,
    _extract_genre_signal,
    _extract_playback_signal,
    _extract_playlist_signal,
    fetch_spotify,
)


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to fixtures directory."""
    return Path(__file__).parent / "fixtures" / "spotify"


@pytest.fixture
def recently_played_fixture(fixtures_dir: Path) -> list[dict[str, Any]]:
    """Load recently_played fixture."""
    with open(fixtures_dir / "recently_played.json") as f:
        return json.load(f)["items"]


@pytest.fixture
def audio_features_fixture(fixtures_dir: Path) -> list[dict[str, Any]]:
    """Load audio_features fixture."""
    with open(fixtures_dir / "audio_features.json") as f:
        return json.load(f)


@pytest.fixture
def top_artists_fixture(fixtures_dir: Path) -> list[dict[str, Any]]:
    """Load top_artists fixture."""
    with open(fixtures_dir / "top_artists.json") as f:
        return json.load(f)["items"]


@pytest.fixture
def current_playback_fixture(fixtures_dir: Path) -> dict[str, Any]:
    """Load current_playback fixture."""
    with open(fixtures_dir / "current_playback.json") as f:
        return json.load(f)


@pytest.fixture
def current_playback_none_fixture(fixtures_dir: Path) -> dict[str, Any]:
    """Load current_playback_none fixture."""
    with open(fixtures_dir / "current_playback_none.json") as f:
        return json.load(f)


@pytest.fixture
def playlists_fixture(fixtures_dir: Path) -> list[dict[str, Any]]:
    """Load playlists fixture."""
    with open(fixtures_dir / "playlists.json") as f:
        return json.load(f)["items"]


# Unit tests for signal extractors


def test_extract_audio_signal_happy_path(
    recently_played_fixture, audio_features_fixture
) -> None:
    """Test audio signal extraction with valid data."""
    signal = _extract_audio_signal(recently_played_fixture, audio_features_fixture)

    assert "avg_energy" in signal
    assert "avg_valence" in signal
    assert "avg_danceability" in signal
    assert "avg_tempo" in signal
    assert "avg_acousticness" in signal
    assert "avg_instrumentalness" in signal
    assert signal["track_count"] == 3
    assert 0 <= signal["avg_energy"] <= 1
    assert 0 <= signal["avg_valence"] <= 1
    assert 0 <= signal["avg_danceability"] <= 1
    assert signal["avg_tempo"] > 0


def test_extract_audio_signal_empty() -> None:
    """Test audio signal extraction with empty data."""
    signal = _extract_audio_signal([], [])

    assert signal["avg_energy"] == 0.0
    assert signal["avg_valence"] == 0.0
    assert signal["avg_danceability"] == 0.0
    assert signal["avg_tempo"] == 0.0
    assert signal["track_count"] == 0


def test_extract_audio_signal_with_none_entries(audio_features_fixture) -> None:
    """Test audio signal extraction when audio_features contains None entries."""
    features_with_nones = [audio_features_fixture[0], None, audio_features_fixture[2]]
    recently_played = [{"track": {"id": f"track_{i}"}} for i in range(3)]

    signal = _extract_audio_signal(recently_played, features_with_nones)

    # Should filter out None and aggregate only valid entries
    assert signal["track_count"] == 3
    assert signal["avg_energy"] > 0


def test_extract_genre_signal_happy_path(top_artists_fixture) -> None:
    """Test genre signal extraction."""
    signal = _extract_genre_signal(top_artists_fixture)

    assert "top_genres" in signal
    assert "artist_count" in signal
    assert signal["artist_count"] == 5
    assert len(signal["top_genres"]) <= 10
    # "pop" and "dance"/"electronic" should appear multiple times
    assert "pop" in signal["top_genres"]


def test_extract_genre_signal_empty() -> None:
    """Test genre signal extraction with empty artists."""
    signal = _extract_genre_signal([])

    assert signal["top_genres"] == []
    assert signal["artist_count"] == 0


def test_extract_playback_signal_active(current_playback_fixture) -> None:
    """Test playback signal extraction with active playback."""
    signal = _extract_playback_signal(current_playback_fixture)

    assert signal["is_active"] is True
    assert signal["track_name"] == "Now Playing Track"
    assert signal["artist_name"] == "Current Artist"
    assert signal["context_type"] == "playlist"
    assert signal["context_uri"] == "spotify:playlist:123456"


def test_extract_playback_signal_none(current_playback_none_fixture) -> None:
    """Test playback signal extraction with no playback."""
    signal = _extract_playback_signal(current_playback_none_fixture)

    assert signal["is_active"] is False
    assert signal["track_name"] is None
    assert signal["artist_name"] is None
    assert signal["context_type"] is None
    assert signal["context_uri"] is None


def test_extract_playback_signal_null_input() -> None:
    """Test playback signal extraction with null input."""
    signal = _extract_playback_signal(None)

    assert signal["is_active"] is False
    assert signal["track_name"] is None
    assert signal["artist_name"] is None


def test_extract_playlist_signal(playlists_fixture) -> None:
    """Test playlist signal extraction."""
    signal = _extract_playlist_signal(playlists_fixture)

    assert len(signal["playlist_names"]) == 3
    assert "Chill Vibes" in signal["playlist_names"]
    assert "Workout Mix" in signal["playlist_names"]
    assert "Date Night" in signal["playlist_names"]
    assert signal["playlist_count"] == 3


def test_extract_playlist_signal_empty() -> None:
    """Test playlist signal extraction with empty input."""
    signal = _extract_playlist_signal([])

    assert signal["playlist_names"] == []
    assert signal["playlist_count"] == 0


# Unit test for confidence calculation


def test_calculate_confidence_all_success() -> None:
    """Test confidence calculation when all sources succeed."""
    confidence = _calculate_confidence(
        recently_played_success=True,
        audio_features_success=True,
        top_artists_success=True,
        current_playback_success=True,
        playlists_success=True,
    )
    assert confidence == 1.0


def test_calculate_confidence_no_audio_features() -> None:
    """Test confidence calculation when audio_features fails."""
    confidence = _calculate_confidence(
        recently_played_success=True,
        audio_features_success=False,
        top_artists_success=True,
        current_playback_success=True,
        playlists_success=True,
    )
    # 0.25 (recently_played halved) + 0.25 (top_artists) + 0.15 (playback) + 0.10 (playlists)
    assert confidence == 0.75


def test_calculate_confidence_only_recently_played() -> None:
    """Test confidence calculation when only recently_played + audio_features succeed."""
    confidence = _calculate_confidence(
        recently_played_success=True,
        audio_features_success=True,
        top_artists_success=False,
        current_playback_success=False,
        playlists_success=False,
    )
    assert confidence == 0.50


def test_calculate_confidence_partial() -> None:
    """Test confidence calculation with partial success."""
    confidence = _calculate_confidence(
        recently_played_success=True,
        audio_features_success=True,
        top_artists_success=False,
        current_playback_success=True,
        playlists_success=True,
    )
    # 0.50 + 0.15 + 0.10 = 0.75
    assert confidence == 0.75


def test_calculate_confidence_all_fail() -> None:
    """Test confidence calculation when all sources fail."""
    confidence = _calculate_confidence(
        recently_played_success=False,
        audio_features_success=False,
        top_artists_success=False,
        current_playback_success=False,
        playlists_success=False,
    )
    assert confidence == 0.0


# Integration tests


@pytest.mark.asyncio
async def test_fetch_spotify_happy_path(
    recently_played_fixture,
    audio_features_fixture,
    top_artists_fixture,
    current_playback_fixture,
    playlists_fixture,
) -> None:
    """Test happy path: all sources succeed."""
    with (
        patch("src.tools.spotify._make_client") as mock_make_client,
        patch("src.tools.spotify._fetch_recently_played") as mock_recent,
        patch("src.tools.spotify._fetch_audio_features") as mock_features,
        patch("src.tools.spotify._fetch_top_artists") as mock_artists,
        patch("src.tools.spotify._fetch_current_playback") as mock_playback,
        patch("src.tools.spotify._fetch_playlists") as mock_playlists,
    ):
        mock_sp = MagicMock()
        mock_make_client.return_value = mock_sp
        mock_recent.return_value = recently_played_fixture
        mock_features.return_value = audio_features_fixture
        mock_artists.return_value = top_artists_fixture
        mock_playback.return_value = current_playback_fixture
        mock_playlists.return_value = playlists_fixture

        payload = await fetch_spotify("test_user")

        assert payload["source"] == "spotify"
        assert "fetched_at" in payload
        assert payload["confidence"] == 1.0
        assert "signals" in payload
        assert "audio" in payload["signals"]
        assert "genre" in payload["signals"]
        assert "playback" in payload["signals"]
        assert "playlist" in payload["signals"]


@pytest.mark.asyncio
async def test_fetch_spotify_recently_played_fails() -> None:
    """Test when only recently_played fails."""
    with (
        patch("src.tools.spotify._make_client") as mock_make_client,
        patch("src.tools.spotify._fetch_recently_played") as mock_recent,
        patch("src.tools.spotify._fetch_audio_features") as mock_features,
        patch("src.tools.spotify._fetch_top_artists") as mock_artists,
        patch("src.tools.spotify._fetch_current_playback") as mock_playback,
        patch("src.tools.spotify._fetch_playlists") as mock_playlists,
    ):
        mock_sp = MagicMock()
        mock_make_client.return_value = mock_sp
        mock_recent.side_effect = Exception("API error")
        mock_features.return_value = []
        mock_artists.return_value = [{"genres": ["pop"]}]
        mock_playback.return_value = None
        mock_playlists.return_value = []

        payload = await fetch_spotify("test_user")

        assert payload["source"] == "spotify"
        assert payload["confidence"] <= 0.50
        # audio signal should be empty
        assert payload["signals"]["audio"]["track_count"] == 0


@pytest.mark.asyncio
async def test_fetch_spotify_makes_client_fails() -> None:
    """Test when _make_client fails (missing env vars)."""
    with patch("src.tools.spotify._make_client") as mock_make_client:
        mock_make_client.side_effect = SourceUnavailableError(
            "spotify", "Missing credentials"
        )

        with pytest.raises(SourceUnavailableError) as exc_info:
            await fetch_spotify("test_user")

        assert exc_info.value.source == "spotify"


@pytest.mark.asyncio
async def test_fetch_spotify_top_artists_fails(
    recently_played_fixture,
    audio_features_fixture,
    current_playback_fixture,
    playlists_fixture,
) -> None:
    """Test when top_artists endpoint fails."""
    with (
        patch("src.tools.spotify._make_client") as mock_make_client,
        patch("src.tools.spotify._fetch_recently_played") as mock_recent,
        patch("src.tools.spotify._fetch_audio_features") as mock_features,
        patch("src.tools.spotify._fetch_top_artists") as mock_artists,
        patch("src.tools.spotify._fetch_current_playback") as mock_playback,
        patch("src.tools.spotify._fetch_playlists") as mock_playlists,
    ):
        mock_sp = MagicMock()
        mock_make_client.return_value = mock_sp
        mock_recent.return_value = recently_played_fixture
        mock_features.return_value = audio_features_fixture
        mock_artists.side_effect = Exception("Rate limit")
        mock_playback.return_value = current_playback_fixture
        mock_playlists.return_value = playlists_fixture

        payload = await fetch_spotify("test_user")

        # Confidence should be reduced: 0.50 + 0.15 + 0.10 = 0.75
        assert payload["confidence"] == 0.75
        assert payload["signals"]["genre"]["top_genres"] == []


@pytest.mark.asyncio
async def test_fetch_spotify_current_playback_none(
    recently_played_fixture,
    audio_features_fixture,
    top_artists_fixture,
    playlists_fixture,
) -> None:
    """Test when current playback returns None."""
    with (
        patch("src.tools.spotify._make_client") as mock_make_client,
        patch("src.tools.spotify._fetch_recently_played") as mock_recent,
        patch("src.tools.spotify._fetch_audio_features") as mock_features,
        patch("src.tools.spotify._fetch_top_artists") as mock_artists,
        patch("src.tools.spotify._fetch_current_playback") as mock_playback,
        patch("src.tools.spotify._fetch_playlists") as mock_playlists,
    ):
        mock_sp = MagicMock()
        mock_make_client.return_value = mock_sp
        mock_recent.return_value = recently_played_fixture
        mock_features.return_value = audio_features_fixture
        mock_artists.return_value = top_artists_fixture
        mock_playback.return_value = None
        mock_playlists.return_value = playlists_fixture

        payload = await fetch_spotify("test_user")

        # returning None is not a success, so playback weight should be 0 but endpoint still "succeeded"
        assert payload["confidence"] == 1.0
        assert payload["signals"]["playback"]["is_active"] is False
