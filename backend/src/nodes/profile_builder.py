"""Profile builder node: synthesizes user profile from raw source data."""

import json
from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm
from src.state import AgentState, UserProfile
from src.prompts.profile import PROFILE_BUILDER_PROMPT, PROFILE_BUILDER_SYSTEM_PROMPT
from src.nodes.utils import extract_json_from_llm_response


async def profile_builder(state: AgentState) -> dict:
    """
    Build a synthesized user profile from raw ingested data.

    Input: state["raw_sources"]
    Output: {"user_profile": UserProfile}
    """
    logger.debug("profile_builder: building user profile from raw sources")

    raw_sources = state.get("raw_sources", {})
    print(f"[PROFILE_BUILDER] Received raw_sources: {list(raw_sources.keys())}")
    if not raw_sources:
        print(f"[PROFILE_BUILDER] ✗ NO RAW SOURCES AVAILABLE!")
        logger.warning("profile_builder: no raw sources available; creating empty profile")
        return {"user_profile": UserProfile()}

    # Format raw sources for the LLM
    sources_summary = json.dumps(
        {
            name: {
                "source": payload.get("source"),
                "signals": payload.get("signals", {}),
                "confidence": payload.get("confidence", 0.0),
            }
            for name, payload in raw_sources.items()
        },
        indent=2,
    )
    print(f"[PROFILE_BUILDER] Sources to send to LLM:")
    print(sources_summary)

    try:
        llm = get_llm()

        human_message_content = f"{PROFILE_BUILDER_PROMPT}\n\nUser data:\n{sources_summary}"
        print(f"[PROFILE_BUILDER] Full message to LLM:")
        print(f"[PROFILE_BUILDER] System: {PROFILE_BUILDER_SYSTEM_PROMPT[:100]}...")
        print(f"[PROFILE_BUILDER] Human prompt length: {len(human_message_content)} chars")
        print(f"[PROFILE_BUILDER] Human message preview:")
        print(human_message_content[:500])

        messages = [
            SystemMessage(content=PROFILE_BUILDER_SYSTEM_PROMPT),
            HumanMessage(content=human_message_content),
        ]

        response = await llm.ainvoke(messages)
        logger.debug("profile_builder: LLM response received")

        # Extract JSON from response (handles markdown code blocks and explanations)
        profile_dict = extract_json_from_llm_response(response.content)
        profile = UserProfile(**profile_dict)
        logger.info("profile_builder: profile synthesized", extra={"profile": profile})
        return {"user_profile": profile}
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("profile_builder: failed to parse profile", extra={"error": str(e)})
        return {"user_profile": UserProfile()}
    except Exception as e:
        logger.error("profile_builder: LLM call failed", extra={"error": str(e), "type": type(e).__name__})
        return {"user_profile": UserProfile()}
