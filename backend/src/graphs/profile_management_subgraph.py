"""Profile management subgraph: handles user profile updates via conversation."""

from langgraph.graph import StateGraph, END
from loguru import logger

from src.state import AgentState
from src.nodes.profile_updater import profile_updater


def build_profile_management_subgraph():
    """
    Build the profile management subgraph.

    Topology:
      profile_updater
        ↓
      END

    This subgraph extracts profile updates from the user message and applies them.
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("profile_updater", profile_updater)
    workflow.set_entry_point("profile_updater")
    workflow.add_edge("profile_updater", END)

    logger.info("build_profile_management_subgraph: compiling subgraph")
    compiled = workflow.compile()

    return compiled
