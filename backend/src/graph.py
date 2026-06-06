"""LangGraph state machine for the cocktail recommendation agent.

Main graph with supervisor routing to subgraphs (registry-driven).
Registry maps intent → subgraph node name + builder.
"""

import os

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from loguru import logger

from src.state import AgentState
from src.nodes.supervisor import supervisor
from src.intent_registry import load_registry, get_default_intent


def build_graph(checkpointer: BaseCheckpointSaver, user_store=None):
    """
    Build and compile the main graph with supervisor routing.

    Registry-driven node registration and conditional routing.
    The intent registry (src/intent_registry.py) defines all intents,
    their subgraph builders, and response builders.

    Args:
        checkpointer: BaseCheckpointSaver for state persistence
        user_store: Optional UserStore for Spotify token management
    """
    workflow = StateGraph(AgentState)
    registry = load_registry()

    # 1. Register supervisor node
    workflow.add_node("supervisor", supervisor)

    # 2. Register subgraph nodes dynamically from registry
    for intent_key, defn in registry.items():
        kwargs = {}
        if defn.needs_checkpointer:
            kwargs["checkpointer"] = checkpointer
        if defn.needs_user_store:
            kwargs["user_store"] = user_store

        subgraph = defn.builder(**kwargs)
        workflow.add_node(defn.node_name, subgraph)
        logger.debug(
            "build_graph: registered subgraph",
            extra={
                "intent": intent_key,
                "node_name": defn.node_name,
                "needs_checkpointer": defn.needs_checkpointer,
                "needs_user_store": defn.needs_user_store,
            },
        )

    # Set entry point
    workflow.set_entry_point("supervisor")

    # 3. Build routing map from registry (compile-time validation)
    default_intent = get_default_intent()
    path_map = {intent: defn.node_name for intent, defn in registry.items()}

    def route_intent(state: AgentState) -> str:
        """Route based on supervisor's intent classification."""
        intent = state.get("intent")
        logger.debug("route_intent: routing based on intent", extra={"intent": intent})

        if intent not in path_map:
            logger.warning(
                "route_intent: unknown intent, falling back to default",
                extra={"intent": intent, "default": default_intent},
            )
            return default_intent

        return intent

    # 4. Add conditional edges with path_map for compile-time validation
    workflow.add_conditional_edges("supervisor", route_intent, path_map)

    # 5. All subgraph nodes lead to END
    for defn in registry.values():
        workflow.add_edge(defn.node_name, END)

    # Configure msgpack to allow custom Pydantic models
    os.environ.setdefault(
        "LANGGRAPH_ALLOWED_MSGPACK_MODULES",
        "src.state:Cocktail,src.state:UserProfile,src.state:Preferences,src.state:Constraints,src.state:Feedback",
    )

    # Compile with checkpointer for persistence
    logger.info(
        "build_graph: compiling main graph with supervisor and registry-based subgraphs",
        extra={"intents": list(registry.keys()), "default_intent": default_intent},
    )
    compiled = workflow.compile(checkpointer=checkpointer)

    return compiled
