"""Pydantic schemas for the FastAPI layer."""

from typing import Literal
from pydantic import BaseModel

from src.state import Cocktail


# Request bodies


class RecommendRequest(BaseModel):
    """Request to generate cocktail recommendations."""

    user_id: str
    thread_id: str | None = None  # Omit to start a new session
    context_override: dict | None = None  # Optional one-off signal overrides


class ClarifyRequest(BaseModel):
    """Request to submit a clarification answer."""

    user_id: str
    thread_id: str
    answer: str


class FeedbackRequest(BaseModel):
    """Request to submit feedback on a cocktail."""

    user_id: str
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


class SessionSummary(BaseModel):
    """Summary of a user's session history."""

    user_id: str
    session_count: int
    last_run_at: str | None = None
    top_preferences: dict
