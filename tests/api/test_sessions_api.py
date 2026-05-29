"""API tests for sessions endpoint."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import create_app


def test_sessions_endpoint_exists():
    """Test that sessions endpoint exists."""
    client = TestClient(create_app())
    # Endpoint requires auth, so we expect 401 without auth
    response = client.get("/v1/sessions/test_user")
    assert response.status_code == 401
