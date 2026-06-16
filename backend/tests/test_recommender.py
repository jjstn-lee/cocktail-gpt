"""Unit tests for recommender node."""

import pytest
from unittest.mock import AsyncMock, patch

from src.nodes.recommender import recommender
from src.state import AgentState, UserProfile, Preferences, Constraints, Cocktail


@pytest.mark.asyncio
async def test_recommender_with_all_inputs():
    """Test recommender with profile, preferences, and constraints."""
    state: AgentState = {
        "user_id": "test_user",
        "thread_id": "test_thread",
        "user_profile": UserProfile(mood="energetic", vibe="upbeat"),
        "preferences": Preferences(
            preferred_spirits=["vodka"],
            preferred_flavors=["citrus"],
            abv_preference="moderate",
        ),
        "constraints": Constraints(allergies=[]),
    }

    mock_llm_response = AsyncMock()
    mock_llm_response.recommendations = [
        Cocktail(
            name="Cosmopolitan",
            ingredients=["2 oz vodka", "1 oz cranberry", "0.5 oz lime"],
            method="shake and strain",
            flavor_notes=["tart", "fruity"],
            why_this_works="vodka base with citrus notes",
        )
    ]
    mock_llm_response.confidence_score = 0.85
    mock_llm_response.rationale = "Great match for energetic vibes"

    with patch("src.nodes.recommender.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.with_structured_output = lambda x: mock_llm
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
        mock_get_llm.return_value = mock_llm

        result = await recommender(state)

    assert "recommendations" in result
    assert len(result["recommendations"]) == 1
    assert result["recommendations"][0].name == "Cosmopolitan"
    assert result["confidence_score"] == 0.85


