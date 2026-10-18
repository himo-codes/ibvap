from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

Point = tuple[float, float]
BBox = tuple[int, int, int, int]          # x1, y1, x2, y2 (pixels)


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class EventType(str, Enum):
    NEW_OBJECT_DETECTED   = "NEW_OBJECT_DETECTED"
    VIRTUAL_FENCE_CROSS   = "VIRTUAL_FENCE_CROSS"
    RESTRICTED_ZONE_ENTRY = "RESTRICTED_ZONE_ENTRY"
    LOITERING             = "LOITERING"
    CAMERA_OFFLINE        = "CAMERA_OFFLINE"
    CAMERA_ONLINE         = "CAMERA_ONLINE"
    CAMERA_TAMPER         = "CAMERA_TAMPER"        # extra.kind in {"BLUR","BLACKOUT","FROZEN"}
    SUSPICIOUS_SEQUENCE   = "SUSPICIOUS_SEQUENCE"


@runtime_checkable
class TrackedLike(Protocol):
    """Protocol for tracked objects consumed by analytics modules."""

    @property
    def track_id(self) -> int: ...

    @property
    def object_type(self) -> str: ...

    @property
    def bbox(self) -> BBox: ...

    @property
    def confidence(self) -> float: ...

    @property
    def center(self) -> Point: ...


@dataclass(frozen=True, slots=True)
class TrackedObject:
    """Lightweight test fixture implementing TrackedLike."""

    track_id: int
    object_type: str
    bbox: BBox
    confidence: float

    @property
    def center(self) -> Point:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


@dataclass(slots=True)
class EventCandidate:
    event_type: EventType
    object_type: str | None = None         # None for camera-level events
    track_id: int | None = None            # None for camera-level events
    confidence: float = 1.0
    severity: Severity | None = None       # filled by assign_severity()
    extra: dict = field(default_factory=dict)   # JSON-serialisable only
