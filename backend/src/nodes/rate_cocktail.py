"""Rate cocktail node: extracts sentiment from user feedback and records it."""

from loguru import logger
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage

from src.llm import get_llm
from src.state import AgentState, Feedback


class FeedbackRating(BaseModel):
    """Extracted feedback from user message."""

    rating: int  # 1 for negative, 5 for positive
    explanation: str  # Brief explanation of the rating


RATE_COCKTAIL_SYSTEM_PROMPT = """You are a feedback extraction assistant for a cocktail recommendation agent.
The supervisor has already determined this message is about rating/providing feedback on a previous recommendation.
Your job is to extract the user's sentiment (positive or negative) from their message.

Examples of positive feedback:
- "I loved that!"
- "That was perfect"
- "Great recommendation"
- "That worked really well"

Examples of negative feedback:
- "That was too bitter"
- "Not my style"
- "Didn't like it"
- "That wasn't good"

Extract from the user's message and return JSON with:
- rating: 5 for positive feedback, 1 for negative feedback
- explanation: brief summary of the sentiment

Be generous in interpretation - if the user says anything positive about the cocktail, rate it 5.
If they say anything negative, rate it 1."""


async def rate_cocktail(state: AgentState) -> dict:
    """
    Extract feedback sentiment from user message and record it.

    Input: state["latest_message"], state["recommendations"], state["feedback"], state["thread_id"]
    Output: {"feedback": updated feedback list}
    """
    logger.debug("rate_cocktail: extracting feedback sentiment")

    latest_message = state.get("latest_message")
    recommendations = state.get("recommendations", [])
    existing_feedback = state.get("feedback", [])
    thread_id = state.get("thread_id")

    if not latest_message:
        logger.warning("rate_cocktail: no latest_message in state")
        return {"feedback": existing_feedback}

    if not recommendations:
        logger.warning("rate_cocktail: no prior recommendations to rate")
        return {
            "feedback": existing_feedback,
            "rate_cocktail_message": "No prior recommendations to rate.",
        }

    llm = get_llm()
    feedback_llm = llm.with_structured_output(FeedbackRating)

    messages = [
        SystemMessage(content=RATE_COCKTAIL_SYSTEM_PROMPT),
        HumanMessage(content=f"User message: {latest_message}"),
    ]

    try:
        result = await feedback_llm.ainvoke(messages)
        logger.debug(
            "rate_cocktail: extracted feedback",
            extra={"rating": result.rating, "explanation": result.explanation},
        )

        # Get the last recommendation
        last_cocktail = recommendations[0]  # Top recommendation

        # Create feedback entry
        new_feedback = Feedback(
            cocktail_name=last_cocktail.name,
            session_id=thread_id,
            rating=result.rating,
        )

        # Append to feedback list
        updated_feedback = existing_feedback + [new_feedback]

        logger.info(
            "rate_cocktail: feedback recorded",
            extra={
                "cocktail": last_cocktail.name,
                "rating": result.rating,
                "explanation": result.explanation,
            },
        )

        return {
            "feedback": updated_feedback,
            "rate_cocktail_message": f"Thanks for the feedback on {last_cocktail.name}! {result.explanation}",
        }

    except Exception as e:
        logger.error("rate_cocktail: error extracting feedback", extra={"error": str(e)})
        return {
            "feedback": existing_feedback,
            "rate_cocktail_message": f"Error processing your feedback: {str(e)}",
        }
