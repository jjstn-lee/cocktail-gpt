"""Integration tests for the full graph."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.graph import build_graph
from langgraph.checkpoint.memory import MemorySaver
from src.state import AgentState, Cocktail


@pytest.fixture
def mock_checkpointer():
    """Provide a real MemorySaver for testing (checkpointer needs real implementation)."""
    return MemorySaver()


@pytest.mark.asyncio
async def test_graph_full_flow_with_recommendations(mock_checkpointer):
    """Test full graph flow from ingest to output with recommendations."""

    # Mock all LLM calls
    mock_profile_response = AsyncMock()
    mock_profile_response.content = '{"mood": "energetic", "vibe": "upbeat", "energy_level": 0.8, "occasion": null}'

    mock_pref_response = AsyncMock()
    mock_pref_response.content = '{"preferred_spirits": ["vodka"], "preferred_flavors": ["citrus"], "abv_preference": "moderate", "style_preferences": []}'

    mock_recommender_response = AsyncMock()
    mock_recommender_response.recommendations = [
        Cocktail(
            name="Cosmopolitan",
            ingredients=["2 oz vodka", "1 oz cranberry"],
            method="shake",
            flavor_notes=["tart"],
            why_this_works="vodka + citrus",
        )
    ]
    mock_recommender_response.confidence_score = 0.85
    mock_recommender_response.rationale = "Great match"

    def mock_get_llm():
        llm = AsyncMock()
        llm.ainvoke = AsyncMock(side_effect=[mock_profile_response, mock_pref_response])
        llm.with_structured_output = lambda x: llm
        return llm

    with patch("src.nodes.profile_builder.get_llm", side_effect=mock_get_llm):
        with patch("src.nodes.preference_extractor.get_llm", side_effect=mock_get_llm):
            with patch("src.nodes.recommender.get_llm") as mock_recommender_llm:
                    mock_rec_llm = AsyncMock()
                    mock_rec_llm.with_structured_output = lambda x: mock_rec_llm
                    mock_rec_llm.ainvoke = AsyncMock(return_value=mock_recommender_response)
                    mock_recommender_llm.return_value = mock_rec_llm

                    with patch("src.nodes.ingest.fetch_spotify") as mock_spotify:
                        with patch("src.nodes.ingest.fetch_weather") as mock_weather:
                            mock_spotify.return_value = {
                                "source": "spotify",
                                "signals": {"audio_signal": {}},
                                "confidence": 0.9,
                                "fetched_at": "2026-05-28T00:00:00Z",
                            }
                            mock_weather.return_value = {
                                "source": "weather",
                                "signals": {"current": {}},
                                "confidence": 0.75,
                                "fetched_at": "2026-05-28T00:00:00Z",
                            }

                            graph = build_graph(mock_checkpointer)

                            initial_state: AgentState = {
                                "user_id": "test_user",
                                "thread_id": "test_thread",
                                "raw_sources": {},
                                "recommendations": [],
                                "confidence_score": 0.0,
                                "session_count": 0,
                                "feedback": [],
                            }

                            config = {"configurable": {"thread_id": "test_thread"}}
                            result = await graph.ainvoke(initial_state, config=config)

                            # Verify graph executed
                            assert result is not None
                            assert result.get("user_id") == "test_user"
