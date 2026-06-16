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
    """User's spirit and flavor preferences.

    NOTE: genre_spirits is session-specific (inferred from Spotify per session)
    and should NOT be persisted to the user profile. Only preferred_spirits,
    preferred_flavors, abv_preference, and style_preferences should be saved.
    """

    preferred_spirits: list[str] = []  # User-explicitly-set favorite spirits (persistent)
    genre_spirits: list[str] = []  # Spirits inferred from music (session-specific, NOT persisted)
    preferred_flavors: list[str] = []  # Persistent
    abv_preference: str | None = None  # e.g., "strong", "moderate", "light" (persistent)
    style_preferences: list[str] = []  # Persistent


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

    # Session and user tracking
    user_id: str
    thread_id: str
    latest_message: str | None  # Current user message (for supervisor routing)
    message_history: list[dict]  # Full conversation history: [{"role": "user" | "assistant", "content": str}]

    # Supervisor routing
    intent: str | None  # "recommendation" or "profile_update"

    # Data ingestion (recommendation subgraph)
    raw_sources: dict[str, Any]  # Keyed by source name (e.g., "spotify", "weather")

    # Profile and preferences
    user_profile: UserProfile | None
    preferences: Preferences | None
    constraints: Constraints | None

    # Profile updates (profile management subgraph)
    profile_update_summary: str | None  # Summary of applied updates

    # Recommendations (recommendation subgraph)
    recommendations: list[Cocktail]
    confidence_score: float
    rationale: str  # Top-pick explanation from recommender

    # History and feedback
    session_count: int
    feedback: list[Feedback]
    recommendation_history: list[dict]  # Past sessions [{session_id, cocktails, timestamp}]

    # Lightweight intent responses
    explanation: str | None  # Explanation for explain_recommendation intent
    explanation_cocktail_names: list[str]  # Names of cocktails being explained
    rate_cocktail_message: str | None  # Acknowledgment message for rate_cocktail intent
    profile_summary: str | None  # Formatted profile summary for retrieve_profile intent
    fallback_message: str | None  # Conversational response for ambiguous/unclear messages
    self_information_message: str | None  # Response for self_information intent
    browse_attribute: str | None  # Attribute label for browse_by_attribute intent
