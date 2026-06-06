"""Custom exception classes for the cocktail recommendation API."""


class GraphExecutionError(Exception):
    """Raised when graph execution fails unrecoverably."""

    pass


class AuthTokenExpiredError(Exception):
    """Raised when the user's OAuth token is invalid or expired."""

    pass
