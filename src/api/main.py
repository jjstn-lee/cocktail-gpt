"""FastAPI app factory for the cocktail recommendation service."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger

from src.graph import build_graph
from src.memory.checkpointer import get_checkpointer
from src.api.middleware import add_middleware


class SourceUnavailableError(Exception):
    """Raised when a data source is unavailable."""

    pass


class GraphExecutionError(Exception):
    """Raised when graph execution fails unrecoverably."""

    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for app startup and shutdown.

    Initializes the graph and checkpointer on startup,
    tears them down on shutdown.
    """
    # Startup
    logger.info("app: starting up")
    app.state.checkpointer = get_checkpointer()
    app.state.graph = build_graph(app.state.checkpointer)
    logger.info("app: graph and checkpointer initialized")

    yield

    # Shutdown
    logger.info("app: shutting down")
    # Cleanup checkpointer if needed (e.g., close DB connection)
    # For now, no async cleanup needed for SqliteSaver


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Cocktail Recommendation Agent",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None if os.getenv("ENV") == "production" else "/docs",
        redoc_url=None if os.getenv("ENV") == "production" else "/redoc",
    )

    # Add middleware
    add_middleware(app)

    # Global exception handlers
    @app.exception_handler(SourceUnavailableError)
    async def source_unavailable_handler(request: Request, exc: SourceUnavailableError):
        logger.warning(
            "SourceUnavailableError",
            extra={"request_id": getattr(request.state, "request_id", "unknown")},
        )
        return JSONResponse(
            {
                "error": "One or more data sources are unavailable; recommendations may be degraded",
                "request_id": getattr(request.state, "request_id", "unknown"),
            },
            status_code=503,
        )

    @app.exception_handler(GraphExecutionError)
    async def graph_execution_error_handler(request: Request, exc: GraphExecutionError):
        logger.error(
            "GraphExecutionError",
            extra={
                "request_id": getattr(request.state, "request_id", "unknown"),
                "error": str(exc),
            },
        )
        return JSONResponse(
            {
                "error": "Internal server error",
                "request_id": getattr(request.state, "request_id", "unknown"),
            },
            status_code=500,
        )

    @app.exception_handler(ValueError)
    async def validation_error_handler(request: Request, exc: ValueError):
        logger.warning(
            "ValidationError",
            extra={
                "request_id": getattr(request.state, "request_id", "unknown"),
                "error": str(exc),
            },
        )
        return JSONResponse(
            {
                "error": "Invalid request",
                "request_id": getattr(request.state, "request_id", "unknown"),
            },
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(
            "UnhandledException",
            extra={
                "request_id": getattr(request.state, "request_id", "unknown"),
                "error": str(exc),
            },
        )
        return JSONResponse(
            {
                "error": "Internal server error",
                "request_id": getattr(request.state, "request_id", "unknown"),
            },
            status_code=500,
        )

    # Health check endpoint (no auth required)
    @app.get("/healthz")
    async def health_check():
        return {"status": "ok"}

    # Import and register routers
    from src.api.routers import recommendations, feedback, sessions

    app.include_router(recommendations.router, prefix="/v1")
    app.include_router(feedback.router, prefix="/v1")
    app.include_router(sessions.router, prefix="/v1")

    return app


# Create the app instance for uvicorn
app = create_app()
