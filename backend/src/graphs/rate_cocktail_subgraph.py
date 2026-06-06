"""Rate cocktail subgraph: handles user feedback on recommendations."""

from langgraph.graph import StateGraph, END
from loguru import logger

from src.state import AgentState
from src.nodes.rate_cocktail import rate_cocktail
from src.nodes.output import output_node


def build_rate_cocktail_subgraph(checkpointer=None, user_store=None):
    """
    Build the rate cocktail subgraph.

    Topology:
      rate_cocktail
        ↓
      output
        ↓
      END

    This subgraph extracts feedback from the user message and records it.

    Args:
        checkpointer: Optional checkpointer (not used, but accepted for registry compatibility)
        user_store: Optional user store (not used, but accepted for registry compatibility)
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("rate_cocktail", rate_cocktail)
    workflow.add_node("output", output_node)
    workflow.set_entry_point("rate_cocktail")
    workflow.add_edge("rate_cocktail", "output")
    workflow.add_edge("output", END)

    logger.info("build_rate_cocktail_subgraph: compiling subgraph")
    compiled = workflow.compile()

    return compiled
