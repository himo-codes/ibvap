"""Track history trail buffer and visualization.

Owner: Kasumi (S2) - stub.
"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from backend.analytics.types import Point, TrackedLike


class TrailBuffer:
    """Trail buffer stub."""

    def __init__(self, max_points: int = 40, stale_seconds: float = 2.0) -> None:
        self.max_points = max_points
        self.stale_seconds = stale_seconds

    def update(self, objects: Sequence[TrackedLike], now: float) -> None:
        """Update trail history for tracked objects."""

    def points(self, track_id: int) -> list[Point]:
        """Return history points for a track."""
        return []


def draw_trails(frame: np.ndarray, trails: TrailBuffer) -> None:
    """Draw trails onto frame in-place."""
