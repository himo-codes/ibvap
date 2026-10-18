"""Camera frame health and tamper monitor.

Owner: Kasumi (S1) - stub.
"""

from __future__ import annotations

import numpy as np

from backend.analytics.types import EventCandidate


class FrameHealthMonitor:
    """Frame health monitor stub."""

    def __init__(
        self,
        check_interval: float = 1.0,
        warmup_seconds: float = 10.0,
        blur_ratio: float = 0.3,
        dark_mean: float = 25.0,
        frozen_seconds: float = 4.0,
        confirm_checks: int = 3,
    ) -> None:
        self.check_interval = check_interval
        self.warmup_seconds = warmup_seconds
        self.blur_ratio = blur_ratio
        self.dark_mean = dark_mean
        self.frozen_seconds = frozen_seconds
        self.confirm_checks = confirm_checks

    def update(self, frame: np.ndarray, now: float) -> list[EventCandidate]:
        """Check frame health and emit tamper events if detected."""
        return []
