"""Tests for the explain_recommendation node."""

import pytest
from unittest.mock import AsyncMock, patch

from src.state import AgentState, Cocktail, UserProfile, Preferences, Constraints
from src.nodes.explain_recommendation import explain_recommendation


@pytest.mark.asyncio
async def test_explain_recommendation_generates_explanation():
    """Test explain_recommendation generates a valid explanation."""
    state = AgentState(
        user_id="test_user",
        thread_id="test_thread",
        latest_message="Why did you recommend that?",
        user_profile=UserProfile(mood="romantic", occasion="date", vibe="elegant", energy_level=0.5),
        preferences=Preferences(
            preferred_spirits=["gin", "whiskey"],
            preferred_flavors=["citrus", "herbal"],
            abv_preference="moderate",
        ),
        constraints=Constraints(allergies=[], max_abv=40.0),
        recommendations=[
            Cocktail(
                name="Bee's Knees",
                ingredients=["gin", "lemon juice", "honey syrup"],
                method="Shake with ice, strain into coupe",
                flavor_notes=["citrus", "floral", "sweet"],
                why_this_works="Classic gin sour with honey sweetness",
            )
        ],
    )

    with patch("src.nodes.explain_recommendation.get_llm") as mock_get_llm:
        from src.nodes.explain_recommendation import ExplanationOutput

        mock_response = ExplanationOutput(
            explanation=(
                "The Bee's Knees is perfect for a romantic date night. "
                "It combines your love of gin with citrus and floral notes that match your elegant mood. "
                "The honey adds just the right sweetness without being too strong."
            )
        )

        mock_llm = AsyncMock()
        mock_llm.with_structured_output = lambda x: mock_llm
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_get_llm.return_value = mock_llm

        result = await explain_recommendation(state)

        assert "explanation" in result
        assert "romantic" in result["explanation"].lower()
        assert "gin" in result["explanation"].lower()


@pytest.mark.asyncio
async def test_explain_recommendation_no_recommendations():
    """Test explain_recommendation handles case with no prior recommendations."""
    state = AgentState(
        user_id="test_user",
        thread_id="test_thread",
        latest_message="Why did you recommend that?",
        recommendations=[],
    )

    result = await explain_recommendation(state)

    assert "explanation" in result
    assert "prior recommendations" in result["explanation"].lower()


@pytest.mark.asyncio
async def test_explain_recommendation_fallback():
    """Test explain_recommendation provides fallback explanation on error."""
    state = AgentState(
        user_id="test_user",
        thread_id="test_thread",
        latest_message="Why did you recommend that?",
        preferences=Preferences(preferred_flavors=["fruity"]),
        recommendations=[
            Cocktail(
                name="Margarita",
                ingredients=["tequila", "lime", "triple sec"],
                method="Shake with ice, strain into salt-rimmed glass",
                flavor_notes=["citrus", "agave"],
                why_this_works="Classic tequila sour",
            )
        ],
    )

    with patch("src.nodes.explain_recommendation.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.with_structured_output = lambda x: mock_llm
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("LLM error"))
        mock_get_llm.return_value = mock_llm

        result = await explain_recommendation(state)

        assert "explanation" in result
        assert "fruity" in result["explanation"].lower()  # Fallback uses preferences
