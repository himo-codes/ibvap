"""Runtime wiring for virtual fence events."""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

import numpy as np

from backend.config import Settings
from backend.db import init_db, insert_event
from backend.events import (
    Fence,
    FenceEventManager,
    RestrictedZone,
    RestrictedZoneEventManager,
    TrackedDetection,
)
from backend.utils.annotation import draw_fence, draw_restricted_zone
from backend.utils.evidence import save_evidence_snapshot

LOGGER = logging.getLogger(__name__)


class VirtualFenceRuntime:
    """Coordinate fence checks, evidence snapshots, and event logging."""

    def __init__(self, settings: Settings) -> None:
        """Create a runtime from detector settings."""
        self.settings = settings
        self.fence_event_manager: FenceEventManager | None = None
        self.zone_event_manager: RestrictedZoneEventManager | None = None
        init_db(settings.database_path)

    def draw(self, frame: np.ndarray) -> None:
        """Draw the virtual fence when it has been initialized."""
        if self.fence_event_manager is not None:
            draw_fence(frame, self.fence_event_manager.fence)
        if self.zone_event_manager is not None:
            draw_restricted_zone(frame, self.zone_event_manager.zone)

    def process(self, frame: np.ndarray, detections: list[TrackedDetection]) -> None:
        """Generate events, save evidence, and log fired events."""
        fence_event_manager, zone_event_manager = self._ensure_event_managers(frame)
        events = fence_event_manager.process(detections, self.settings.evidence_dir)
        events.extend(zone_event_manager.process(detections, self.settings.evidence_dir))
        detections_by_track = {detection.track_id: detection for detection in detections}

        for event in events:
            detection = detections_by_track[int(event["track_id"])]
            if not save_evidence_snapshot(
                frame,
                detection,
                Path(str(event["evidence_path"])),
                self.settings.location_label,
                str(event["timestamp"]),
            ):
                LOGGER.warning("Failed to save evidence for event %s", event["event_id"])
            try:
                insert_event(event, self.settings.database_path)
            except (sqlite3.Error, OSError) as exc:
                LOGGER.error("Failed to store event %s: %s", event["event_id"], exc)
            LOGGER.info("Fence event:\n%s", json.dumps(event, indent=2))

    def _ensure_event_managers(
        self,
        frame: np.ndarray,
    ) -> tuple[FenceEventManager, RestrictedZoneEventManager]:
        """Create event managers once frame dimensions are known."""
        if self.fence_event_manager is not None and self.zone_event_manager is not None:
            return self.fence_event_manager, self.zone_event_manager

        height, width = frame.shape[:2]
        fence = Fence.from_frame(
            self.settings.fence_start,
            self.settings.fence_end,
            width,
            height,
        )
        self.fence_event_manager = FenceEventManager(
            camera_id=self.settings.camera_id,
            fence=fence,
            cooldown_seconds=self.settings.event_cooldown_seconds,
        )
        zone = RestrictedZone.from_frame(
            self.settings.restricted_zone,
            width,
            height,
        )
        self.zone_event_manager = RestrictedZoneEventManager(
            camera_id=self.settings.camera_id,
            zone=zone,
            cooldown_seconds=self.settings.event_cooldown_seconds,
        )
        LOGGER.info("Virtual fence initialized: %s -> %s", fence.start, fence.end)
        LOGGER.info("Restricted zone initialized: %s", zone.points)
        return self.fence_event_manager, self.zone_event_manager
