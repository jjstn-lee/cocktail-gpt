"""Unit tests for clarify node."""

import pytest
from unittest.mock import AsyncMock, patch
from langgraph.types import interrupt as lg_interrupt

from src.nodes.clarify import clarify
from src.state import AgentState


@pytest.mark.asyncio
async def test_clarify_pauses_with_interrupt():
    """Test clarify node generates a question and pauses via interrupt()."""
    state: AgentState = {
        "user_id": "test_user",
        "thread_id": "test_thread",
        "confidence_score": 0.5,
    }

    mock_llm_response = AsyncMock()
    mock_llm_response.content = "Are you a whiskey person or more into vodka?"

    # Mock interrupt to return an answer (simulating user submission)
    user_answer = "I prefer whiskey"

    with patch("src.nodes.clarify.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
        mock_get_llm.return_value = mock_llm

        with patch("src.nodes.clarify.interrupt") as mock_interrupt:
            mock_interrupt.return_value = user_answer

            result = await clarify(state)

    # Verify interrupt was called with the question
    mock_interrupt.assert_called_once_with("Are you a whiskey person or more into vodka?")

    # Verify result contains clarification_answer and session flag
    assert "clarification_answer" in result
    assert result["clarification_answer"] == user_answer
    assert result["session_clarification_used"] is True
