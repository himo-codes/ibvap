"""Clip recorder for event video/GIF snippets.

Owner: Kasumi (S5) - stub.
"""

from __future__ import annotations

import numpy as np


class ClipRecorder:
    """Clip recorder stub."""

    def __init__(
        self,
        seconds_before: float = 4.0,
        seconds_after: float = 4.0,
        fps: float = 5.0,
        max_width: int = 480,
    ) -> None:
        self.seconds_before = seconds_before
        self.seconds_after = seconds_after
        self.fps = fps
        self.max_width = max_width

    def push(self, frame: np.ndarray, now: float) -> None:
        """Push a frame into the circular buffer."""

    def request(self, event_id: str, now: float) -> None:
        """Request recording a clip for an event."""

    def poll(self, now: float, out_dir: str) -> list[tuple[str, str]]:
        """Return list of completed (event_id, clip_path) pairs since last poll."""
        return []
