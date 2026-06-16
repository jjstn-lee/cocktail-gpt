"""Recommendation subgraph: the original cocktail recommendation workflow."""

import os

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from loguru import logger

from src.state import AgentState
from src.nodes.ingest import make_ingest_node
from src.nodes.profile_builder import profile_builder
from src.nodes.preference_extractor import preference_extractor
from src.nodes.recommender import recommender
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
      recommender
        ↓
      output
        ↓
      END

    Args:
        checkpointer: BaseCheckpointSaver for state persistence
        user_store: Optional UserStore for Spotify token management
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("ingest", make_ingest_node(user_store))
    workflow.add_node("profile_builder", profile_builder)
    workflow.add_node("preference_extractor", preference_extractor)
    workflow.add_node("recommender", recommender)
    workflow.add_node("output", output_node)

    workflow.add_edge("ingest", "profile_builder")
    workflow.add_edge("profile_builder", "preference_extractor")
    workflow.add_edge("preference_extractor", "recommender")
    workflow.add_edge("recommender", "output")
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
