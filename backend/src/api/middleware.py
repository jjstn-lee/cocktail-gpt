"""Middleware for the FastAPI app."""

import os
import uuid
from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from loguru import logger


def add_middleware(app: FastAPI) -> None:
    """Register middleware in the correct order: CORS → RequestID."""

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
