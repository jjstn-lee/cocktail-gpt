"""Recommendation subgraph: the original cocktail recommendation workflow."""

import os
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


def build_recommendation_subgraph(checkpointer: BaseCheckpointSaver, user_store=None):
    """
    Build the recommendation subgraph (original cocktail recommendation workflow).

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

    # Configure msgpack to allow custom Pydantic models
    # (Allows deserialization without warnings)
    os.environ.setdefault(
        "LANGGRAPH_ALLOWED_MSGPACK_MODULES",
        "src.state:Cocktail,src.state:UserProfile,src.state:Preferences,src.state:Constraints,src.state:Feedback",
    )

    # Compile with checkpointer for persistence
    logger.info("build_recommendation_subgraph: compiling subgraph with checkpointer")
    compiled = workflow.compile(checkpointer=checkpointer)

    return compiled
