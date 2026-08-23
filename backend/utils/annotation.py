"""Frame annotation helpers for detector output."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from backend import config
from backend.events import Fence, RestrictedZone


def draw_detections(frame: np.ndarray, result: Any) -> np.ndarray:
    """Draw result boxes with class names, track IDs, and confidence scores."""
    if result.boxes is None:
        return frame

    for box in result.boxes:
        x1, y1, x2, y2 = (int(value) for value in box.xyxy[0].tolist())
        confidence = float(box.conf[0])
        class_id = int(box.cls[0])
        track_id = get_track_id(box)
        label = build_label(result.names[class_id], confidence, track_id)

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            config.BOX_COLOR,
            config.BOX_THICKNESS,
        )
        draw_label(frame, label, x1, y1)

    return frame


def draw_fence(frame: np.ndarray, fence: Fence) -> np.ndarray:
    """Draw the virtual fence line on a frame."""
    start = (int(fence.start[0]), int(fence.start[1]))
    end = (int(fence.end[0]), int(fence.end[1]))
    cv2.line(frame, start, end, config.FENCE_COLOR, config.FENCE_THICKNESS)
    return frame


def draw_restricted_zone(frame: np.ndarray, zone: RestrictedZone) -> np.ndarray:
    """Draw a semi-transparent restricted zone polygon on a frame."""
    points = np.array(
        [[(int(point[0]), int(point[1])) for point in zone.points]],
        dtype=np.int32,
    )
    overlay = frame.copy()
    cv2.fillPoly(overlay, points, config.ZONE_COLOR)
    cv2.addWeighted(
        overlay,
        config.ZONE_FILL_ALPHA,
        frame,
        1 - config.ZONE_FILL_ALPHA,
        0,
        frame,
    )
    cv2.polylines(frame, points, True, config.ZONE_COLOR, config.FENCE_THICKNESS)
    return frame


def draw_counts_overlay(frame: np.ndarray, counts: dict[str, int]) -> np.ndarray:
    """Draw current tracked object counts on the frame."""
    text = (
        f"Person: {counts.get('person', 0)}  "
        f"Vehicle: {counts.get('vehicle', 0)}  "
        f"Animal: {counts.get('animal', 0)}"
    )
    size, baseline = cv2.getTextSize(
        text,
        config.TEXT_FONT,
        config.TEXT_SCALE,
        config.TEXT_THICKNESS,
    )
    text_width, text_height = size
    x = config.TEXT_PADDING
    y = config.TEXT_PADDING + text_height
    cv2.rectangle(
        frame,
        (0, 0),
        (
            text_width + config.TEXT_PADDING * 2,
            text_height + baseline + config.TEXT_PADDING * 2,
        ),
        (16, 24, 32),
        cv2.FILLED,
    )
    cv2.putText(
        frame,
        text,
        (x, y),
        config.TEXT_FONT,
        config.TEXT_SCALE,
        config.TEXT_COLOR,
        config.TEXT_THICKNESS,
    )
    return frame


def build_label(class_name: str, confidence: float, track_id: int | None) -> str:
    """Build a display label for a detection with an optional track ID."""
    if track_id is None:
        return f"{class_name} {confidence:.2f}"
    return f"{class_name} #{track_id}  {confidence:.2f}"


def get_track_id(box: Any) -> int | None:
    """Extract a tracker ID from a YOLO box when one is available."""
    box_id = getattr(box, "id", None)
    if box_id is None:
        return None
    value = box_id[0]
    if hasattr(value, "item"):
        return int(value.item())
    return int(value)


def draw_label(frame: np.ndarray, label: str, x: int, y: int) -> None:
    """Draw a readable text label near a bounding box."""
    size, baseline = cv2.getTextSize(
        label,
        config.TEXT_FONT,
        config.TEXT_SCALE,
        config.TEXT_THICKNESS,
    )
    text_width, text_height = size
    label_y = max(y, text_height + config.TEXT_PADDING)

    cv2.rectangle(
        frame,
        (x, label_y - text_height - config.TEXT_PADDING),
        (x + text_width + config.TEXT_PADDING, label_y + baseline),
        config.TEXT_BACKGROUND_COLOR,
        cv2.FILLED,
    )
    cv2.putText(
        frame,
        label,
        (x + config.TEXT_PADDING // 2, label_y - config.TEXT_PADDING // 2),
        config.TEXT_FONT,
        config.TEXT_SCALE,
        config.TEXT_COLOR,
        config.TEXT_THICKNESS,
    )
