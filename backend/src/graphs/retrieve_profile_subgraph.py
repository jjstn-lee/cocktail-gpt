"""Retrieve profile subgraph: handles user requests to view their profile."""

from langgraph.graph import StateGraph, END
from loguru import logger

from src.state import AgentState
from src.nodes.retrieve_profile import retrieve_profile
from src.nodes.output import output_node


def build_retrieve_profile_subgraph(checkpointer=None, user_store=None):
    """
    Build the retrieve profile subgraph.

    Topology:
      retrieve_profile
        ↓
      output
        ↓
      END

    This subgraph formats and returns profile data saved to the user.

    Args:
        checkpointer: Optional checkpointer (not used, but accepted for registry compatibility)
        user_store: Optional user store (not used, but accepted for registry compatibility)
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("retrieve_profile", retrieve_profile)
    workflow.add_node("output", output_node)
    workflow.set_entry_point("retrieve_profile")
    workflow.add_edge("retrieve_profile", "output")
    workflow.add_edge("output", END)

    logger.info("build_retrieve_profile_subgraph: compiling subgraph")
    compiled = workflow.compile()

    return compiled
