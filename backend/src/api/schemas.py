"""Pydantic schemas for the FastAPI layer."""

from typing import Literal
from pydantic import BaseModel


class CocktailOut(BaseModel):
    """A recommended cocktail for API output."""

    name: str
    ingredients: list[str]
    method: str
    flavor_notes: list[str]
    why_this_works: str


# Conversational chat (supervisor routing)


class ChatRequest(BaseModel):
    """Request for conversational interaction with the agent."""

    message: str  # User's message (e.g., "give me a cocktail" or "I like gin")
    thread_id: str | None = None  # Omit to start a new session


class ChatResponse(BaseModel):
    """Response from conversational interaction (can be recommendations, profile update, feedback, or explanation)."""

    thread_id: str
    intent: Literal["recommendation", "profile_update", "rate_cocktail", "explain_recommendation", "manage_restrictions", "retrieve_profile", "conversational_fallback", "self_information"]
    message: str  # Main text message to display
    status: str  # Status message describing what was done (e.g., "Crafted cocktail recommendations")
    # For recommendations
    recommendations: list[CocktailOut] = []
    confidence_score: float | None = None
    rationale: str | None = None
    needs_clarification: bool = False
    clarification_question: str | None = None
    # For profile updates
    profile_update_summary: str | None = None
    # For rate_cocktail
    rating_message: str | None = None
    # For explain_recommendation
    explanation: str | None = None
    explanation_cocktail: str | None = None  # Name of cocktail being explained
    # For manage_restrictions
    restriction_summary: str | None = None  # e.g., "Got it — keeping it alcohol-free tonight."
    # For retrieve_profile
    profile_summary: str | None = None  # Formatted profile summary
    # For conversational_fallback
    fallback_message: str | None = None  # Conversational response for ambiguous messages
    # For self_information
    self_information_message: str | None = None  # Explanation of agent capabilities
    # Metadata
    degraded: bool = False  # True if any source failed


# Spotify OAuth


class SpotifyStatusResponse(BaseModel):
    """Response with Spotify connection status."""

    connected: bool
    connected_at: str | None = None
    scopes: list[str] = []
