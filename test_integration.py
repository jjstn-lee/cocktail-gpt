#!/usr/bin/env python
"""Integration test script demonstrating the full data flow with mocked sources."""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import patch

from loguru import logger

from src.nodes.ingest import ingest_node
from src.state import AgentState
from src.tools.base import SourcePayload


def create_mock_spotify_payload() -> SourcePayload:
    """Create a realistic mock Spotify payload."""
    return SourcePayload(
        source="spotify",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        signals={
            "audio": {
                "avg_energy": 0.78,
                "avg_valence": 0.62,
                "avg_danceability": 0.71,
                "avg_tempo": 125.3,
                "avg_acousticness": 0.15,
                "avg_instrumentalness": 0.08,
                "track_count": 47,
            },
            "genre": {
                "top_genres": ["indie-rock", "alternative", "pop", "electronic"],
                "artist_count": 23,
            },
            "playback": {
                "is_active": True,
                "track_name": "Ocean Avenue",
                "artist_name": "Yellowcard",
                "context_type": "playlist",
                "context_uri": "spotify:playlist:37i9dQZF1DX7F6T8nwGA03",
            },
            "playlist": {
                "playlist_names": ["Summer Vibes", "Workout Mix", "Chill Evening"],
                "playlist_count": 3,
            },
        },
        confidence=0.92,
    )


def create_mock_weather_payload() -> SourcePayload:
    """Create a realistic mock weather payload."""
    return SourcePayload(
        source="weather",
        fetched_at=datetime.now(timezone.utc).isoformat(),
        signals={
            "current": {
                "temp": 72.5,
                "feels_like": 71.2,
                "humidity": 65,
                "pressure": 1013,
                "wind_speed": 4.5,
                "clouds": 15,
                "condition": "Clear",
                "description": "clear sky",
                "sunrise": 1679078400,
                "sunset": 1679125200,
            },
            "forecast": {
                "avg_temp": 71.8,
                "avg_humidity": 63,
                "avg_wind_speed": 4.2,
                "forecast_count": 12,
                "conditions": ["Clear", "Partly Cloudy"],
            },
        },
        confidence=0.75,
    )


def print_header(title: str) -> None:
    """Print a formatted header."""
    print(f"\n{'=' * 80}")
    print(f"  {title}")
    print(f"{'=' * 80}")


async def test_integration() -> None:
    """Run integration test with mocked data sources."""

    print_header("COCKTAIL RECOMMENDATION AGENT - INTEGRATION TEST")
    print("\nThis test runs the ingest node with mocked Spotify and Weather data.")
    print("This allows testing without requiring live API credentials.")

    # Create initial state
    initial_state: AgentState = AgentState(
        user_id="integration_test_user",
        raw_sources={},
        user_profile=None,
        preferences=None,
        constraints=None,
        recommendations=[],
        confidence_score=0.0,
        clarification_question=None,
        clarification_answer=None,
        session_count=1,
        session_clarification_used=False,
        feedback=[],
    )

    # Mock the fetch functions
    spotify_payload = create_mock_spotify_payload()
    weather_payload = create_mock_weather_payload()

    print_header("Test Setup")
    print(f"User ID: {initial_state['user_id']}")
    print(f"Sources to ingest: Spotify, Weather")
    print(f"Mocked Spotify confidence: {spotify_payload['confidence']:.2f}")
    print(f"Mocked Weather confidence: {weather_payload['confidence']:.2f}")

    # Run ingest with mocked sources
    with patch("src.nodes.ingest.fetch_spotify", return_value=spotify_payload), patch(
        "src.nodes.ingest.fetch_weather", return_value=weather_payload
    ):
        print_header("Running Ingest Node")
        logger.info("Starting ingest node...")

        result = await ingest_node(initial_state)

        logger.info("Ingest node complete")

    # Display results
    print_header("INGESTION RESULTS")

    raw_sources = result.get("raw_sources", {})
    print(f"\nSources successfully ingested: {list(raw_sources.keys())}")

    for source_name, payload in raw_sources.items():
        print(f"\n{'─' * 40}")
        print(f"📊 {source_name.upper()}")
        print(f"{'─' * 40}")

        print(f"  Fetched: {payload.get('fetched_at')}")
        print(f"  Confidence: {payload.get('confidence', 0):.2f}")

        signals = payload.get("signals", {})
        print(f"  Signal categories: {', '.join(signals.keys())}")

        for signal_name, signal_data in signals.items():
            print(f"\n    {signal_name.title()}:")
            if isinstance(signal_data, dict):
                for key, value in list(signal_data.items())[:5]:  # Show first 5
                    if isinstance(value, (int, float)):
                        print(f"      • {key}: {value:.2f}")
                    elif isinstance(value, list):
                        preview = ", ".join(str(v) for v in value[:3])
                        suffix = ", ..." if len(value) > 3 else ""
                        print(f"      • {key}: [{preview}{suffix}]")
                    else:
                        print(f"      • {key}: {value}")
                if len(signal_data) > 5:
                    print(f"      ... and {len(signal_data) - 5} more fields")

    # Data flow example
    print_header("Data Flow Example")
    print("""
The ingested data flows into subsequent nodes:

1. PROFILE BUILDER
   - Analyzes Spotify signals (energy, valence, genres, current playback)
   - Analyzes weather signals (temperature, condition, forecast)
   - Synthesizes into UserProfile (mood, occasion, vibe, energy_level)

2. PREFERENCE EXTRACTOR
   - Maps genres and playlist themes to spirit preferences
   - Extracts flavor notes from audio characteristics
   - Sets ABV preferences based on energy and mood

3. CONSTRAINT CHECKER
   - Parses any dietary restrictions from the user profile
   - Tracks ingredients the user has on hand
   - Sets maximum ABV limits based on weather/mood

4. RECOMMENDER
   - Generates cocktail recommendations based on signals
   - Returns top 3 recommendations with confidence score

5. CLARIFY (conditional)
   - If confidence < 0.65, asks clarifying question
   - User responds and recommender runs again

6. OUTPUT
   - Returns final recommendations to user
    """)

    # Save to JSON
    print_header("Saving Results")

    results = {
        "test_type": "integration_test_with_mocks",
        "user_id": initial_state["user_id"],
        "sources_ingested": list(raw_sources.keys()),
        "spotify": {
            "confidence": spotify_payload["confidence"],
            "signals": spotify_payload["signals"],
        },
        "weather": {
            "confidence": weather_payload["confidence"],
            "signals": weather_payload["signals"],
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    with open("integration_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("✓ Results saved to integration_test_results.json")

    print_header("Integration Test Complete")
    print("\n✅ All sources ingested successfully!")
    print("\nNext steps:")
    print("  1. Implement profile_builder node")
    print("  2. Implement preference_extractor node")
    print("  3. Implement constraint_checker node")
    print("  4. Implement recommender node with LLM")
    print("  5. Implement clarify node with conditional routing")
    print("  6. Implement output node")
    print()


if __name__ == "__main__":
    asyncio.run(test_integration())
