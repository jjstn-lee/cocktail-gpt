#!/usr/bin/env python
"""Main entry point for the cocktail recommendation agent."""

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langgraph.graph import StateGraph
from loguru import logger

from src.nodes.ingest import ingest_node
from src.state import AgentState

# Load environment variables
load_dotenv()

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=os.getenv("LOG_LEVEL", "INFO"),
)


def create_graph():
    """Create and compile the cocktail recommendation graph.

    Returns:
        Compiled StateGraph ready for execution.
    """
    from src.memory.checkpointer import get_checkpointer
    from src.graph import build_graph

    checkpointer = get_checkpointer()
    return build_graph(checkpointer)


async def run_agent(user_id: str) -> dict:
    """Run the agent for a given user.

    Args:
        user_id: The user ID to fetch recommendations for.

    Returns:
        The final state after running the graph.
    """
    logger.info(f"Starting cocktail recommendation agent for user: {user_id}")

    # Create initial state
    initial_state: AgentState = {
        "user_id": user_id,
        "thread_id": "main_thread",
        "raw_sources": {},
        "user_profile": None,
        "preferences": None,
        "constraints": None,
        "recommendations": [],
        "confidence_score": 0.0,
        "clarification_question": None,
        "clarification_answer": None,
        "session_count": 1,
        "session_clarification_used": False,
        "feedback": [],
    }

    # Compile graph
    graph = create_graph()

    # Run agent
    logger.info("Invoking graph...")
    config = {"configurable": {"thread_id": "main_thread"}}
    final_state = await graph.ainvoke(initial_state, config=config)

    return final_state


def print_results(state: dict) -> None:
    """Pretty-print the agent results.

    Args:
        state: The final state dict from the graph.
    """
    print("\n" + "=" * 80)
    print("COCKTAIL RECOMMENDATION AGENT RESULTS")
    print("=" * 80)

    print(f"\nUser ID: {state.get('user_id')}")
    print(f"Session Count: {state.get('session_count')}")

    if state.get("raw_sources"):
        print(f"\nSources Ingested: {', '.join(state['raw_sources'].keys())}")
        print("\nSource Details:")
        for source_name, payload in state["raw_sources"].items():
            print(f"\n  {source_name.upper()}:")
            print(f"    Fetched: {payload.get('fetched_at')}")
            print(f"    Confidence: {payload.get('confidence', 0):.2f}")
            print(f"    Signals: {list(payload.get('signals', {}).keys())}")

            # Pretty-print signals
            signals = payload.get("signals", {})
            for signal_name, signal_data in signals.items():
                print(f"      {signal_name}:")
                if isinstance(signal_data, dict):
                    for key, value in signal_data.items():
                        if isinstance(value, (int, float)):
                            print(f"        {key}: {value:.2f}")
                        elif isinstance(value, list):
                            print(
                                f"        {key}: {value[:3]}{'...' if len(value) > 3 else ''}"
                            )
                        else:
                            print(f"        {key}: {value}")

    print(f"\nUser Profile: {state.get('user_profile')}")
    print(f"Preferences: {state.get('preferences')}")
    print(f"Constraints: {state.get('constraints')}")
    print(f"Recommendations: {len(state.get('recommendations', []))} items")
    print(f"Confidence Score: {state.get('confidence_score', 0):.2f}")

    print("\n" + "=" * 80 + "\n")


async def main() -> None:
    """Main entry point."""
    # Get user ID from command line or environment
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
    else:
        user_id = os.getenv("TEST_USER_ID", "test_user_123")

    logger.info(f"Using user_id: {user_id}")

    # Validate required environment variables
    required_vars = ["SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "OPENWEATHER_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        logger.warning( 
            f"Missing environment variables: {', '.join(missing_vars)}. "
            "Some data sources may fail gracefully."
        )

    if not os.getenv("SPOTIFY_CLIENT_ID"):
        logger.warning("SPOTIFY_CLIENT_ID not set; Spotify data will not be fetched")
    if not os.getenv("OPENWEATHER_API_KEY"):
        logger.warning("OPENWEATHER_API_KEY not set; Weather data will not be fetched")

    try:
        # Run the agent
        final_state = await run_agent(user_id)

        # Print results
        print_results(final_state)

        # Save results to file
        results_file = Path("results.json")
        with open(results_file, "w") as f:
            # Convert to JSON-serializable format
            recommendations = final_state.get("recommendations", [])
            json_state = {
                "user_id": final_state.get("user_id"),
                "thread_id": final_state.get("thread_id"),
                "session_count": final_state.get("session_count"),
                "sources_ingested": list(final_state.get("raw_sources", {}).keys()),
                "raw_sources": {
                    name: {
                        "source": payload.get("source"),
                        "fetched_at": payload.get("fetched_at"),
                        "confidence": payload.get("confidence"),
                        "signals": payload.get("signals"),
                    }
                    for name, payload in final_state.get("raw_sources", {}).items()
                },
                "user_profile": final_state.get("user_profile").model_dump() if final_state.get("user_profile") else None,
                "preferences": final_state.get("preferences").model_dump() if final_state.get("preferences") else None,
                "constraints": final_state.get("constraints").model_dump() if final_state.get("constraints") else None,
                "recommendations": [
                    {
                        "name": rec.name,
                        "ingredients": rec.ingredients,
                        "method": rec.method,
                        "flavor_notes": rec.flavor_notes,
                        "why_this_works": rec.why_this_works,
                    }
                    for rec in recommendations
                ],
                "confidence_score": final_state.get("confidence_score"),
                "rationale": final_state.get("rationale"),
                "clarification_question": final_state.get("clarification_question"),
            }
            json.dump(json_state, f, indent=2)

        logger.info(f"Results saved to {results_file}")

    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
