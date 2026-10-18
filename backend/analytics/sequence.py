"""Suspicious sequence analytics module.

Owner: Kabir (K5) - stub.
"""

from __future__ import annotations

from backend.analytics.types import EventCandidate


class SequenceDetector:
    """Sequence detector stub."""

    def __init__(
        self,
        window_seconds: float = 60.0,
        repeat_count: int = 3,
        repeat_window: float = 120.0,
    ) -> None:
        self.window_seconds = window_seconds
        self.repeat_count = repeat_count
        self.repeat_window = repeat_window

    def ingest(self, c: EventCandidate, now: float) -> list[EventCandidate]:
        """Ingest an event candidate and detect suspicious sequences."""
        return []
