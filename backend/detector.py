"""YOLOv8 detection and tracking pipeline for IBVAP Phase 2."""

from __future__ import annotations

import logging
import sys
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from cv2 import VideoCapture
from ultralytics import YOLO

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend import config
from backend.config import Settings, get_settings
from backend.utils.annotation import draw_detections, get_track_id
from backend.utils.video_source import open_video_source

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
LOGGER = logging.getLogger(__name__)


class Detector:
    """YOLO-backed detector and tracker for people and vehicle classes."""

    def __init__(self, settings: Settings) -> None:
        """Create a detector with config-driven runtime settings."""
        self.settings = settings
        self.model: YOLO | None = None
        self.capture: VideoCapture | None = None
        self.frame_count = 0
        self.fps_started_at = time.perf_counter()
        self.seen_track_ids: set[int] = set()

    def load_model(self) -> YOLO:
        """Load the configured YOLO model."""
        LOGGER.info("Loading YOLO model: %s", self.settings.model_path)
        self.model = YOLO(self.settings.model_path)
        LOGGER.info("YOLO model loaded")
        return self.model

    def open_source(self) -> VideoCapture:
        """Open the configured video source."""
        self.capture = open_video_source(self.settings.video_source)
        return self.capture

    def read_frame(self) -> np.ndarray | None:
        """Read one frame, returning None when the source disconnects."""
        if self.capture is None:
            raise RuntimeError("Video source is not open")

        success, frame = self.capture.read()
        if not success or frame is None:
            LOGGER.warning("No frame received; stopping detector loop")
            return None
        return frame

    def run_inference(self, frame: np.ndarray) -> Any:
        """Run YOLO tracking for configured COCO class ids."""
        if self.model is None:
            raise RuntimeError("Model is not loaded")

        results = self.model.track(
            frame,
            persist=True,
            conf=self.settings.confidence_threshold,
            classes=list(self.settings.class_filter),
            tracker=self.settings.tracker_type,
            verbose=False,
        )
        return results[0]

    def annotate_frame(self, frame: np.ndarray, result: Any) -> np.ndarray:
        """Draw bounding boxes, track IDs, labels, and confidence scores."""
        return draw_detections(frame, result)

    def log_new_tracks(self, result: Any) -> None:
        """Log each track ID the first time it appears."""
        if result.boxes is None:
            return

        for box in result.boxes:
            track_id = get_track_id(box)
            if track_id is None or track_id in self.seen_track_ids:
                continue

            class_id = int(box.cls[0])
            LOGGER.info("New track: %s #%s", result.names[class_id], track_id)
            self.seen_track_ids.add(track_id)

    def log_fps(self) -> None:
        """Log average FPS every configured frame interval."""
        self.frame_count += 1
        if self.frame_count % self.settings.frame_log_interval != 0:
            return

        elapsed = time.perf_counter() - self.fps_started_at
        fps = self.settings.frame_log_interval / elapsed if elapsed > 0 else 0.0
        LOGGER.info("Processed FPS: %.2f", fps)
        self.fps_started_at = time.perf_counter()

    def run(self) -> None:
        """Run the live detection loop until exit key or disconnect."""
        self.load_model()
        self.open_source()

        try:
            while True:
                frame = self.read_frame()
                if frame is None:
                    break

                result = self.run_inference(frame)
                self.log_new_tracks(result)
                annotated = self.annotate_frame(frame, result)
                cv2.imshow(config.WINDOW_NAME, annotated)
                self.log_fps()

                key = cv2.waitKey(1) & 0xFF
                if key == ord(config.EXIT_KEY):
                    LOGGER.info("Exit key pressed; stopping detector")
                    break
        except cv2.error as exc:
            LOGGER.error("OpenCV error while running detector: %s", exc)
        finally:
            self.close()

    def close(self) -> None:
        """Release OpenCV resources."""
        if self.capture is not None:
            self.capture.release()
        cv2.destroyAllWindows()


def main() -> None:
    """Run the detector from the command line."""
    try:
        Detector(get_settings()).run()
    except (RuntimeError, ValueError) as exc:
        LOGGER.error("%s", exc)


if __name__ == "__main__":
    main()
