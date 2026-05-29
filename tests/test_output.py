"""Unit tests for output node."""

import pytest

from src.nodes.output import output_node
from src.state import AgentState, Cocktail


@pytest.mark.asyncio
async def test_output_node_passthrough():
    """Test output node passes through state."""
    state: AgentState = {
        "user_id": "test_user",
        "thread_id": "test_thread",
        "recommendations": [
            Cocktail(
                name="Negroni",
                ingredients=["1 oz gin", "1 oz campari", "1 oz vermouth"],
                method="stir with ice",
                flavor_notes=["bitter", "herbal"],
                why_this_works="classic",
            )
        ],
        "confidence_score": 0.85,
        "clarification_question": None,
    }

    result = await output_node(state)

    # Output node returns empty dict
    assert result == {}
