"""Evidence snapshot helpers."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from backend.events import TrackedDetection


def save_evidence_snapshot(
    frame: np.ndarray,
    detection: TrackedDetection,
    evidence_path: Path,
) -> bool:
    """Save a cropped evidence snapshot for one tracked detection."""
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    crop = crop_bbox(frame, detection.bbox)
    if crop is None:
        return False
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
