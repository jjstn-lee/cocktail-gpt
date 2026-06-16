"""Response builders for each intent type.

Each builder function converts final_state + context into a ChatResponse.
Registry-driven dispatch in chat_service.py calls these builders.
"""

from typing import Any
from datetime import datetime
from loguru import logger

from src.storage.user_store import UserStore
from src.state import Feedback, Preferences
from src.api.schemas import ChatResponse, CocktailOut


async def build_recommendation_response(
    final_state: dict[str, Any],
    thread_id: str,
    user_store: UserStore | None,
    user_id: str,
) -> ChatResponse:
    """Build recommendation intent response with cocktail suggestions."""
    recommendations = [
        CocktailOut(
            name=c.name,
            ingredients=c.ingredients,
            method=c.method,
            flavor_notes=c.flavor_notes,
            why_this_works=c.why_this_works,
        )
        for c in final_state.get("recommendations", [])
    ]

    if user_store:
        cocktail_names = [c.name for c in final_state.get("recommendations", [])]
        user_store.save_session_recommendations(user_id, thread_id, cocktail_names)
        user_store.increment_session_count(user_id)

    if recommendations:
        status = "✓ Crafted cocktail recommendations"
        message = f"I've selected **{len(recommendations)}** cocktail(s) that match your taste. Here they are:"
    else:
        status = "Looking for the perfect cocktail..."
        message = "Looking for the perfect cocktail based on your profile..."

    return ChatResponse(
        thread_id=thread_id,
        intent="recommendation",
        message=message,
        status=status,
        recommendations=recommendations,
        confidence_score=final_state.get("confidence_score", 0.0),
        rationale=final_state.get("rationale", ""),
        degraded=False,
    )


async def build_profile_update_response(
    final_state: dict[str, Any],
    thread_id: str,
    user_store: UserStore | None,
    user_id: str,
) -> ChatResponse:
    """Build profile_update intent response with profile changes summary."""
    profile_update_summary = final_state.get("profile_update_summary", "Profile updated.")

    # Ensure message has markdown formatting
    message = profile_update_summary if profile_update_summary else "Profile updated successfully."

    # Save updated preferences and constraints if user_store is available
    if user_store:
        prefs = final_state.get("preferences")
        if prefs:
            # Remove genre_spirits before saving (session-specific data)
            # Only save user-explicitly-set preferences to profile
            prefs_dict = prefs.model_dump()
            prefs_dict.pop("genre_spirits", None)  # Remove session-specific data
            clean_prefs = Preferences(**prefs_dict)
            user_store.save_preferences(user_id, clean_prefs)
            logger.info(
                "response_builders: saved preferences",
                extra={
                    "user_id": user_id,
                    "preferred_spirits": clean_prefs.preferred_spirits,
                    "preferred_flavors": clean_prefs.preferred_flavors,
                },
            )

        constraints = final_state.get("constraints")
        if constraints:
            user_store.save_constraints(user_id, constraints)
            logger.info(
                "response_builders: saved constraints",
                extra={"user_id": user_id, "constraints": constraints.model_dump()},
            )

    return ChatResponse(
        thread_id=thread_id,
        intent="profile_update",
        message=message,
        status="✓ Profile updated",
        profile_update_summary=profile_update_summary,
        degraded=False,
    )


async def build_rate_cocktail_response(
    final_state: dict[str, Any],
    thread_id: str,
    user_store: UserStore | None,
    user_id: str,
) -> ChatResponse:
    """Build rate_cocktail intent response acknowledging feedback."""
    rating_message = final_state.get("rate_cocktail_message", "Thanks for the feedback!")

    # Ensure message has markdown formatting
    if rating_message and not any(char in rating_message for char in ['**', '_', '#', '-', '•']):
        # Add emphasis to the message if it doesn't have markdown
        message = f"**Thanks for the feedback!** {rating_message}"
    else:
        message = rating_message

    # Save the most recent feedback entry to user_store if available
    if user_store:
        feedback_list = final_state.get("feedback", [])
        if feedback_list:
            # Get the last feedback entry (most recent)
            last_feedback = feedback_list[-1]
            # Convert Feedback object to dict if needed
            if isinstance(last_feedback, Feedback):
                feedback_dict = last_feedback.model_dump()
            else:
                feedback_dict = last_feedback
            # Add timestamp if not present
            if "timestamp" not in feedback_dict:
                feedback_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"

            user_store.save_feedback(user_id, feedback_dict)
            logger.info(
                "response_builders: saved feedback",
                extra={
                    "user_id": user_id,
                    "cocktail": feedback_dict.get("cocktail_name"),
                    "rating": feedback_dict.get("rating"),
                },
            )

    return ChatResponse(
        thread_id=thread_id,
        intent="rate_cocktail",
        message=message,
        status="✓ Feedback recorded",
        rating_message=rating_message,
        degraded=False,
    )


