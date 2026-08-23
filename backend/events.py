"""Virtual fence crossing detection and event construction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from uuid import uuid4


Point = tuple[float, float]
BBox = tuple[int, int, int, int]
PERSON_CLASS_NAMES = {"person"}
VEHICLE_CLASS_NAMES = {"car", "motorcycle", "bus", "truck"}
ANIMAL_CLASS_NAMES = {
    "bird",
    "cat",
    "dog",
    "horse",
    "sheep",
    "cow",
    "elephant",
    "bear",
    "zebra",
    "giraffe",
}


@dataclass(frozen=True)
class TrackedDetection:
    """Plain tracked object data used by event logic."""

    track_id: int
    bbox: BBox
    class_name: str
    confidence: float

    @property
    def center(self) -> Point:
        """Return the center point of the bounding box."""
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    @property
    def object_type(self) -> str:
        """Map class names into event-facing object types."""
        if self.class_name in PERSON_CLASS_NAMES:
            return "person"
        if self.class_name in VEHICLE_CLASS_NAMES:
            return "vehicle"
        if self.class_name in ANIMAL_CLASS_NAMES:
            return "animal"
        return "vehicle"


@dataclass(frozen=True)
class Fence:
    """Line segment used for crossing detection."""

    start: Point
    end: Point

    @classmethod
    def from_frame(
        cls,
        start: Point,
        end: Point,
        frame_width: int,
        frame_height: int,
    ) -> Fence:
        """Build a fence from pixel or normalized frame coordinates."""
        return cls(
            start=_scale_point(start, frame_width, frame_height),
            end=_scale_point(end, frame_width, frame_height),
        )

    def side_of(self, point: Point) -> int:
        """Return which side of the fence a point is on using cross product."""
        x1, y1 = self.start
        x2, y2 = self.end
        px, py = point
        cross = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
        if cross > 0:
            return 1
        if cross < 0:
            return -1
        return 0


@dataclass(frozen=True)
class RestrictedZone:
    """Polygon used for restricted-zone entry detection."""

    points: tuple[Point, ...]

    @classmethod
    def from_frame(
        cls,
        points: tuple[Point, ...],
        frame_width: int,
        frame_height: int,
    ) -> RestrictedZone:
        """Build a polygon from pixel or normalized frame coordinates."""
        return cls(
            points=tuple(
                _scale_point(point, frame_width, frame_height)
                for point in points
            )
        )

    def contains(self, point: Point) -> bool:
        """Return whether a point is inside the polygon."""
        x, y = point
        inside = False
        previous_x, previous_y = self.points[-1]

        for current_x, current_y in self.points:
            crosses_y = (current_y > y) != (previous_y > y)
            if crosses_y:
                slope_x = (previous_x - current_x) * (y - current_y)
                slope_x /= previous_y - current_y
                intersect_x = slope_x + current_x
                if x < intersect_x:
                    inside = not inside
            previous_x, previous_y = current_x, current_y

        return inside


class FenceEventManager:
    """Track per-object fence side and emit de-duplicated crossing events."""

    def __init__(self, camera_id: str, fence: Fence, cooldown_seconds: float) -> None:
        """Create a virtual fence event manager."""
        self.camera_id = camera_id
        self.fence = fence
        self.cooldown_seconds = cooldown_seconds
        self.last_side_by_track: dict[int, int] = {}
        self.last_event_at_by_track: dict[int, float] = {}

    def process(
        self,
        detections: list[TrackedDetection],
        evidence_dir: Path,
    ) -> list[dict[str, object]]:
        """Return events for detections that crossed the fence this frame."""
        events: list[dict[str, object]] = []
        now = monotonic()

        for detection in detections:
            side = self.fence.side_of(detection.center)
            if side == 0:
                continue

            previous_side = self.last_side_by_track.get(detection.track_id)
            self.last_side_by_track[detection.track_id] = side

            if not _is_crossing(previous_side, side):
                continue
            if self._is_in_cooldown(detection.track_id, now):
                continue

            self.last_event_at_by_track[detection.track_id] = now
            events.append(
                build_event(
                    camera_id=self.camera_id,
                    detection=detection,
                    evidence_dir=evidence_dir,
                    event_type="VIRTUAL_FENCE_CROSS",
                )
            )

        return events

    def _is_in_cooldown(self, track_id: int, now: float) -> bool:
        """Return whether a track is still inside its event cooldown."""
        last_event_at = self.last_event_at_by_track.get(track_id)
        if last_event_at is None:
            return False
        return now - last_event_at < self.cooldown_seconds


class RestrictedZoneEventManager:
    """Emit per-track restricted-zone entry events with cooldown."""

    def __init__(
        self,
        camera_id: str,
        zone: RestrictedZone,
        cooldown_seconds: float,
    ) -> None:
        """Create a restricted-zone event manager."""
        self.camera_id = camera_id
        self.zone = zone
        self.cooldown_seconds = cooldown_seconds
        self.last_inside_by_track: dict[int, bool] = {}
        self.last_event_at_by_track: dict[int, float] = {}

    def process(
        self,
        detections: list[TrackedDetection],
        evidence_dir: Path,
    ) -> list[dict[str, object]]:
        """Return events for detections currently inside the restricted zone."""
        events: list[dict[str, object]] = []
        now = monotonic()

        for detection in detections:
            is_inside = self.zone.contains(detection.center)
            was_inside = self.last_inside_by_track.get(detection.track_id, False)
            self.last_inside_by_track[detection.track_id] = is_inside

            if not is_inside or was_inside:
                continue
            if self._is_in_cooldown(detection.track_id, now):
                continue

            self.last_event_at_by_track[detection.track_id] = now
            events.append(
                build_event(
                    camera_id=self.camera_id,
                    detection=detection,
                    evidence_dir=evidence_dir,
                    event_type="RESTRICTED_ZONE_ENTRY",
                )
            )

        return events

    def _is_in_cooldown(self, track_id: int, now: float) -> bool:
        """Return whether a track is still inside its event cooldown."""
        last_event_at = self.last_event_at_by_track.get(track_id)
        if last_event_at is None:
            return False
        return now - last_event_at < self.cooldown_seconds


def build_event(
    camera_id: str,
    detection: TrackedDetection,
    evidence_dir: Path,
    event_type: str,
) -> dict[str, object]:
    """Build a structured event with an evidence path."""
    event_id = str(uuid4())
    return {
        "event_id": event_id,
        "camera_id": camera_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "event_type": event_type,
        "object_type": detection.object_type,
        "track_id": detection.track_id,
        "confidence": detection.confidence,
        "evidence_path": str(evidence_dir / f"{event_id}.jpg"),
    }


def build_new_object_event(
    camera_id: str,
    detection: TrackedDetection,
) -> dict[str, object]:
    """Build a low-severity event for a first-seen track."""
    return {
        "event_id": str(uuid4()),
        "camera_id": camera_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "event_type": "NEW_OBJECT_DETECTED",
        "object_type": detection.object_type,
        "track_id": detection.track_id,
        "confidence": detection.confidence,
        "evidence_path": "",
    }


def _is_crossing(previous_side: int | None, current_side: int) -> bool:
    """Return true when a track moves from one fence side to the other."""
    if previous_side is None or previous_side == 0:
        return False
    return previous_side != current_side


def _scale_point(point: Point, frame_width: int, frame_height: int) -> Point:
    """Scale normalized coordinates to pixels when both values are 0..1."""
    x, y = point
    if 0 <= x <= 1 and 0 <= y <= 1:
        return (x * frame_width, y * frame_height)
    return point
