"""FastAPI dependency injection for graph, checkpointer, and user store."""

import os
import httpx
from fastapi import Request, Depends, HTTPException, status
from loguru import logger

from src.storage.user_store import UserStore


async def get_current_user(request: Request) -> dict:
    """
    Validate Google ID token from Authorization header.

    Returns user dict with 'sub' (user ID) and 'email'.
    Raises HTTP 401 if token is invalid or missing.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )

    token = auth_header[7:]  # Remove "Bearer " prefix
    google_client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not google_client_id:
        logger.error("GOOGLE_CLIENT_ID not configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": token},
            )
            data = response.json()

            # Check for errors in response
            if response.status_code != 200 or "error" in data:
                logger.warning(
                    "get_current_user: invalid token",
                    extra={"request_id": getattr(request.state, "request_id", "unknown")},
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorized",
                )

            # Validate audience matches our client ID
            if data.get("aud") != google_client_id:
                logger.warning(
                    "get_current_user: audience mismatch",
                    extra={"request_id": getattr(request.state, "request_id", "unknown")},
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorized",
                )

            return {
                "sub": data.get("sub"),
                "email": data.get("email"),
            }
    except httpx.RequestError as e:
        logger.error(
            "get_current_user: request failed",
            extra={
                "request_id": getattr(request.state, "request_id", "unknown"),
                "error": str(e),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


def get_graph(request: Request):
    """Get the compiled LangGraph from app state."""
    return request.app.state.graph


def get_checkpointer(request: Request):
    """Get the checkpointer from app state."""
    return request.app.state.checkpointer


def get_user_store(request: Request) -> UserStore:
    """Get the user store from app state."""
    return request.app.state.user_store
