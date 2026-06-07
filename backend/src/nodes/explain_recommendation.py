"""Explain recommendation node: generates explanation for why a cocktail was recommended."""

from loguru import logger
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from src.llm import get_llm
from src.prompts.base import GENERAL_SYSTEM_PROMPT
from src.state import AgentState


class ExplanationOutput(BaseModel):
    """Explanation of why a cocktail was recommended."""

    explanation: str  # 2-3 sentences explaining the match


EXPLAIN_RECOMMENDATION_SYSTEM_PROMPT = f"""{GENERAL_SYSTEM_PROMPT}

Your job is to explain why cocktails were recommended.
The supervisor has already determined the user wants to understand why their recommended cocktails were suggested.
Provide a clear, concise explanation (2-3 sentences) of why these cocktails are a good fit for them.

Consider:
- Their mood/occasion/vibe
- Their spirit and flavor preferences
- Any constraints (allergies, ABV limits)
- Why these specific cocktails are great matches for their profile

Focus on what makes THESE cocktails special for THEM.
If explaining multiple cocktails, you can mention what they have in common or how each serves a different aspect of their taste."""


async def explain_recommendation(state: AgentState) -> dict:
    """
    Generate explanation for why the recommended cocktail was suggested.

    Input: state["recommendations"], state["user_profile"], state["preferences"], state["constraints"]
    Output: {"explanation": str}
    """
    logger.debug("explain_recommendation: generating explanation")

    recommendations = state.get("recommendations", [])
    user_profile = state.get("user_profile")
    preferences = state.get("preferences")
    constraints = state.get("constraints")

    # Debug: print what we have in state
    print(f"[EXPLAIN_REC] State keys: {list(state.keys())}")
    print(f"[EXPLAIN_REC] Has recommendations: {bool(recommendations)}")
    if recommendations:
        print(f"[EXPLAIN_REC] Recommendations: {[c.name for c in recommendations]}")
    print(f"[EXPLAIN_REC] Latest message: {state.get('latest_message')}")
    print(f"[EXPLAIN_REC] Thread ID: {state.get('thread_id')}")

    if not recommendations:
        logger.warning("explain_recommendation: no recommendations to explain")
        return {
            "explanation": "No prior recommendations to explain. Would you like me to make a recommendation first?",
            "explanation_cocktail_names": [],
        }

    # Try to find all cocktails mentioned in the user's message
    latest_message = state.get("latest_message", "")
    requested_cocktails = []

    if latest_message:
        # Search for cocktail names in the message (case-insensitive)
        message_lower = latest_message.lower()
        for rec in recommendations:
            if rec.name.lower() in message_lower:
                requested_cocktails.append(rec)
                print(f"[EXPLAIN_REC] Found requested cocktail in message: {rec.name}")

    # If no specific cocktails mentioned, default to first recommendation
    if not requested_cocktails:
        requested_cocktails = [recommendations[0]]
        print(f"[EXPLAIN_REC] No specific cocktails in message, using default: {recommendations[0].name}")

    cocktail_names = [c.name for c in requested_cocktails]

    # Build context from user profile and preferences
    profile_dict = user_profile.model_dump() if user_profile else {}
    preferences_dict = preferences.model_dump() if preferences else {}
    constraints_dict = constraints.model_dump() if constraints else {}

    # Format cocktails section (one or multiple)
    cocktails_section = ""
    if len(requested_cocktails) == 1:
        c = requested_cocktails[0]
        cocktails_section = f"""Cocktail: {c.name}
Ingredients: {", ".join(c.ingredients)}
Flavor notes: {", ".join(c.flavor_notes)}"""
    else:
        cocktails_section = "Cocktails:\n"
        for c in requested_cocktails:
            cocktails_section += f"""- {c.name}: {", ".join(c.flavor_notes)}
"""

    context = f"""{cocktails_section}

User Profile:
- Mood: {profile_dict.get('mood', 'unknown')}
- Occasion: {profile_dict.get('occasion', 'unknown')}
- Vibe: {profile_dict.get('vibe', 'unknown')}
- Energy level: {profile_dict.get('energy_level', 'unknown')}

User Preferences:
- Preferred spirits: {preferences_dict.get('preferred_spirits', [])} {preferences_dict.get('genre_spirits', [])}
- Preferred flavors: {preferences_dict.get('preferred_flavors', [])}
- ABV preference: {preferences_dict.get('abv_preference', 'any')}
- Style preferences: {preferences_dict.get('style_preferences', [])}

User Constraints:
- Allergies: {constraints_dict.get('allergies', 'none')}
- Max ABV: {constraints_dict.get('max_abv', 'none')}
- Ingredients on hand: {constraints_dict.get('ingredients_on_hand', 'not specified')}"""

    llm = get_llm()
    explanation_llm = llm.with_structured_output(ExplanationOutput)

    # Build messages with conversation history
    message_history = state.get("message_history", [])
    messages = [SystemMessage(content=EXPLAIN_RECOMMENDATION_SYSTEM_PROMPT)]

    # Add message history (excluding current turn)
    if message_history and len(message_history) > 1:
        for msg in message_history[:-1]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(AIMessage(content=msg["content"]))

    # Add the context about cocktails and profile
    messages.append(HumanMessage(content=context))

    try:
        result = await explanation_llm.ainvoke(messages)
        print(f"[EXPLAIN_REC] Generated explanation for {cocktail_names}:")
        print(f"[EXPLAIN_REC] {result.explanation}")
        logger.info(
            "explain_recommendation: generated explanation",
            extra={"cocktails": cocktail_names, "explanation": result.explanation},
        )

        return_dict = {"explanation": result.explanation, "explanation_cocktail_names": cocktail_names}
        print(f"[EXPLAIN_REC] Returning: {return_dict}")
        return return_dict

    except Exception as e:
        logger.error("explain_recommendation: error generating explanation", extra={"error": str(e)})
        # Fallback explanation
        fallback = (
            f"I recommended {', '.join(cocktail_names)} because they combine your preferred "
            f"flavors ({', '.join(preferences_dict.get('preferred_flavors', ['balanced flavors']))}) "
            f"in a way that matches your style perfectly."
        )
        print(f"[EXPLAIN_REC] Using fallback explanation due to error: {str(e)}")
        print(f"[EXPLAIN_REC] {fallback}")
        return {"explanation": fallback, "explanation_cocktail_names": cocktail_names}
