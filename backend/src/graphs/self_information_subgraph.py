"""Self-information subgraph: explains agent capabilities and limitations."""

from langgraph.graph import StateGraph, END
from loguru import logger

from src.state import AgentState
from src.nodes.self_information import self_information
from src.nodes.output import output_node


def build_self_information_subgraph(checkpointer=None, user_store=None):
    """
    Build the self-information subgraph.

    Topology:
      self_information
        ↓
      output
        ↓
      END

    This subgraph explains what the agent can and cannot do in response to
    capability-related questions.

    Args:
        checkpointer: Optional checkpointer (not used, but accepted for registry compatibility)
        user_store: Optional user store (not used, but accepted for registry compatibility)
    """
    workflow = StateGraph(AgentState)

    workflow.add_node("self_information", self_information)
    workflow.add_node("output", output_node)
    workflow.set_entry_point("self_information")
    workflow.add_edge("self_information", "output")
    workflow.add_edge("output", END)

    logger.info("build_self_information_subgraph: compiling subgraph")
    compiled = workflow.compile()

    return compiled
