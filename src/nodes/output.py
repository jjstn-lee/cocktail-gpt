"""Output node: formats the final state for API response."""

from loguru import logger

from src.state import AgentState


async def output_node(state: AgentState) -> dict:
    """
    Format and validate the final state.

    This is a passthrough node that ensures all expected fields are present
    and properly formatted for the API layer.

    Input: complete AgentState
    Output: empty dict (no state modifications)
    """
    logger.info("output_node: formatting final state for output")

    recommendations = state.get("recommendations", [])
    confidence_score = state.get("confidence_score", 0.0)
    clarification_question = state.get("clarification_question")

    logger.debug(
        "output_node: final state",
        extra={
            "recommendations_count": len(recommendations),
            "confidence_score": confidence_score,
            "needs_clarification": clarification_question is not None,
        },
    )

    return {}
