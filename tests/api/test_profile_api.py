"""Tests for profile management API endpoints (/api/*)."""

import json
import tempfile
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.api.services.profile_service import update_preferences, update_constraints, get_user_profile
from src.storage.user_store import UserStore
from src.state import Preferences, Constraints
from src.api.schemas import UpdatePreferencesRequest, UpdateConstraintsRequest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for user store."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def app(temp_dir):
    """Create FastAPI app with mocked graph and checkpointer."""
    app = create_app()

    # Mock graph and checkpointer
    app.state.graph = AsyncMock()
    app.state.checkpointer = AsyncMock()
    app.state.user_store = UserStore(base_dir=temp_dir)

    return app


@pytest.fixture
def client(app):
    """Create TestClient."""
    return TestClient(app)


def test_get_profile_empty_user(client):
    """Test getting profile for user with no stored data."""
    response = client.get("/api/profile/new_user", headers={"Authorization": "Bearer test_key"})

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "new_user"
    assert data["preferences"]["preferred_spirits"] == []
    assert data["constraints"]["allergies"] == []


def test_update_preferences_new_user(client):
    """Test updating preferences for a new user."""
    request_body = {
        "user_id": "test_user",
        "preferred_spirits": ["gin", "tequila"],
        "preferred_flavors": ["citrus", "herbal"],
    }

    response = client.post(
        "/api/update/profile",
        json=request_body,
        headers={"Authorization": "Bearer test_key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "test_user"
    assert data["preferences"]["preferred_spirits"] == ["gin", "tequila"]
    assert data["preferences"]["preferred_flavors"] == ["citrus", "herbal"]
    assert data["preferences"]["abv_preference"] is None


def test_update_preferences_partial(client):
    """Test partial preference update."""
    # First update
    client.post(
        "/api/update/profile",
        json={
            "user_id": "test_user",
            "preferred_spirits": ["gin"],
        },
        headers={"Authorization": "Bearer test_key"},
    )

    # Partial update (only ABV)
    response = client.post(
        "/api/update/profile",
        json={
            "user_id": "test_user",
            "abv_preference": "strong",
        },
        headers={"Authorization": "Bearer test_key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["preferences"]["preferred_spirits"] == ["gin"]  # Preserved
    assert data["preferences"]["abv_preference"] == "strong"  # Updated


def test_update_constraints_new_user(client):
    """Test updating constraints for a new user."""
    request_body = {
        "user_id": "test_user",
        "allergies": ["nuts", "dairy"],
        "max_abv": 20.0,
    }

    response = client.post(
        "/api/update/constraints",
        json=request_body,
        headers={"Authorization": "Bearer test_key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "test_user"
    assert data["constraints"]["allergies"] == ["nuts", "dairy"]
    assert data["constraints"]["max_abv"] == 20.0


def test_update_constraints_partial(client):
    """Test partial constraint update."""
    # First update
    client.post(
        "/api/update/constraints",
        json={
            "user_id": "test_user",
            "allergies": ["nuts"],
        },
        headers={"Authorization": "Bearer test_key"},
    )

    # Partial update (add max_abv)
    response = client.post(
        "/api/update/constraints",
        json={
            "user_id": "test_user",
            "max_abv": 15.0,
        },
        headers={"Authorization": "Bearer test_key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["constraints"]["allergies"] == ["nuts"]  # Preserved
    assert data["constraints"]["max_abv"] == 15.0  # Updated


def test_get_profile_after_updates(client):
    """Test retrieving profile after multiple updates."""
    # Update preferences
    client.post(
        "/api/update/profile",
        json={
            "user_id": "test_user",
            "preferred_spirits": ["vodka"],
        },
        headers={"Authorization": "Bearer test_key"},
    )

    # Update constraints
    client.post(
        "/api/update/constraints",
        json={
            "user_id": "test_user",
            "allergies": ["shellfish"],
        },
        headers={"Authorization": "Bearer test_key"},
    )

    # Get profile
    response = client.get(
        "/api/profile/test_user",
        headers={"Authorization": "Bearer test_key"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["preferences"]["preferred_spirits"] == ["vodka"]
    assert data["constraints"]["allergies"] == ["shellfish"]
    assert data["updated_at"] is not None


def test_auth_required(client):
    """Test that endpoints require authentication."""
    response = client.get("/api/profile/test_user")
    assert response.status_code == 401

    response = client.post(
        "/api/update/profile",
        json={
            "user_id": "test_user",
            "preferred_spirits": ["gin"],
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_profile_service_update_preferences():
    """Test profile service update_preferences function."""
    with tempfile.TemporaryDirectory() as temp_dir:
        user_store = UserStore(base_dir=temp_dir)

        request = UpdatePreferencesRequest(
            user_id="test_user",
            preferred_spirits=["gin"],
        )

        response = await update_preferences(request, user_store)

        assert response.user_id == "test_user"
        assert response.preferences["preferred_spirits"] == ["gin"]


@pytest.mark.asyncio
async def test_profile_service_update_constraints():
    """Test profile service update_constraints function."""
    with tempfile.TemporaryDirectory() as temp_dir:
        user_store = UserStore(base_dir=temp_dir)

        request = UpdateConstraintsRequest(
            user_id="test_user",
            allergies=["nuts"],
        )

        response = await update_constraints(request, user_store)

        assert response.user_id == "test_user"
        assert response.constraints["allergies"] == ["nuts"]


@pytest.mark.asyncio
async def test_profile_service_get_user_profile():
    """Test profile service get_user_profile function."""
    with tempfile.TemporaryDirectory() as temp_dir:
        user_store = UserStore(base_dir=temp_dir)

        # Save some data first
        prefs = Preferences(preferred_spirits=["vodka"])
        user_store.save_preferences("test_user", prefs)

        response = await get_user_profile("test_user", user_store)

        assert response.user_id == "test_user"
        assert response.preferences["preferred_spirits"] == ["vodka"]
