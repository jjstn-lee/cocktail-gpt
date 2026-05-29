"""Middleware for the FastAPI app."""

import os
import uuid
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from loguru import logger


def add_middleware(app: FastAPI) -> None:
    """Register middleware in the correct order: CORS → RequestID → Auth."""

    # 1. CORS middleware
    cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
    if cors_origins == ["*"] and os.getenv("ENV") == "production":
        # Never use * in production
        cors_origins = []
        logger.warning("middleware: CORS_ORIGINS is * in production; using empty list")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins if cors_origins != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 2. Request ID middleware (custom)
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Log incoming request
        logger.info(
            "http_request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "request_id": request_id,
            },
        )

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # 3. Auth middleware (custom)
    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        # Skip auth for these paths
        skip_paths = {"/docs", "/openapi.json", "/redoc", "/healthz"}
        if request.url.path in skip_paths:
            return await call_next(request)

        api_key = os.getenv("API_KEY")
        if not api_key:
            logger.warning("auth_middleware: API_KEY not set; all requests will be rejected")
            return JSONResponse(
                {"error": "API not configured"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"error": "Unauthorized", "request_id": request.state.request_id},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        token = auth_header[7:]  # Remove "Bearer " prefix
        if token != api_key:
            logger.warning(
                "auth_middleware: invalid token",
                extra={"request_id": request.state.request_id},
            )
            return JSONResponse(
                {"error": "Unauthorized", "request_id": request.state.request_id},
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        return await call_next(request)
