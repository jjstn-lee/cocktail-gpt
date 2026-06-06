"""Explain recommendation subgraph: generates explanations for recommendations."""

from langgraph.graph import StateGraph, END
from loguru import logger

from src.state import AgentState
from src.nodes.explain_recommendation import explain_recommendation
from src.nodes.output import output_node


def build_explain_recommendation_subgraph(checkpointer=None, user_store=None):
    """
    Build the explain recommendation subgraph.

    Topology:
      explain_recommendation
        ↓
      output
        ↓
      END

    This subgraph generates an explanation for why a cocktail was recommended
    without re-running the full recommendation workflow.

    Args:
        checkpointer: Optional checkpointer (not used, but accepted for registry compatibility)
        user_store: Optional user store (not used, but accepted for registry compatibility)
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("explain_recommendation", explain_recommendation)
    workflow.add_node("output", output_node)
    workflow.set_entry_point("explain_recommendation")
    workflow.add_edge("explain_recommendation", "output")
    workflow.add_edge("output", END)

    logger.info("build_explain_recommendation_subgraph: compiling subgraph")
    compiled = workflow.compile()

    return compiled
