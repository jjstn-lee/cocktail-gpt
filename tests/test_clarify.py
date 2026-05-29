"""Unit tests for clarify node."""

import pytest
from unittest.mock import AsyncMock, patch

from src.nodes.clarify import clarify
from src.state import AgentState


@pytest.mark.asyncio
async def test_clarify_asks_question():
    """Test clarify node generates a question."""
    state: AgentState = {
        "user_id": "test_user",
        "thread_id": "test_thread",
        "confidence_score": 0.5,
    }

    mock_llm_response = AsyncMock()
    mock_llm_response.content = "Are you a whiskey person or more into vodka?"

    with patch("src.nodes.clarify.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
        mock_get_llm.return_value = mock_llm

        result = await clarify(state)

    assert "clarification_question" in result
    assert result["clarification_question"] == "Are you a whiskey person or more into vodka?"
    assert result["session_clarification_used"] is True
