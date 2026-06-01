"""Router for profile management: preferences, constraints, and recommendations via /api/*."""

from typing import Any
from fastapi import APIRouter, Depends

from src.storage.user_store import UserStore
from src.api.dependencies import get_graph, get_checkpointer, get_user_store, get_current_user
from src.api.schemas import (
    RecommendRequest,
    RecommendResponse,
    UpdatePreferencesRequest,
    UpdateConstraintsRequest,
    UserProfileResponse,
)
from src.api.services.recommendation_service import get_recommendations
from src.api.services.profile_service import (
    update_preferences,
    update_constraints,
    get_user_profile,
)

router = APIRouter(
    prefix="/api", tags=["profile"], dependencies=[Depends(get_current_user)]
)


@router.post("/recommend", response_model=RecommendResponse)
async def recommend(
    request: RecommendRequest,
    user: dict = Depends(get_current_user),
    graph: Any = Depends(get_graph),
    checkpointer: Any = Depends(get_checkpointer),
    user_store: UserStore = Depends(get_user_store),
) -> RecommendResponse:
    """
    Get cocktail recommendations for a user.

    Uses /api prefix (alternative to /v1/recommend).
    Seeds initial state with saved preferences and constraints from user store.
    """
    user_id = user["sub"]
    return await get_recommendations(request, user_id, graph, checkpointer, user_store)


@router.post("/update/profile", response_model=UserProfileResponse)
async def update_profile_preferences(
    request: UpdatePreferencesRequest,
    user: dict = Depends(get_current_user),
    user_store: UserStore = Depends(get_user_store),
) -> UserProfileResponse:
    """
    Update user preferences.

    Partial update: only provided fields are updated.
    Returns full user profile (preferences and constraints).
    """
    user_id = user["sub"]
    return await update_preferences(request, user_id, user_store)


@router.post("/update/constraints", response_model=UserProfileResponse)
async def update_profile_constraints(
    request: UpdateConstraintsRequest,
    user: dict = Depends(get_current_user),
    user_store: UserStore = Depends(get_user_store),
) -> UserProfileResponse:
    """
    Update user constraints.

    Partial update: only provided fields are updated.
    Returns full user profile (preferences and constraints).
    """
    user_id = user["sub"]
    return await update_constraints(request, user_id, user_store)


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    user: dict = Depends(get_current_user),
    user_store: UserStore = Depends(get_user_store),
) -> UserProfileResponse:
    """
    Get user profile (read-only).

    Returns preferences, constraints, and last update timestamp.
    """
    user_id = user["sub"]
    return await get_user_profile(user_id, user_store)
