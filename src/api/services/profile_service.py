"""Business logic for user profile management."""

from loguru import logger

from src.storage.user_store import UserStore
from src.state import Preferences, Constraints
from src.api.schemas import (
    UpdatePreferencesRequest,
    UpdateConstraintsRequest,
    UserProfileResponse,
)


async def update_preferences(
    request: UpdatePreferencesRequest,
    user_store: UserStore,
) -> UserProfileResponse:
    """
    Update user preferences (partial merge).

    Loads existing preferences, updates only provided fields, saves, and returns full profile.
    """
    logger.info("profile_service: updating preferences", extra={"user_id": request.user_id})

    existing = user_store.get_preferences(request.user_id) or Preferences()

    # Merge: only update fields that are not None
    merged = Preferences(
        preferred_spirits=request.preferred_spirits
        if request.preferred_spirits is not None
        else existing.preferred_spirits,
        preferred_flavors=request.preferred_flavors
        if request.preferred_flavors is not None
        else existing.preferred_flavors,
        abv_preference=request.abv_preference
        if request.abv_preference is not None
        else existing.abv_preference,
        style_preferences=request.style_preferences
        if request.style_preferences is not None
        else existing.style_preferences,
    )

    user_store.save_preferences(request.user_id, merged)

    # Load full profile to return
    prefs = user_store.get_preferences(request.user_id) or Preferences()
    constraints = user_store.get_constraints(request.user_id) or Constraints()
    data = user_store._load_user_file(request.user_id)

    return UserProfileResponse(
        user_id=request.user_id,
        preferences=prefs.model_dump(),
        constraints=constraints.model_dump(),
        updated_at=data.get("updated_at"),
    )


async def update_constraints(
    request: UpdateConstraintsRequest,
    user_store: UserStore,
) -> UserProfileResponse:
    """
    Update user constraints (partial merge).

    Loads existing constraints, updates only provided fields, saves, and returns full profile.
    """
    logger.info("profile_service: updating constraints", extra={"user_id": request.user_id})

    existing = user_store.get_constraints(request.user_id) or Constraints()

    # Merge: only update fields that are not None
    merged = Constraints(
        allergies=request.allergies if request.allergies is not None else existing.allergies,
        ingredients_on_hand=request.ingredients_on_hand
        if request.ingredients_on_hand is not None
        else existing.ingredients_on_hand,
        max_abv=request.max_abv if request.max_abv is not None else existing.max_abv,
    )

    user_store.save_constraints(request.user_id, merged)

    # Load full profile to return
    prefs = user_store.get_preferences(request.user_id) or Preferences()
    constraints = user_store.get_constraints(request.user_id) or Constraints()
    data = user_store._load_user_file(request.user_id)

    return UserProfileResponse(
        user_id=request.user_id,
        preferences=prefs.model_dump(),
        constraints=constraints.model_dump(),
        updated_at=data.get("updated_at"),
    )


async def get_user_profile(
    user_id: str,
    user_store: UserStore,
) -> UserProfileResponse:
    """
    Get user profile (read-only).

    Returns empty defaults for unknown users.
    """
    logger.info("profile_service: getting user profile", extra={"user_id": user_id})

    prefs = user_store.get_preferences(user_id) or Preferences()
    constraints = user_store.get_constraints(user_id) or Constraints()
    data = user_store._load_user_file(user_id)

    return UserProfileResponse(
        user_id=user_id,
        preferences=prefs.model_dump(),
        constraints=constraints.model_dump(),
        updated_at=data.get("updated_at"),
    )
