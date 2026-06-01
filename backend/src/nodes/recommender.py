"""Recommender node: generates cocktail recommendations based on profile, preferences, and constraints."""

import json
from loguru import logger
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm
from src.state import AgentState, Cocktail
from src.prompts.recommender import RECOMMENDER_PROMPT, RECOMMENDER_SYSTEM_PROMPT


class RecommenderOutput(BaseModel):
    """Structured output from the recommender node."""

    recommendations: list[Cocktail]
    confidence_score: float
    rationale: str


async def recommender(state: AgentState) -> dict:
    """
    Generate cocktail recommendations based on user profile, preferences, and constraints.

    Input: state["user_profile"], state["preferences"], state["constraints"], state.get("clarification_answer")
    Output: {"recommendations": list[Cocktail], "confidence_score": float, "rationale": str}
    """
    logger.debug("recommender: generating recommendations")

    user_profile = state.get("user_profile")
    preferences = state.get("preferences")
    constraints = state.get("constraints")
    clarification_answer = state.get("clarification_answer")

    profile_dict = user_profile.model_dump() if user_profile else {}
    preferences_dict = preferences.model_dump() if preferences else {}
    constraints_dict = constraints.model_dump() if constraints else {}

    context = f"""User Profile: {json.dumps(profile_dict)}
    Preferences: {json.dumps(preferences_dict)}
    Constraints: {json.dumps(constraints_dict)}"""

    if clarification_answer:
        context += f"\nClarification Answer: {clarification_answer}"

    llm = get_llm()
    llm_with_structured = llm.with_structured_output(RecommenderOutput)

    messages = [
        SystemMessage(content=RECOMMENDER_SYSTEM_PROMPT),
        HumanMessage(content=f"{RECOMMENDER_PROMPT}\n\n{context}"),
    ]

    response = await llm_with_structured.ainvoke(messages)
    logger.info(
        "recommender: recommendations generated",
        extra={
            "count": len(response.recommendations),
            "confidence_score": response.confidence_score,
        },
    )

    return {
        "recommendations": response.recommendations,
        "confidence_score": response.confidence_score,
        "rationale": response.rationale,
    }
