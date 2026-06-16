"""Central registry mapping intents to their subgraph definitions.

This is the single source of truth for intent routing. To add a new intent:
1. Create the subgraph builder in src/graphs/
2. Add an IntentDefinition entry here with the builder function
3. Add a corresponding Intent enum value in src/nodes/supervisor.py
4. The supervisor will validate that enum and registry are in sync on startup
"""

from dataclasses import dataclass
from typing import Callable, Any
from loguru import logger


@dataclass
class IntentDefinition:
    """Definition of an intent: how to route it and what response builder to use."""

    node_name: str  # StateGraph node name (must be unique)
    builder: Callable[..., Any]  # Subgraph factory function
    response_builder: Callable[..., Any]  # Response builder function
    needs_checkpointer: bool = False
    needs_user_store: bool = False
    default: bool = False  # Fallback when intent is unknown or defaults to this


def _get_registry() -> dict[str, "IntentDefinition"]:
    """
    Lazy-load registry to avoid circular imports at module level.
    Called once on first access, then cached.
    """
    from src.graphs.recommendation_subgraph import build_recommendation_subgraph
    from src.graphs.profile_management_subgraph import build_profile_management_subgraph
    from src.graphs.rate_cocktail_subgraph import build_rate_cocktail_subgraph
    from src.graphs.explain_recommendation_subgraph import build_explain_recommendation_subgraph
    from src.graphs.manage_restrictions_subgraph import build_manage_restrictions_subgraph
    from src.graphs.retrieve_profile_subgraph import build_retrieve_profile_subgraph
    from src.graphs.conversational_fallback_subgraph import build_conversational_fallback_subgraph
    from src.graphs.self_information_subgraph import build_self_information_subgraph
    from src.graphs.browse_by_attribute_subgraph import build_browse_by_attribute_subgraph
    from src.api.services.response_builders import (
        build_recommendation_response,
        build_profile_update_response,
        build_rate_cocktail_response,
        build_explain_recommendation_response,
        build_manage_restrictions_response,
        build_retrieve_profile_response,
        build_conversational_fallback_response,
        build_self_information_response,
        build_browse_by_attribute_response,
    )

    return {
        "recommendation": IntentDefinition(
            node_name="recommendation_subgraph",
            builder=build_recommendation_subgraph,
            response_builder=build_recommendation_response,
            needs_checkpointer=True,
            needs_user_store=True,
            default=True,
        ),
        "profile_update": IntentDefinition(
            node_name="profile_management_subgraph",
            builder=build_profile_management_subgraph,
            response_builder=build_profile_update_response,
            needs_checkpointer=False,
            needs_user_store=False,  # Subgraph builder doesn't need it; response builder does
        ),
        "rate_cocktail": IntentDefinition(
            node_name="rate_cocktail",
            builder=build_rate_cocktail_subgraph,
            response_builder=build_rate_cocktail_response,
            needs_checkpointer=True,
            needs_user_store=True,
        ),
        "explain_recommendation": IntentDefinition(
            node_name="explain_recommendation",
            builder=build_explain_recommendation_subgraph,
            response_builder=build_explain_recommendation_response,
            needs_checkpointer=True,
            needs_user_store=False,
        ),
        "manage_restrictions": IntentDefinition(
            node_name="manage_restrictions",
            builder=build_manage_restrictions_subgraph,
            response_builder=build_manage_restrictions_response,
            needs_checkpointer=False,
            needs_user_store=False,
        ),
        "retrieve_profile": IntentDefinition(
            node_name="retrieve_profile",
            builder=build_retrieve_profile_subgraph,
            response_builder=build_retrieve_profile_response,
            needs_checkpointer=False,
            needs_user_store=False,
        ),
        "conversational_fallback": IntentDefinition(
            node_name="conversational_fallback_subgraph",
            builder=build_conversational_fallback_subgraph,
            response_builder=build_conversational_fallback_response,
            needs_checkpointer=False,
            needs_user_store=False,
        ),
        "self_information": IntentDefinition(
            node_name="self_information_subgraph",
            builder=build_self_information_subgraph,
            response_builder=build_self_information_response,
            needs_checkpointer=False,
            needs_user_store=False,
        ),
        "browse_by_attribute": IntentDefinition(
            node_name="browse_by_attribute_subgraph",
            builder=build_browse_by_attribute_subgraph,
            response_builder=build_browse_by_attribute_response,
            needs_checkpointer=False,
            needs_user_store=False,
        ),
    }


# Eagerly-evaluated registry (called once at import of graph.py)
INTENT_REGISTRY: dict[str, IntentDefinition] = {}


def load_registry() -> dict[str, IntentDefinition]:
    """Load the intent registry (cached after first call)."""
    global INTENT_REGISTRY
    if not INTENT_REGISTRY:
        INTENT_REGISTRY = _get_registry()
        logger.debug(
            "intent_registry: loaded",
            extra={"intents": list(INTENT_REGISTRY.keys())},
        )
    return INTENT_REGISTRY


def get_default_intent() -> str:
    """Get the default intent key (for unknown/missing intents)."""
    registry = load_registry()
    for intent_key, defn in registry.items():
        if defn.default:
            return intent_key
    # Fallback if no default marked (should not happen in normal operation)
    return "recommendation"
