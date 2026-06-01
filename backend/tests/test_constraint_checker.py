"""Unit tests for constraint_checker node."""

import pytest
from unittest.mock import AsyncMock, patch
import json

from src.nodes.constraint_checker import constraint_checker
from src.state import AgentState, Constraints


@pytest.mark.asyncio
async def test_constraint_checker():
    """Test constraint checker."""
    state: AgentState = {
        "user_id": "test_user",
        "thread_id": "test_thread",
        "raw_sources": {},
    }

    mock_llm_response = AsyncMock()
    mock_llm_response.content = json.dumps(
        {
            "allergies": ["nuts"],
            "ingredients_on_hand": ["vodka", "lime juice"],
            "max_abv": 30.0,
        }
    )

    with patch("src.nodes.constraint_checker.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
        mock_get_llm.return_value = mock_llm

        result = await constraint_checker(state)

    assert "constraints" in result
    assert result["constraints"].allergies == ["nuts"]
    assert result["constraints"].max_abv == 30.0


@pytest.mark.asyncio
async def test_constraint_checker_no_constraints():
    """Test constraint checker with no constraints."""
    state: AgentState = {
        "user_id": "test_user",
        "thread_id": "test_thread",
        "raw_sources": {},
    }

    mock_llm_response = AsyncMock()
    mock_llm_response.content = json.dumps(
        {
            "allergies": [],
            "ingredients_on_hand": [],
            "max_abv": None,
        }
    )

    with patch("src.nodes.constraint_checker.get_llm") as mock_get_llm:
        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
        mock_get_llm.return_value = mock_llm

        result = await constraint_checker(state)

    assert "constraints" in result
    assert isinstance(result["constraints"], Constraints)
    assert result["constraints"].allergies == []
