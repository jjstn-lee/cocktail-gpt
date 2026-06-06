"""Tests for the rate_cocktail node."""

import pytest
from unittest.mock import AsyncMock, patch

from src.state import AgentState, Cocktail, Feedback
from src.nodes.rate_cocktail import rate_cocktail


@pytest.mark.asyncio
async def test_rate_cocktail_positive():
    """Test rate_cocktail extracts positive feedback."""
    state = AgentState(
        user_id="test_user",
        thread_id="test_thread",
        latest_message="I loved that! Perfect drink",
        recommendations=[
            Cocktail(
                name="Negroni",
                ingredients=["gin", "campari", "vermouth"],
                method="Stir with ice, strain into rocks glass",
                flavor_notes=["bitter", "herbal"],
                why_this_works="Classic bitter spirit combo",
            )
        ],
        feedback=[],
    )

    with patch("src.nodes.rate_cocktail.get_llm") as mock_get_llm:
        from src.nodes.rate_cocktail import FeedbackRating

        mock_response = FeedbackRating(
            rating=5, explanation="Great positive feedback on the drink!"
        )

        mock_llm = AsyncMock()
        mock_llm.with_structured_output = lambda x: mock_llm
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_get_llm.return_value = mock_llm

        result = await rate_cocktail(state)

        assert "feedback" in result
        assert len(result["feedback"]) == 1
        assert result["feedback"][0].rating == 5
        assert result["feedback"][0].cocktail_name == "Negroni"


@pytest.mark.asyncio
async def test_rate_cocktail_negative():
    """Test rate_cocktail extracts negative feedback."""
    state = AgentState(
        user_id="test_user",
        thread_id="test_thread",
        latest_message="That was way too bitter for me",
        recommendations=[
            Cocktail(
                name="Campari Soda",
                ingredients=["campari", "soda", "lime"],
                method="Pour over ice, top with soda",
                flavor_notes=["bitter", "citrus"],
                why_this_works="Refreshing aperitif",
            )
        ],
        feedback=[],
    )

    with patch("src.nodes.rate_cocktail.get_llm") as mock_get_llm:
        from src.nodes.rate_cocktail import FeedbackRating

        mock_response = FeedbackRating(
            rating=1, explanation="User found it too bitter"
        )

        mock_llm = AsyncMock()
        mock_llm.with_structured_output = lambda x: mock_llm
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_get_llm.return_value = mock_llm

        result = await rate_cocktail(state)

        assert "feedback" in result
        assert len(result["feedback"]) == 1
        assert result["feedback"][0].rating == 1


@pytest.mark.asyncio
async def test_rate_cocktail_no_recommendations():
    """Test rate_cocktail handles case with no prior recommendations."""
    state = AgentState(
        user_id="test_user",
        thread_id="test_thread",
        latest_message="That was great!",
        recommendations=[],
        feedback=[],
    )

    result = await rate_cocktail(state)

    assert "feedback" in result
    assert len(result["feedback"]) == 0
    assert "rate_cocktail_message" in result
