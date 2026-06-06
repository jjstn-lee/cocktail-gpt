"""Conversational fallback subgraph: handles ambiguous or unclear user messages."""

from langgraph.graph import StateGraph, END
from loguru import logger

from src.state import AgentState
from src.nodes.conversational_fallback import conversational_fallback
from src.nodes.output import output_node


def build_conversational_fallback_subgraph(checkpointer=None, user_store=None):
    """
    Build the conversational fallback subgraph.

    Topology:
      conversational_fallback
        ↓
      output
        ↓
      END

    This subgraph handles ambiguous or unclear user messages by generating
    a helpful, conversational response that guides the user toward useful actions.

    Args:
        checkpointer: Optional checkpointer (not used, but accepted for registry compatibility)
        user_store: Optional user store (not used, but accepted for registry compatibility)
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("conversational_fallback", conversational_fallback)
    workflow.add_node("output", output_node)
    workflow.set_entry_point("conversational_fallback")
    workflow.add_edge("conversational_fallback", "output")
    workflow.add_edge("output", END)

    logger.info("build_conversational_fallback_subgraph: compiling subgraph")
    compiled = workflow.compile()

    return compiled
