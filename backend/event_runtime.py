"""Runtime wiring for virtual fence events."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np

from backend.config import Settings
from backend.events import Fence, FenceEventManager, TrackedDetection
from backend.utils.annotation import draw_fence
from backend.utils.evidence import save_evidence_snapshot

LOGGER = logging.getLogger(__name__)


class VirtualFenceRuntime:
    """Coordinate fence checks, evidence snapshots, and event logging."""

    def __init__(self, settings: Settings) -> None:
        """Create a runtime from detector settings."""
        self.settings = settings
        self.event_manager: FenceEventManager | None = None

    def draw(self, frame: np.ndarray) -> None:
        """Draw the virtual fence when it has been initialized."""
        if self.event_manager is not None:
            draw_fence(frame, self.event_manager.fence)

    def process(self, frame: np.ndarray, detections: list[TrackedDetection]) -> None:
        """Generate events, save evidence, and log fired events."""
        event_manager = self._ensure_event_manager(frame)
        events = event_manager.process(detections, self.settings.evidence_dir)
        detections_by_track = {detection.track_id: detection for detection in detections}

        for event in events:
            detection = detections_by_track[int(event["track_id"])]
            if not save_evidence_snapshot(
                frame,
                detection,
                Path(str(event["evidence_path"])),
            ):
                LOGGER.warning("Failed to save evidence for event %s", event["event_id"])
            LOGGER.info("Fence event:\n%s", json.dumps(event, indent=2))

    def _ensure_event_manager(self, frame: np.ndarray) -> FenceEventManager:
        """Create the fence event manager once frame dimensions are known."""
        if self.event_manager is not None:
            return self.event_manager

        height, width = frame.shape[:2]
        fence = Fence.from_frame(
            self.settings.fence_start,
            self.settings.fence_end,
            width,
            height,
        )
        self.event_manager = FenceEventManager(
            camera_id=self.settings.camera_id,
            fence=fence,
            cooldown_seconds=self.settings.event_cooldown_seconds,
        )
        LOGGER.info("Virtual fence initialized: %s -> %s", fence.start, fence.end)
        return self.event_manager
