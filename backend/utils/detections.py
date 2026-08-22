"""Adapters from YOLO results to plain event-layer detections."""

from __future__ import annotations

from typing import Any

from backend.events import TrackedDetection
from backend.utils.annotation import get_track_id


def extract_tracked_detections(result: Any) -> list[TrackedDetection]:
    """Convert a YOLO result into plain tracked detections."""
    if result.boxes is None:
        return []

    detections: list[TrackedDetection] = []
    for box in result.boxes:
        track_id = get_track_id(box)
        if track_id is None:
            continue

        bbox = tuple(int(value) for value in box.xyxy[0].tolist())
        detections.append(
            TrackedDetection(
                track_id=track_id,
                bbox=(bbox[0], bbox[1], bbox[2], bbox[3]),
                class_name=result.names[int(box.cls[0])],
                confidence=float(box.conf[0]),
            )
        )

    return detections
