"""Browse by attribute subgraph: attribute-led cocktail exploration."""

from langgraph.graph import StateGraph, END
from loguru import logger

from src.state import AgentState
from src.nodes.browse_by_attribute import browse_by_attribute


def build_browse_by_attribute_subgraph(checkpointer=None, user_store=None):
    """
    Build the browse by attribute subgraph.

    Topology:
      browse_by_attribute
        ↓
      END

    This subgraph generates cocktail recommendations based on a user-specified attribute,
    flavor, ingredient, or style without applying personal preferences.

    Args:
        checkpointer: Optional checkpointer (not used, but accepted for registry compatibility)
        user_store: Optional user store (not used, but accepted for registry compatibility)
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("browse_by_attribute", browse_by_attribute)
    workflow.set_entry_point("browse_by_attribute")
    workflow.add_edge("browse_by_attribute", END)

    logger.info("build_browse_by_attribute_subgraph: compiling subgraph")
    compiled = workflow.compile()

    return compiled
