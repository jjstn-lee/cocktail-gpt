"""Manage restrictions subgraph: temporary session-only restriction handling."""

from langgraph.graph import StateGraph, END
from loguru import logger

from src.state import AgentState
from src.nodes.manage_restrictions import manage_restrictions


def build_manage_restrictions_subgraph(checkpointer=None, user_store=None):
    """
    Build the manage restrictions subgraph.

    Topology:
      manage_restrictions
        ↓
      END

    This subgraph generates cocktail recommendations that respect a temporary,
    session-only restriction (e.g., "I'm driving", "no citrus", "low ABV")
    without saving the restriction to the user's profile.

    Args:
        checkpointer: Optional checkpointer (not used, but accepted for registry compatibility)
        user_store: Optional user store (not used, but accepted for registry compatibility)
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("manage_restrictions", manage_restrictions)
    workflow.set_entry_point("manage_restrictions")
    workflow.add_edge("manage_restrictions", END)

    logger.info("build_manage_restrictions_subgraph: compiling subgraph")
    compiled = workflow.compile()

    return compiled
