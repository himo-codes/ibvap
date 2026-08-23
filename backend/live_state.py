"""Thread-safe live detector state shared with API routes."""

from __future__ import annotations

import threading

import numpy as np


class LiveDetectorState:
    """Store the latest annotated frame and current active object counts."""

    def __init__(self) -> None:
        """Create an empty live-state buffer."""
        self._lock = threading.Lock()
        self._latest_frame: np.ndarray | None = None
        self._counts = {"person": 0, "vehicle": 0, "animal": 0}

    def update(
        self,
        frame: np.ndarray,
        counts: dict[str, int],
    ) -> None:
        """Replace latest frame and counts atomically."""
        with self._lock:
            self._latest_frame = frame.copy()
            self._counts = {
                "person": int(counts.get("person", 0)),
                "vehicle": int(counts.get("vehicle", 0)),
                "animal": int(counts.get("animal", 0)),
            }

    def get_frame(self) -> np.ndarray | None:
        """Return a copy of the latest annotated frame."""
        with self._lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def get_counts(self) -> dict[str, int]:
        """Return current-frame active tracked object counts."""
        with self._lock:
            return dict(self._counts)