async def build_explain_recommendation_response(
    final_state: dict[str, Any],
    thread_id: str,
    user_store: UserStore | None,
    user_id: str,
) -> ChatResponse:
    """Build explain_recommendation intent response with explanation."""
    explanation = final_state.get("explanation", "I chose these cocktails based on your profile.")

    # Ensure message is populated
    message = explanation if explanation else "I chose these cocktails based on your profile."

    # Get the cocktails being explained (set by explain_recommendation node)
    cocktail_names = final_state.get("explanation_cocktail_names", [])
    explanation_cocktail = ", ".join(cocktail_names) if cocktail_names else None

    print(f"[RESPONSE_BUILDER] Building explain_recommendation response")
    print(f"[RESPONSE_BUILDER] Explanation: {explanation}")
    print(f"[RESPONSE_BUILDER] Cocktails: {cocktail_names}")

    response = ChatResponse(
        thread_id=thread_id,
        intent="explain_recommendation",
        message=message,
        status="✓ Here's the reasoning",
        explanation=explanation,
        explanation_cocktail=explanation_cocktail,
        degraded=False,
    )

    print(f"[RESPONSE_BUILDER] Response: {response.model_dump()}")

    return response


async def build_manage_restrictions_response(
    final_state: dict[str, Any],
    thread_id: str,
    user_store: UserStore | None,
    user_id: str,
) -> ChatResponse:
    """Build manage_restrictions intent response with restriction-aware recommendations."""
    recommendations = [
        CocktailOut(
            name=c.name,
            ingredients=c.ingredients,
            method=c.method,
            flavor_notes=c.flavor_notes,
            why_this_works=c.why_this_works,
        )
        for c in final_state.get("recommendations", [])
    ]

    restriction_summary = final_state.get("restriction_summary", "Your restriction has been noted.")

    # If recommendations list is empty, provide a helpful fallback message
    if not recommendations:
        message = "I couldn't find cocktails matching that restriction. Could you **adjust the restriction** or try something different?"
    else:
        # Ensure message has markdown formatting
        if restriction_summary and not any(char in restriction_summary for char in ['**', '_', '#', '-', '•']):
            message = f"**Restriction applied.** {restriction_summary}"
        else:
            message = restriction_summary

    status = "✓ Restriction applied" if recommendations else "⚠ No cocktails found"

    return ChatResponse(
        thread_id=thread_id,
        intent="manage_restrictions",
        message=message,
        status=status,
        recommendations=recommendations,
        restriction_summary=restriction_summary,
        degraded=False,
    )


async def build_retrieve_profile_response(
    final_state: dict[str, Any],
    thread_id: str,
    user_store: UserStore | None,
    user_id: str,
) -> ChatResponse:
    """Build retrieve_profile intent response with formatted profile summary."""
    profile_summary = final_state.get("profile_summary", "No profile data saved yet.")

    # Ensure message is populated
    message = profile_summary if profile_summary else "No profile data saved yet."

    return ChatResponse(
        thread_id=thread_id,
        intent="retrieve_profile",
        message=message,
        status="✓ Here's your profile",
        profile_summary=profile_summary,
        degraded=False,
    )


async def build_conversational_fallback_response(
    final_state: dict[str, Any],
    thread_id: str,
    user_store: UserStore | None,
    user_id: str,
) -> ChatResponse:
    """Build conversational_fallback intent response with helpful guidance."""
    fallback_message = final_state.get(
        "fallback_message",
        "I'm here to help! You can ask me for cocktail recommendations, update your preferences, or ask what I know about you.",
    )

    # Ensure message is populated
    message = fallback_message if fallback_message else "I'm here to help! How can I assist you today?"

    return ChatResponse(
        thread_id=thread_id,
        intent="conversational_fallback",
        message=message,
        status="💬 Let's chat",
        fallback_message=fallback_message,
        degraded=False,
    )


async def build_browse_by_attribute_response(
    final_state: dict[str, Any],
    thread_id: str,
    user_store: UserStore | None,
    user_id: str,
) -> ChatResponse:
    """Build browse_by_attribute intent response with KB-grounded attribute picks."""
    recommendations = [
        CocktailOut(
            name=c.name,
            ingredients=c.ingredients,
            method=c.method,
            flavor_notes=c.flavor_notes,
            why_this_works=c.why_this_works,
        )
        for c in final_state.get("recommendations", [])
    ]
    attribute = final_state.get("browse_attribute") or "that style"

    if recommendations:
        status = f"✓ Browsing by {attribute}"
        message = f"Here are **{len(recommendations)}** cocktail(s) matching **{attribute}**."
    else:
        status = f"⚠ No matches for {attribute}"
        message = (
            f"I couldn't find any cocktails matching **{attribute}** in my knowledgebase. "
            "Try a different attribute or ask for a personalized recommendation."
        )

    return ChatResponse(
        thread_id=thread_id,
        intent="browse_by_attribute",
        message=message,
        status=status,
        recommendations=recommendations,
        browse_attribute=attribute,
        degraded=False,
    )


async def build_self_information_response(
    final_state: dict[str, Any],
    thread_id: str,
    user_store: UserStore | None,
    user_id: str,
) -> ChatResponse:
    """Build self_information intent response with capability explanation."""
    self_info_message = final_state.get(
        "self_information_message",
        "I can recommend cocktails, manage your profile, browse by style, and provide feedback. I cannot order drinks or provide medical advice.",
    )

    # Ensure message is populated
    message = self_info_message if self_info_message else "Here's what I can help you with:"

    return ChatResponse(
        thread_id=thread_id,
        intent="self_information",
        message=message,
        status="ℹ️ Here's what I can do",
        self_information_message=self_info_message,
        degraded=False,
    )
