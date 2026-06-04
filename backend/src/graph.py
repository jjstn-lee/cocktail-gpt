"""LangGraph state machine for the cocktail recommendation agent.

Main graph with supervisor routing to subgraphs:
  supervisor
    ├→ recommendation_subgraph (if intent == "recommendation")
    └→ profile_management_subgraph (if intent == "profile_update")
"""

import os
from typing import Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from loguru import logger

from src.state import AgentState
from src.nodes.supervisor import supervisor, Intent
from src.graphs.recommendation_subgraph import build_recommendation_subgraph
from src.graphs.profile_management_subgraph import build_profile_management_subgraph


def build_graph(checkpointer: BaseCheckpointSaver, user_store=None):
    """
    Build and compile the main graph with supervisor routing.

    Topology:
      supervisor (classifies user intent)
        ├→ recommendation_subgraph (if intent == "recommendation")
        └→ profile_management_subgraph (if intent == "profile_update")
        ↓
      END

    The supervisor classifies the user's intent based on their message.
    - "recommendation": routes to the recommendation subgraph (ingest → ... → output)
    - "profile_update": routes to the profile management subgraph (profile_updater)

    Args:
        checkpointer: BaseCheckpointSaver for state persistence
        user_store: Optional UserStore for Spotify token management
    """
    workflow = StateGraph(AgentState)

    # Build subgraphs
    recommendation_subgraph = build_recommendation_subgraph(checkpointer, user_store)
    profile_management_subgraph = build_profile_management_subgraph()

    # Add supervisor node
    workflow.add_node("supervisor", supervisor)

    # Add subgraphs as nodes
    workflow.add_node("recommendation_subgraph", recommendation_subgraph)
    workflow.add_node("profile_management_subgraph", profile_management_subgraph)

    # Set entry point
    workflow.set_entry_point("supervisor")

    # Conditional routing from supervisor
    def route_intent(state: AgentState) -> str:
        """Route based on supervisor's intent classification."""
        intent = state.get("intent")
        print(f"[ROUTE_INTENT] Intent from state: {intent}")
        print(f"[ROUTE_INTENT] Comparing with: {Intent.PROFILE_UPDATE.value}")
        logger.debug("route_intent: routing based on intent", extra={"intent": intent})

        if intent == Intent.PROFILE_UPDATE.value:
            print(f"[ROUTE_INTENT] Routing to: profile_management_subgraph")
            return "profile_management_subgraph"
        print(f"[ROUTE_INTENT] Routing to: recommendation_subgraph")
        return "recommendation_subgraph"

    workflow.add_conditional_edges("supervisor", route_intent)

    # Both subgraphs lead to END
    workflow.add_edge("recommendation_subgraph", END)
    workflow.add_edge("profile_management_subgraph", END)

    # Configure msgpack to allow custom Pydantic models
    os.environ.setdefault(
        "LANGGRAPH_ALLOWED_MSGPACK_MODULES",
        "src.state:Cocktail,src.state:UserProfile,src.state:Preferences,src.state:Constraints,src.state:Feedback",
    )

    # Compile with checkpointer for persistence
    logger.info("build_graph: compiling main graph with supervisor and subgraphs")
    compiled = workflow.compile(checkpointer=checkpointer)

    return compiled
