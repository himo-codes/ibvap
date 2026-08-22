"""Frame annotation helpers for detector output."""

from __future__ import annotations

from typing import Any

import cv2
import numpy as np

from backend import config


def draw_detections(frame: np.ndarray, result: Any) -> np.ndarray:
    """Draw result bounding boxes, labels, and confidence scores on a frame."""
    if result.boxes is None:
        return frame

    for box in result.boxes:
        x1, y1, x2, y2 = (int(value) for value in box.xyxy[0].tolist())
        confidence = float(box.conf[0])
        class_id = int(box.cls[0])
        label = f"{result.names[class_id]} {confidence:.2f}"

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            config.BOX_COLOR,
            config.BOX_THICKNESS,
        )
        draw_label(frame, label, x1, y1)

    return frame


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
