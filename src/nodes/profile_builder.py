"""Profile builder node: synthesizes user profile from raw source data."""

import json
from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm
from src.state import AgentState, UserProfile
from src.prompts.profile import PROFILE_BUILDER_PROMPT, PROFILE_BUILDER_SYSTEM_PROMPT


async def profile_builder(state: AgentState) -> dict:
    """
    Build a synthesized user profile from raw ingested data.

    Input: state["raw_sources"]
    Output: {"user_profile": UserProfile}
    """
    logger.debug("profile_builder: building user profile from raw sources")

    raw_sources = state.get("raw_sources", {})
    if not raw_sources:
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

    try:
        llm = get_llm()

        messages = [
            SystemMessage(content=PROFILE_BUILDER_SYSTEM_PROMPT),
            HumanMessage(content=f"{PROFILE_BUILDER_PROMPT}\n\nUser data:\n{sources_summary}"),
        ]

        response = await llm.ainvoke(messages)
        logger.debug("profile_builder: LLM response received")

        # Extract JSON from response (may be wrapped in markdown code block)
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:]  # Remove ```json
        if content.startswith("```"):
            content = content[3:]  # Remove ```
        if content.endswith("```"):
            content = content[:-3]  # Remove trailing ```
        content = content.strip()

        profile_dict = json.loads(content)
        profile = UserProfile(**profile_dict)
        logger.info("profile_builder: profile synthesized", extra={"profile": profile})
        return {"user_profile": profile}
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning("profile_builder: failed to parse profile", extra={"error": str(e)})
        return {"user_profile": UserProfile()}
    except Exception as e:
        logger.error("profile_builder: LLM call failed", extra={"error": str(e), "type": type(e).__name__})
        return {"user_profile": UserProfile()}
