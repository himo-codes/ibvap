"""OpenCV video-source helpers."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
from cv2 import VideoCapture

LOGGER = logging.getLogger(__name__)


def parse_video_source(raw_source: str) -> int | str:
    """Convert numeric camera indexes to int and file sources to paths."""
    source = raw_source.strip()
    if source.isdigit():
        return int(source)
    return str(Path(source).expanduser())


def open_video_source(raw_source: str) -> VideoCapture:
    """Open a webcam index or video file path with OpenCV."""
    source = parse_video_source(raw_source)
    capture = cv2.VideoCapture(source)

    if not capture.isOpened():
        raise RuntimeError(f"Unable to open video source: {raw_source}")

    LOGGER.info("Video source opened: %s", raw_source)
    return capture
