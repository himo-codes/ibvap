"""YOLOv8 detection, tracking, and event pipeline for IBVAP Phase 3."""

from __future__ import annotations

import logging
import sqlite3
import sys
import threading
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
from backend.db import insert_event
from backend.event_runtime import VirtualFenceRuntime
from backend.events import build_new_object_event
from backend.live_state import LiveDetectorState
from backend.utils.annotation import draw_counts_overlay, draw_detections
from backend.utils.detections import extract_tracked_detections
from backend.utils.video_source import open_video_source

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
LOGGER = logging.getLogger(__name__)


class Detector:
    """YOLO-backed detector and tracker for people and vehicle classes."""

    def __init__(
        self,
        settings: Settings,
        stop_event: threading.Event | None = None,
        live_state: LiveDetectorState | None = None,
    ) -> None:
        """Create a detector with config-driven runtime settings."""
        self.settings = settings
        self.stop_event = stop_event
        self.live_state = live_state
        self.model: YOLO | None = None
        self.capture: VideoCapture | None = None
        self.frame_count = 0
        self.fps_started_at = time.perf_counter()
        self.seen_track_ids: set[int] = set()
        self.event_runtime = VirtualFenceRuntime(settings)

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

    def annotate_frame(
        self,
        frame: np.ndarray,
        result: Any,
        counts: dict[str, int],
    ) -> np.ndarray:
        """Draw fence, boxes, track IDs, labels, and confidence scores."""
        self.event_runtime.draw(frame)
        draw_detections(frame, result)
        return draw_counts_overlay(frame, counts)

    def handle_new_tracks(self, detections: list[Any]) -> None:
        """Store a quiet event each time a new track ID appears."""
        for detection in detections:
            if detection.track_id in self.seen_track_ids:
                continue

            LOGGER.info("New track: %s #%s", detection.class_name, detection.track_id)
            event = build_new_object_event(self.settings.camera_id, detection)
            try:
                insert_event(event, self.settings.database_path)
            except (sqlite3.Error, OSError) as exc:
                LOGGER.error("Failed to store event %s: %s", event["event_id"], exc)
            self.seen_track_ids.add(detection.track_id)

    def count_active_objects(self, detections: list[Any]) -> dict[str, int]:
        """Count currently tracked objects by event-facing object group."""
        track_ids_by_type = {"person": set(), "vehicle": set(), "animal": set()}
        for detection in detections:
            object_type = detection.object_type
            if object_type in track_ids_by_type:
                track_ids_by_type[object_type].add(detection.track_id)

        return {
            object_type: len(track_ids)
            for object_type, track_ids in track_ids_by_type.items()
        }

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
                detections = extract_tracked_detections(result)
                self.handle_new_tracks(detections)
                self.event_runtime.process(frame, detections)
                counts = self.count_active_objects(detections)
                annotated = self.annotate_frame(frame.copy(), result, counts)
                if self.live_state is not None:
                    self.live_state.update(annotated, counts)
                if self.settings.display_enabled:
                    cv2.imshow(config.WINDOW_NAME, annotated)
                self.log_fps()

                if self.should_stop_from_user_input():
                    break
        except cv2.error as exc:
            LOGGER.error("OpenCV error while running detector: %s", exc)
        finally:
            self.close()

    def should_stop_from_user_input(self) -> bool:
        """Return true when stop was requested or display exit key is pressed."""
        if self.stop_event is not None and self.stop_event.is_set():
            LOGGER.info("Stop requested; stopping detector")
            return True
        if not self.settings.display_enabled:
            return False

        key = cv2.waitKey(1) & 0xFF
        if key == ord(config.EXIT_KEY):
            LOGGER.info("Exit key pressed; stopping detector")
            return True
        return False

    def close(self) -> None:
        """Release OpenCV resources."""
        if self.capture is not None:
            self.capture.release()
        if self.settings.display_enabled:
            cv2.destroyAllWindows()


def main() -> None:
    """Run the detector from the command line."""
    try:
        Detector(get_settings()).run()
    except (RuntimeError, ValueError) as exc:
        LOGGER.error("%s", exc)


if __name__ == "__main__":
    main()
