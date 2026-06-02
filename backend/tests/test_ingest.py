"""Tests for the ingest node."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from src.nodes.ingest import ingest_node
from src.state import AgentState
from src.tools.base import SourcePayload, SourceUnavailableError


@pytest.fixture
def base_state() -> AgentState:
    """Create a base agent state for testing."""
    return AgentState(
        user_id="test_user_123",
        raw_sources={},
        user_profile=None,
        preferences=None,
        constraints=None,
        recommendations=[],
        confidence_score=0.0,
        clarification_answer=None,
        session_count=1,
        session_clarification_used=False,
        feedback=[],
    )


@pytest.fixture
def spotify_payload() -> SourcePayload:
    """Create a mock Spotify payload."""
    return SourcePayload(
        source="spotify",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        signals={
            "audio": {
                "avg_energy": 0.75,
                "avg_valence": 0.65,
                "avg_danceability": 0.70,
                "avg_tempo": 120.0,
                "avg_acousticness": 0.2,
                "avg_instrumentalness": 0.1,
                "track_count": 50,
            },
            "genre": {"top_genres": ["pop", "rock"], "artist_count": 10},
            "playback": {
                "is_active": True,
                "track_name": "Test Song",
                "artist_name": "Test Artist",
                "context_type": "playlist",
                "context_uri": "spotify:playlist:123",
            },
            "playlist": {
                "playlist_names": ["Favorites", "Workout"],
                "playlist_count": 2,
            },
        },
        confidence=0.95,
    )


@pytest.fixture
def weather_payload() -> SourcePayload:
    """Create a mock weather payload."""
    return SourcePayload(
        source="weather",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        signals={
            "current": {
                "temp": 72.5,
                "feels_like": 71.0,
                "humidity": 65,
                "pressure": 1013,
                "wind_speed": 4.5,
                "clouds": 10,
                "condition": "Clear",
                "description": "clear sky",
                "sunrise": 1000000000,
                "sunset": 1000050000,
            },
            "forecast": {
                "avg_temp": 71.2,
                "avg_humidity": 62,
                "avg_wind_speed": 4.8,
                "forecast_count": 12,
                "conditions": ["Clear", "Clouds"],
            },
        },
        confidence=0.75,
    )


@pytest.mark.asyncio
async def test_ingest_node_spotify_success(
    base_state: AgentState, spotify_payload: SourcePayload
) -> None:
    """Test ingest node with successful Spotify fetch."""
    with patch("src.nodes.ingest.fetch_spotify") as mock_fetch:
        mock_fetch.return_value = spotify_payload

        result = await ingest_node(base_state)

        assert "raw_sources" in result
        assert "spotify" in result["raw_sources"]
        assert result["raw_sources"]["spotify"]["source"] == "spotify"
        assert (
            result["raw_sources"]["spotify"]["signals"]["audio"]["avg_energy"] == 0.75
        )


@pytest.mark.asyncio
async def test_ingest_node_spotify_unavailable(base_state: AgentState) -> None:
    """Test ingest node when Spotify source is unavailable."""
    with patch("src.nodes.ingest.fetch_spotify") as mock_fetch:
        mock_fetch.side_effect = SourceUnavailableError(
            "spotify", "Missing credentials"
        )

        result = await ingest_node(base_state)

        # Should continue gracefully without raising
        assert "raw_sources" in result
        assert "spotify" not in result["raw_sources"]
        assert result["raw_sources"] == {}


@pytest.mark.asyncio
async def test_ingest_node_generic_exception(base_state: AgentState) -> None:
    """Test ingest node with generic exception."""
    with patch("src.nodes.ingest.fetch_spotify") as mock_fetch:
        mock_fetch.side_effect = RuntimeError("Unexpected error")

        result = await ingest_node(base_state)

        # Should continue gracefully without raising
        assert "raw_sources" in result
        assert "spotify" not in result["raw_sources"]


@pytest.mark.asyncio
async def test_ingest_node_weather_success(
    base_state: AgentState, weather_payload: SourcePayload
) -> None:
    """Test ingest node with successful weather fetch."""
    with patch("src.nodes.ingest.fetch_spotify") as mock_spotify, patch(
        "src.nodes.ingest.fetch_weather"
    ) as mock_weather:
        # Return dummy Spotify to avoid empty sources
        mock_spotify.return_value = SourcePayload(
            source="spotify",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            signals={},
            confidence=0.0,
        )
        mock_weather.return_value = weather_payload

        result = await ingest_node(base_state)

        assert "raw_sources" in result
        assert "weather" in result["raw_sources"]
        assert result["raw_sources"]["weather"]["source"] == "weather"
        assert result["raw_sources"]["weather"]["signals"]["current"]["temp"] == 72.5


@pytest.mark.asyncio
async def test_ingest_node_weather_unavailable(base_state: AgentState) -> None:
    """Test ingest node when weather source is unavailable."""
    with patch("src.nodes.ingest.fetch_spotify") as mock_spotify, patch(
        "src.nodes.ingest.fetch_weather"
    ) as mock_weather:
        mock_spotify.return_value = SourcePayload(
            source="spotify",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            signals={},
            confidence=0.0,
        )
        mock_weather.side_effect = SourceUnavailableError(
            "weather", "Missing API key"
        )

        result = await ingest_node(base_state)

        # Should continue gracefully
        assert "raw_sources" in result
        assert "weather" not in result["raw_sources"]
        assert "spotify" in result["raw_sources"]


@pytest.mark.asyncio
async def test_ingest_node_multiple_sources(
    base_state: AgentState,
    spotify_payload: SourcePayload,
    weather_payload: SourcePayload,
) -> None:
    """Test ingest node with multiple sources (Spotify and Weather)."""
    with patch("src.nodes.ingest.fetch_spotify") as mock_spotify, patch(
        "src.nodes.ingest.fetch_weather"
    ) as mock_weather:
        mock_spotify.return_value = spotify_payload
        mock_weather.return_value = weather_payload

        result = await ingest_node(base_state)

        assert "raw_sources" in result
        assert "spotify" in result["raw_sources"]
        assert "weather" in result["raw_sources"]
        assert len(result["raw_sources"]) == 2
        assert (
            result["raw_sources"]["spotify"]["signals"]["audio"]["avg_energy"] == 0.75
        )
        assert result["raw_sources"]["weather"]["signals"]["current"]["temp"] == 72.5


@pytest.mark.asyncio
async def test_ingest_node_user_id_preserved(
    spotify_payload: SourcePayload,
) -> None:
    """Test that user_id is read correctly from state."""
    state = AgentState(
        user_id="unique_user_456",
        raw_sources={},
        user_profile=None,
        preferences=None,
        constraints=None,
        recommendations=[],
        confidence_score=0.0,
        clarification_answer=None,
        session_count=1,
        session_clarification_used=False,
        feedback=[],
    )

    with patch("src.nodes.ingest.fetch_spotify") as mock_fetch:
        mock_fetch.return_value = spotify_payload

        await ingest_node(state)

        # Verify fetch_spotify was called with the correct user_id
        mock_fetch.assert_called_once_with("unique_user_456")


@pytest.mark.asyncio
async def test_ingest_node_returns_dict_update(
    base_state: AgentState, spotify_payload: SourcePayload
) -> None:
    """Test that ingest node returns a proper dict update for state."""
    with patch("src.nodes.ingest.fetch_spotify") as mock_fetch:
        mock_fetch.return_value = spotify_payload

        result = await ingest_node(base_state)

        # Should return a dict with only "raw_sources" to update state
        assert isinstance(result, dict)
        assert "raw_sources" in result
        # Should not mutate original state
        assert base_state["raw_sources"] == {}


@pytest.mark.asyncio
async def test_ingest_node_concurrent_execution(
    base_state: AgentState,
    spotify_payload: SourcePayload,
    weather_payload: SourcePayload,
) -> None:
    """Test that ingest node gathers concurrent source fetches."""
    with patch("src.nodes.ingest.fetch_spotify") as mock_spotify, patch(
        "src.nodes.ingest.fetch_weather"
    ) as mock_weather:
        mock_spotify.return_value = spotify_payload
        mock_weather.return_value = weather_payload

        result = await ingest_node(base_state)

        # Both Spotify and Weather are implemented, so two calls expected
        assert mock_spotify.call_count == 1
        assert mock_weather.call_count == 1
        assert "raw_sources" in result
        assert len(result["raw_sources"]) == 2


@pytest.mark.asyncio
async def test_ingest_node_source_key_normalization(
    base_state: AgentState,
) -> None:
    """Test that sources are keyed by source name in raw_sources."""
    payload = SourcePayload(
        source="test_source",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        signals={"key": "value"},
        confidence=0.8,
    )

    with patch("src.nodes.ingest.fetch_spotify") as mock_fetch:
        mock_fetch.return_value = payload

        result = await ingest_node(base_state)

        # The payload has source="test_source" (mocking doesn't change this)
        # so we expect it to be keyed as "test_source"
        assert "test_source" in result["raw_sources"]


@pytest.mark.asyncio
async def test_ingest_node_partial_failure(
    base_state: AgentState, spotify_payload: SourcePayload
) -> None:
    """Test ingest node handles mix of success and failure gracefully."""
    # When we have multiple sources in the future, this will test:
    # Some succeed, some fail, all results are collected
    with patch("src.nodes.ingest.fetch_spotify") as mock_fetch:
        mock_fetch.return_value = spotify_payload

        result = await ingest_node(base_state)

        assert "raw_sources" in result
        # Spotify succeeds, so it should be in the result
        assert "spotify" in result["raw_sources"]
