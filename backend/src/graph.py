"""LangGraph state machine for the cocktail recommendation agent."""

from typing import Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from loguru import logger

from src.state import AgentState
from src.config import CLARIFY_THRESHOLD
from src.nodes.ingest import make_ingest_node
from src.nodes.profile_builder import profile_builder
from src.nodes.preference_extractor import preference_extractor
from src.nodes.constraint_checker import constraint_checker
from src.nodes.recommender import recommender
from src.nodes.clarify import clarify
from src.nodes.output import output_node


def build_graph(checkpointer: BaseCheckpointSaver, user_store=None):
    """
    Build and compile the cocktail recommendation graph.

    Topology:
      ingest
        ↓
      profile_builder
        ↓
      preference_extractor
        ↓
      constraint_checker
        ↓
      recommender
        ↓
      [conditional] clarify (if confidence < CLARIFY_THRESHOLD)
        ↓
      output
        ↓
      END

    If clarification is needed and not yet used in this session, route to clarify,
    which then loops back to recommender. After clarification, always proceed to output.

    Args:
        checkpointer: BaseCheckpointSaver for state persistence
        user_store: Optional UserStore for Spotify token management
    """
    workflow = StateGraph(AgentState)

    # Add all nodes (ingest is created from factory with optional user_store)
    workflow.add_node("ingest", make_ingest_node(user_store))
    workflow.add_node("profile_builder", profile_builder)
    workflow.add_node("preference_extractor", preference_extractor)
    workflow.add_node("constraint_checker", constraint_checker)
    workflow.add_node("recommender", recommender)
    workflow.add_node("clarify", clarify)
    workflow.add_node("output", output_node)

    # Linear edges (ingest through constraint_checker)
    workflow.add_edge("ingest", "profile_builder")
    workflow.add_edge("profile_builder", "preference_extractor")
    workflow.add_edge("preference_extractor", "constraint_checker")
    workflow.add_edge("constraint_checker", "recommender")

    # Conditional edge after recommender
    def should_clarify(state: AgentState) -> Literal["clarify", "output"]:
        """Decide whether to ask for clarification based on confidence and prior usage."""
        confidence = state.get("confidence_score", 0.0)
        already_used = state.get("session_clarification_used", False)

        if confidence < CLARIFY_THRESHOLD and not already_used:
            logger.debug(
                "should_clarify: routing to clarify",
                extra={"confidence": confidence, "threshold": CLARIFY_THRESHOLD},
            )
            return "clarify"
        return "output"

    workflow.add_conditional_edges("recommender", should_clarify)

    # After clarify, loop back to recommender (not output directly)
    workflow.add_edge("clarify", "recommender")

    # From output to end
    workflow.add_edge("output", END)

    # Set entry point
    workflow.set_entry_point("ingest")

    # Compile with checkpointer for persistence
    logger.info("build_graph: compiling graph with checkpointer")
    compiled = workflow.compile(checkpointer=checkpointer)

    return compiled
