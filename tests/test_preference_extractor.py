"""Unit tests for preference_extractor node."""

import pytest
from unittest.mock import AsyncMock, patch
import json

from src.nodes.preference_extractor import preference_extractor
from src.state import AgentState, UserProfile, Preferences


@pytest.mark.asyncio
async def test_preference_extractor_with_profile():
    """Test preference extractor with user profile."""
    state: AgentState = {
        "user_id": "test_user",
        "thread_id": "test_thread",
        "raw_sources": {},
        "user_profile": UserProfile(mood="energetic", vibe="upbeat"),
    }

    mock_llm_response = AsyncMock()
    mock_llm_response.content = json.dumps(
        {
            "preferred_spirits": ["vodka", "gin"],
            "preferred_flavors": ["citrus", "herbal"],
            "abv_preference": "moderate",
            "style_preferences": ["sour"],
        }
    )

    with patch("src.nodes.preference_extractor.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
        mock_get_llm.return_value = mock_llm

        result = await preference_extractor(state)

    assert "preferences" in result
    assert result["preferences"].preferred_spirits == ["vodka", "gin"]
    assert result["preferences"].abv_preference == "moderate"


@pytest.mark.asyncio
async def test_preference_extractor_no_profile():
    """Test preference extractor with no profile."""
    state: AgentState = {
        "user_id": "test_user",
        "thread_id": "test_thread",
        "raw_sources": {},
    }

    mock_llm_response = AsyncMock()
    mock_llm_response.content = json.dumps(
        {
            "preferred_spirits": [],
            "preferred_flavors": [],
            "abv_preference": None,
            "style_preferences": [],
        }
    )

    with patch("src.nodes.preference_extractor.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
        mock_get_llm.return_value = mock_llm

        result = await preference_extractor(state)

    assert "preferences" in result
    assert isinstance(result["preferences"], Preferences)
