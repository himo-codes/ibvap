"""Evidence snapshot helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from backend.events import TrackedDetection


def save_evidence_snapshot(
    frame: np.ndarray,
    detection: TrackedDetection,
    evidence_path: Path,
    location_label: str,
    timestamp: str,
) -> bool:
    """Save a cropped evidence snapshot for one tracked detection."""
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    crop = crop_bbox(frame, detection.bbox)
    if crop is None:
        return False
    stamp_evidence(crop, location_label, timestamp)
    return bool(cv2.imwrite(str(evidence_path), crop))


def crop_bbox(frame: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray | None:
    """Return a frame crop for a bounding box, clipped to image bounds."""
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = bbox
    left = max(0, min(x1, width - 1))
    top = max(0, min(y1, height - 1))
    right = max(0, min(x2, width))
    bottom = max(0, min(y2, height))

    if right <= left or bottom <= top:
        return None
    return frame[top:bottom, left:right]


def stamp_evidence(
    image: np.ndarray,
    location_label: str,
    timestamp: str,
) -> None:
    """Burn timestamp and location text into an evidence image."""
    lines = (format_timestamp(timestamp), location_label)
    font = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.52
    thickness = 1
    padding = 7
    line_gap = 6
    sizes = [
        cv2.getTextSize(line, font, scale, thickness)[0]
        for line in lines
    ]
    text_width = max(width for width, _ in sizes)
    text_height = sum(height for _, height in sizes) + line_gap * (len(lines) - 1)
    background_height = text_height + padding * 2
    cv2.rectangle(
        image,
        (0, 0),
        (text_width + padding * 2, background_height),
        (0, 0, 0),
        cv2.FILLED,
    )

    y = padding
    for line, (_, height) in zip(lines, sizes, strict=True):
        y += height
        cv2.putText(
            image,
            line,
            (padding, y),
            font,
            scale,
            (255, 255, 255),
            thickness,
            cv2.LINE_AA,
        )
        y += line_gap


def format_timestamp(timestamp: str) -> str:
    """Format an ISO timestamp for evidence stamping."""
    try:
        return datetime.fromisoformat(timestamp).strftime("%Y-%m-%d %H:%M:%S %Z")
    except ValueError:
        return timestamp
