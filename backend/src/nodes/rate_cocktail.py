"""Rate cocktail node: extracts sentiment from user feedback and records it."""

from loguru import logger
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from src.llm import get_llm
from src.prompts.base import GENERAL_SYSTEM_PROMPT
from src.state import AgentState, Feedback


class FeedbackRating(BaseModel):
    """Extracted feedback from user message."""

    rating: int  # 1 for negative, 5 for positive
    conversational_response: str  # Friendly conversational acknowledgment of their feedback


RATE_COCKTAIL_SYSTEM_PROMPT = f"""{GENERAL_SYSTEM_PROMPT}

The supervisor has already determined this message is about rating/providing feedback on a previous recommendation.
Your job is to:
1. Extract whether the user loved (positive) or disliked (negative) the cocktail
2. Generate a warm acknowledgment of their feedback

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

Return JSON with:
- rating: 5 for positive feedback, 1 for negative feedback
- conversational_response: A natural, warm acknowledgment (1-2 sentences) like "That's fantastic! I'm so glad you enjoyed it!" or "Thanks for the feedback. I'll keep that in mind for next time!"""


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

    # Build messages with conversation history
    message_history = state.get("message_history", [])
    messages = [SystemMessage(content=RATE_COCKTAIL_SYSTEM_PROMPT)]

    # Add message history (excluding current turn)
    if message_history and len(message_history) > 1:
        for msg in message_history[:-1]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

    messages.append(HumanMessage(content=f"User message: {latest_message}"))

    try:
        result = await feedback_llm.ainvoke(messages)
        logger.debug(
            "rate_cocktail: extracted feedback",
            extra={"rating": result.rating, "conversational_response": result.conversational_response},
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
                "response": result.conversational_response,
            },
        )

        return {
            "feedback": updated_feedback,
            "rate_cocktail_message": result.conversational_response,
        }

    except Exception as e:
        logger.error("rate_cocktail: error extracting feedback", extra={"error": str(e)})
        return {
            "feedback": existing_feedback,
            "rate_cocktail_message": f"Error processing your feedback: {str(e)}",
        }
