from typing import Any
from typing_extensions import TypedDict
from pydantic import BaseModel


class Cocktail(BaseModel):
    """A recommended cocktail."""

    name: str
    ingredients: list[str]
    method: str
    flavor_notes: list[str]
    why_this_works: str


class UserProfile(BaseModel):
    """Synthesized user profile from ingested data."""

    mood: str | None = None
    occasion: str | None = None
    vibe: str | None = None
    energy_level: float | None = None  # 0–1


class Preferences(BaseModel):
    """User's spirit and flavor preferences."""

    preferred_spirits: list[str] = []
    preferred_flavors: list[str] = []
    abv_preference: str | None = None  # e.g., "strong", "moderate", "light"
    style_preferences: list[str] = []


class Constraints(BaseModel):
    """User's constraints."""

    allergies: list[str] = []
    ingredients_on_hand: list[str] = []
    max_abv: float | None = None


class Feedback(BaseModel):
    """User feedback on a recommendation."""

    cocktail_name: str
    session_id: str
    rating: int  # 1 (thumbs down) or 5 (thumbs up)


class AgentState(TypedDict, total=False):
    """The graph state for cocktail recommendations."""

    user_id: str
    thread_id: str
    raw_sources: dict[str, Any]  # Keyed by source name (e.g., "spotify", "weather")
    user_profile: UserProfile | None
    preferences: Preferences | None
    constraints: Constraints | None
    recommendations: list[Cocktail]
    confidence_score: float
    clarification_question: str | None
    clarification_answer: str | None
    session_count: int
    session_clarification_used: bool  # Cap clarification at one round
    feedback: list[Feedback]
