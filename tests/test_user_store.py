"""Tests for UserStore persistence."""

import json
import tempfile
from pathlib import Path

import pytest

from src.storage.user_store import UserStore
from src.state import Preferences, Constraints


@pytest.fixture
def temp_dir():
    """Create a temporary directory for user store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_user_store_init(temp_dir):
    """Test UserStore initialization."""
    store = UserStore(base_dir=temp_dir)
    assert Path(temp_dir).exists()


def test_sanitize_user_id():
    """Test user ID sanitization."""
    store = UserStore()

    assert store._sanitize_user_id("user@123") == "user_123"
    assert store._sanitize_user_id("user/path/123") == "user_path_123"
    assert store._sanitize_user_id("user_123") == "user_123"
    assert store._sanitize_user_id("user-123") == "user-123"


def test_save_and_get_preferences(temp_dir):
    """Test saving and retrieving preferences."""
    store = UserStore(base_dir=temp_dir)
    user_id = "test_user"

    prefs = Preferences(
        preferred_spirits=["gin", "tequila"],
        preferred_flavors=["citrus", "herbal"],
        abv_preference="moderate",
        style_preferences=["sour"],
    )

    store.save_preferences(user_id, prefs)
    retrieved = store.get_preferences(user_id)

    assert retrieved is not None
    assert retrieved.preferred_spirits == ["gin", "tequila"]
    assert retrieved.preferred_flavors == ["citrus", "herbal"]
    assert retrieved.abv_preference == "moderate"
    assert retrieved.style_preferences == ["sour"]


def test_save_and_get_constraints(temp_dir):
    """Test saving and retrieving constraints."""
    store = UserStore(base_dir=temp_dir)
    user_id = "test_user"

    constraints = Constraints(
        allergies=["nuts", "dairy"],
        ingredients_on_hand=["vodka", "lime"],
        max_abv=20.0,
    )

    store.save_constraints(user_id, constraints)
    retrieved = store.get_constraints(user_id)

    assert retrieved is not None
    assert retrieved.allergies == ["nuts", "dairy"]
    assert retrieved.ingredients_on_hand == ["vodka", "lime"]
    assert retrieved.max_abv == 20.0


def test_merge_preferences(temp_dir):
    """Test partial preference updates (merge)."""
    store = UserStore(base_dir=temp_dir)
    user_id = "test_user"

    # Save initial preferences
    prefs1 = Preferences(preferred_spirits=["gin"], preferred_flavors=["citrus"])
    store.save_preferences(user_id, prefs1)

    # Update with partial preferences
    prefs2 = Preferences(
        preferred_spirits=["gin", "vodka"],
        preferred_flavors=["citrus"],
        abv_preference="strong",
    )
    store.save_preferences(user_id, prefs2)

    # Verify the update
    retrieved = store.get_preferences(user_id)
    assert retrieved.preferred_spirits == ["gin", "vodka"]
    assert retrieved.abv_preference == "strong"


def test_get_nonexistent_user(temp_dir):
    """Test getting preferences/constraints for nonexistent user."""
    store = UserStore(base_dir=temp_dir)

    assert store.get_preferences("nonexistent") is None
    assert store.get_constraints("nonexistent") is None


def test_clear_user_data(temp_dir):
    """Test clearing user data."""
    store = UserStore(base_dir=temp_dir)
    user_id = "test_user"

    prefs = Preferences(preferred_spirits=["gin"])
    store.save_preferences(user_id, prefs)

    # Verify it was saved
    assert store.get_preferences(user_id) is not None

    # Clear and verify deletion
    store.clear(user_id)
    assert store.get_preferences(user_id) is None


def test_updated_at_timestamp(temp_dir):
    """Test that updated_at timestamp is set."""
    store = UserStore(base_dir=temp_dir)
    user_id = "test_user"

    prefs = Preferences(preferred_spirits=["gin"])
    store.save_preferences(user_id, prefs)

    data = store._load_user_file(user_id)
    assert data.get("updated_at") is not None
    assert data["updated_at"].endswith("Z")  # ISO 8601 UTC


def test_file_persists_across_instances(temp_dir):
    """Test that data persists across UserStore instances."""
    # Save with first instance
    store1 = UserStore(base_dir=temp_dir)
    prefs = Preferences(preferred_spirits=["gin"])
    store1.save_preferences("test_user", prefs)

    # Load with second instance
    store2 = UserStore(base_dir=temp_dir)
    retrieved = store2.get_preferences("test_user")

    assert retrieved is not None
    assert retrieved.preferred_spirits == ["gin"]
