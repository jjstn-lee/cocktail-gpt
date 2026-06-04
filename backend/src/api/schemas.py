"""Pydantic schemas for the FastAPI layer."""

from typing import Literal
from pydantic import BaseModel

from src.state import Cocktail, Preferences, Constraints


# Request bodies


class RecommendRequest(BaseModel):
    """Request to generate cocktail recommendations."""

    thread_id: str | None = None  # Omit to start a new session
    context_override: dict | None = None  # Optional one-off signal overrides
    message: str | None = None  # Optional user message (defaults to "recommendation" intent)


class ClarifyRequest(BaseModel):
    """Request to submit a clarification answer."""

    thread_id: str
    answer: str


class FeedbackRequest(BaseModel):
    """Request to submit feedback on a cocktail."""

    thread_id: str
    cocktail_name: str
    rating: Literal["up", "down"]
    notes: str | None = None


# Response bodies


class CocktailOut(BaseModel):
    """A recommended cocktail for API output."""

    name: str
    ingredients: list[str]
    method: str
    flavor_notes: list[str]
    why_this_works: str


class RecommendResponse(BaseModel):
    """Response with cocktail recommendations."""

    thread_id: str
    recommendations: list[CocktailOut]
    confidence_score: float
    rationale: str
    needs_clarification: bool
    clarification_question: str | None = None
    degraded: bool = False  # True if any source failed


class FeedbackResponse(BaseModel):
    """Response after submitting feedback."""

    accepted: bool


# Conversational chat (supervisor routing)


class ChatRequest(BaseModel):
    """Request for conversational interaction with the agent."""

    message: str  # User's message (e.g., "give me a cocktail" or "I like gin")
    thread_id: str | None = None  # Omit to start a new session


class ChatResponse(BaseModel):
    """Response from conversational interaction (can be recommendations or profile update)."""

    thread_id: str
    intent: Literal["recommendation", "profile_update"]
    # For recommendations
    recommendations: list[CocktailOut] = []
    confidence_score: float | None = None
    rationale: str | None = None
    needs_clarification: bool = False
    clarification_question: str | None = None
    # For profile updates
    profile_update_summary: str | None = None
    # Metadata
    degraded: bool = False  # True if any source failed


class SessionSummary(BaseModel):
    """Summary of a user's session history."""

    user_id: str
    session_count: int
    last_run_at: str | None = None
    top_preferences: dict


# Profile management


class UpdatePreferencesRequest(BaseModel):
    """Request to update user preferences."""

    preferred_spirits: list[str] | None = None
    preferred_flavors: list[str] | None = None
    abv_preference: str | None = None
    style_preferences: list[str] | None = None


class UpdateConstraintsRequest(BaseModel):
    """Request to update user constraints."""

    allergies: list[str] | None = None
    ingredients_on_hand: list[str] | None = None
    max_abv: float | None = None


class UserProfileResponse(BaseModel):
    """Response with full user profile (preferences and constraints)."""

    user_id: str
    preferences: dict
    constraints: dict
    updated_at: str | None = None


# Spotify OAuth


class SpotifyStatusResponse(BaseModel):
    """Response with Spotify connection status."""

    connected: bool
    connected_at: str | None = None
    scopes: list[str] = []
