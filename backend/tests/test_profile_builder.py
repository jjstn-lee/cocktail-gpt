"""Unit tests for profile_builder node."""

import pytest
from unittest.mock import AsyncMock, patch
import json

from src.nodes.profile_builder import profile_builder
from src.state import AgentState, UserProfile


@pytest.mark.asyncio
async def test_profile_builder_with_sources():
    """Test profile builder with valid source data."""
    state: AgentState = {
        "user_id": "test_user",
        "thread_id": "test_thread",
        "raw_sources": {
            "spotify": {
                "source": "spotify",
                "signals": {"audio_signal": {"energy": 0.8}},
                "confidence": 0.9,
                "fetched_at": "2026-05-28T00:00:00Z",
            }
        },
    }

    mock_llm_response = AsyncMock()
    mock_llm_response.content = json.dumps(
        {
            "mood": "energetic",
            "occasion": "happy hour",
            "vibe": "upbeat",
            "energy_level": 0.8,
        }
    )

    with patch("src.nodes.profile_builder.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
        mock_get_llm.return_value = mock_llm

        result = await profile_builder(state)

    assert "user_profile" in result
    assert result["user_profile"].mood == "energetic"
    assert result["user_profile"].energy_level == 0.8


@pytest.mark.asyncio
async def test_profile_builder_no_sources():
    """Test profile builder with no sources."""
    state: AgentState = {
        "user_id": "test_user",
        "thread_id": "test_thread",
        "raw_sources": {},
    }

    result = await profile_builder(state)

    assert "user_profile" in result
    assert isinstance(result["user_profile"], UserProfile)


@pytest.mark.asyncio
async def test_profile_builder_malformed_response():
    """Test profile builder with malformed LLM response."""
    state: AgentState = {
        "user_id": "test_user",
        "thread_id": "test_thread",
        "raw_sources": {
            "spotify": {
                "source": "spotify",
                "signals": {"audio_signal": {"energy": 0.8}},
                "confidence": 0.9,
                "fetched_at": "2026-05-28T00:00:00Z",
            }
        },
    }

    mock_llm_response = AsyncMock()
    mock_llm_response.content = "invalid json"

    with patch("src.nodes.profile_builder.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
        mock_get_llm.return_value = mock_llm

        result = await profile_builder(state)

    assert "user_profile" in result
    assert isinstance(result["user_profile"], UserProfile)
