"""API tests for feedback endpoint."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app


def test_feedback_endpoint_exists():
    """Test that feedback endpoint exists."""
    client = TestClient(create_app())
    # Endpoint requires auth, so we expect 401 without auth
    response = client.post(
        "/v1/feedback",
        json={
            "user_id": "test_user",
            "thread_id": "thread_1",
            "cocktail_name": "Negroni",
            "rating": "up",
        },
    )
    assert response.status_code == 401
