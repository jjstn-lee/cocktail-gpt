from typing import Any
from typing_extensions import TypedDict


class SourceUnavailableError(Exception):
    """Raised when a data source fails to provide data."""

    def __init__(
        self, source: str, reason: str, original: Exception | None = None
    ) -> None:
        self.source = source
        self.reason = reason
        self.original = original
        super().__init__(f"[{source}] {reason}")


class SourcePayload(TypedDict, total=False):
    """Normalized payload from a data source."""

    source: str
    fetched_at: str  # ISO 8601 UTC
    signals: dict[str, Any]
    confidence: float  # 0.0–1.0
