"""Loitering detector analytics module.

Owner: Kabir (K2) - stub.
"""

from __future__ import annotations

from collections.abc import Sequence

from backend.analytics.types import EventCandidate, Point, TrackedLike


class LoiteringDetector:
    """Loitering detector stub."""

    def __init__(
        self,
        zone: list[Point],
        dwell_seconds: float = 10.0,
        grace_seconds: float = 1.5,
        cooldown_seconds: float = 30.0,
        stale_seconds: float = 5.0,
    ) -> None:
        self.zone = zone
        self.dwell_seconds = dwell_seconds
        self.grace_seconds = grace_seconds
        self.cooldown_seconds = cooldown_seconds
        self.stale_seconds = stale_seconds

    def update(
        self,
        objects: Sequence[TrackedLike],
        now: float,
    ) -> list[EventCandidate]:
        """Update tracker state and emit loitering candidates."""
        return []
