# CONTRACTS — Types, Interfaces, Schema, API

> The agreement that lets four people build in parallel without breaking each other.
> **Changing anything here requires Divyansh's approval in a dedicated PR.** Everyone codes against this file, not against each other's branches.

## 0. Reconciliation notice (Divyansh, task D1)

Reconciled against the real code on 2026-10-18:
- **Tracked Detections:** The real runtime class in `backend/events.py` is `TrackedDetection`. To decouple analytics from YOLO-specific internals, `TrackedLike` is introduced as a `typing.Protocol` with `track_id`, `object_type`, `bbox`, `confidence`, and `center`. Analytics modules accept `Sequence[TrackedLike]`. `TrackedObject` is preserved as a lightweight test fixture. `BBox` coordinates are `tuple[int, int, int, int]`.
- **Reference Point (Center):** The reference point for fence/zone intersection is exposed on `TrackedDetection` via `@property def center(self) -> Point:` using formula `((x1 + x2) / 2, (y1 + y2) / 2)`.
- **Events:** Events remain plain `dict`s at the storage and API boundary. `EventCandidate` is internal to the analytics pipeline; the worker converts candidates into event dicts. `build_event()` accepts optional `severity` and `extra` parameters with backward-compatible defaults.
- **Evidence Storage & API:** Database column remains `evidence_path`. The API adds `evidence_url` (`"/evidence/<basename>"`). The API temporarily still returns `evidence_path` until Himanshu's task H3 merges, after which it will be removed from the response.
- **Configuration:** Single-camera legacy `.env` settings map directly to `cameras.json` camera keys. Global settings (`model_path`, `confidence_threshold`, `class_filter`, `tracker_type`, `frame_log_interval`, `display_enabled`, `evidence_dir`, `database_path`) remain in `.env` and are not duplicated per camera.
- **Module Signatures:** Analytics modules accept `Sequence[TrackedLike]` instead of a concrete class.

## 1. Conventions

- **Geometry is in pixel coordinates** inside `backend/analytics/*`. The camera worker converts normalized (0.0–1.0) config values to pixels once the frame size is known. Origin is top-left; y grows downward.
- **Time:** all logic takes `now: float` (seconds, monotonic) as a parameter. Wall-clock is only used when building the stored `timestamp` (ISO-8601 UTC) and for time-of-day severity (`now_local: datetime`).
- **Analytics modules are pure**: no I/O, no globals, no sleeping, no threads. They return data; the worker acts on it.
- **One instance per camera.** Stateful detectors (loitering, health, trails, sequence) are instantiated per camera by the worker. Never share instances across cameras.
- **Object types** are exactly: `"person"`, `"vehicle"`, `"animal"`.
- **Errors:** modules never raise on bad frames/empty input; they return empty results. Programmer errors (bad constructor args) raise `ValueError` immediately.

## 2. Shared types — `backend/analytics/types.py`

The runtime class in `backend/events.py` is:
```python
@dataclass(frozen=True)
class TrackedDetection:
    track_id: int
    bbox: BBox  # tuple[int, int, int, int]
    class_name: str
    confidence: float

    @property
    def center(self) -> Point:
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    @property
    def object_type(self) -> str:
        # maps class_name to "person" | "vehicle" | "animal"
        ...
```

Analytics code is typed against the `TrackedLike` protocol so it does not depend on YOLO class names. `TrackedObject` is maintained as a lightweight test fixture implementing this protocol:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

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

class TrackedLike(Protocol):
    """Protocol for tracked objects consumed by analytics modules."""
    @property
    def track_id(self) -> int: ...
    @property
    def object_type(self) -> str: ...
    @property
    def bbox: BBox: ...
    @property
    def confidence: float: ...
    @property
    def center: Point: ...

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
```

## 3. Event types and default severity (owned by K1; table is normative)

| Event | Base severity | Modifiers (applied in `assign_severity`) |
|---|---|---|
| `VIRTUAL_FENCE_CROSS` | HIGH | animal → LOW |
| `RESTRICTED_ZONE_ENTRY` | HIGH | animal → LOW |
| `LOITERING` | MEDIUM | night (22:00–05:00 local) → HIGH; animal → LOW |
| `SUSPICIOUS_SEQUENCE` | HIGH | — |
| `CAMERA_TAMPER` | HIGH | — |
| `CAMERA_OFFLINE` | HIGH | — |
| `CAMERA_ONLINE` | LOW | — |
| `NEW_OBJECT_DETECTED` | LOW | never triggers alarm |

Night modifier raises one level, capped at HIGH. Animal modifier sets LOW. Animal wins over night.

## 4. Event record (DB row == API JSON)

Events remain plain dicts at the storage/API boundary. `EventCandidate` is internal to the analytics pipeline; the worker converts it into an event dict. `build_event()` gets optional `severity` and `extra` params with backward-compatible defaults.

Existing fields are unchanged: `event_id, camera_id, timestamp, event_type, object_type, track_id, confidence, ack_status`.

New / changed:

| Field | Type | Notes |
|---|---|---|
| `severity` | `"LOW"\|"MEDIUM"\|"HIGH"` | default `MEDIUM` for legacy rows |
| `extra` | JSON object | e.g. `{"dwell_seconds": 12.4, "direction": "A_TO_B", "kind": "BLUR", "latency_ms": 180}` |
| `evidence_url` | string or null | `"/evidence/<file>.jpg"`. **Dashboard must use this.** |
| `clip_url` | string or null | `"/evidence/<file>.gif"` (S5) |
| `evidence_path` | string | Internal DB column. **Temporarily** still returned by API until H3 merges, then removed from API response. |

Migration (idempotent, in `db.py`, run at startup; check `PRAGMA table_info(events)` first):

```sql
ALTER TABLE events ADD COLUMN severity  TEXT NOT NULL DEFAULT 'MEDIUM';
ALTER TABLE events ADD COLUMN extra     TEXT NOT NULL DEFAULT '{}';
ALTER TABLE events ADD COLUMN clip_path TEXT;
CREATE INDEX IF NOT EXISTS idx_events_cam_ts ON events(camera_id, timestamp);
PRAGMA journal_mode=WAL;
```

`extra.latency_ms` = (DB write time − frame capture time). Written by the worker; read by `kpi_report.py`.

## 5. `cameras.json`

```json
{
  "cameras": [
    {
      "camera_id": "cam_01",
      "location": "BOP West Gate",
      "source": "http://192.168.43.5:8080/video",
      "loop": false,
      "inference_stride": 2,
      "target_width": 640,
      "fence": { "start": [0.0, 0.5], "end": [1.0, 0.5], "alert_direction": "ANY" },
      "zone":  [[0.62,0.18],[0.95,0.18],[0.95,0.82],[0.62,0.82]],
      "analytics": { "loitering": true, "health": true, "night": false, "trails": true, "clips": false, "sequence": false },
      "loiter_seconds": 10
    }
  ]
}
```

### Legacy `.env` to `cameras.json` Mapping

| Legacy Setting (`backend/config.py` / `.env`) | `cameras.json` Key | Notes |
|---|---|---|
| `IBVAP_LOCATION_LABEL` | `location` | Human-readable camera label |
| `IBVAP_VIDEO_SOURCE` | `source` | URL, file path, or device integer |
| `IBVAP_RESTRICTED_ZONE` | `zone` | Polygon coordinate list `[[x, y], ...]` |
| `IBVAP_FENCE_START` / `IBVAP_FENCE_END` | `fence.start` / `fence.end` | Line endpoints `[x, y]` |
| `IBVAP_EVENT_COOLDOWN_SECONDS` | `cooldown_seconds` | Event trigger cooldown |

Global settings (`model_path`, `confidence_threshold`, `class_filter`, `tracker_type`, `frame_log_interval`, `display_enabled`, `evidence_dir`, `database_path`) stay in `.env` and are not per camera.

- `source`: URL, file path, or integer camera index. `loop: true` replays files (demo fallback).
- Coordinates in `[0,1]` are normalized; anything larger is treated as pixels (existing behaviour).
- `alert_direction`: `"ANY" | "A_TO_B" | "B_TO_A"`. A side = left of vector `start→end`.
- `analytics.*` are **feature flags**: an unfinished module can be merged but stays `false`.
- Real `cameras.json` is gitignored. Legacy `.env` single-camera mode must keep working as `cam_01`.

## 6. Module interfaces (frozen signatures)

All files under `backend/analytics/`. Stubs are created in D1 so every branch imports cleanly.

```python
# severity.py  (K1, K4)
def assign_severity(c: EventCandidate, now_local: datetime) -> Severity: ...
def is_suppressed(c: EventCandidate) -> bool:
    """True when an animal-triggered fence/zone/loitering candidate was downgraded to LOW (K4)."""

# loitering.py  (K2)
class LoiteringDetector:
    def __init__(self, zone: list[Point], dwell_seconds: float = 10.0,
                 grace_seconds: float = 1.5, cooldown_seconds: float = 30.0,
                 stale_seconds: float = 5.0) -> None: ...
    def update(self, objects: Sequence[TrackedLike], now: float) -> list[EventCandidate]: ...

# direction.py  (K3)
def crossing_direction(prev: Point, curr: Point, a: Point, b: Point) -> Literal["A_TO_B", "B_TO_A"] | None: ...

# sequence.py  (K5)
class SequenceDetector:
    def __init__(self, window_seconds: float = 60.0, repeat_count: int = 3, repeat_window: float = 120.0) -> None: ...
    def ingest(self, c: EventCandidate, now: float) -> list[EventCandidate]: ...

# health.py  (S1)
class FrameHealthMonitor:
    def __init__(self, check_interval: float = 1.0, warmup_seconds: float = 10.0,
                 blur_ratio: float = 0.3, dark_mean: float = 25.0,
                 frozen_seconds: float = 4.0, confirm_checks: int = 3) -> None: ...
    def update(self, frame: "np.ndarray", now: float) -> list[EventCandidate]: ...

# trails.py  (S2)
class TrailBuffer:
    def __init__(self, max_points: int = 40, stale_seconds: float = 2.0) -> None: ...
    def update(self, objects: Sequence[TrackedLike], now: float) -> None: ...
    def points(self, track_id: int) -> list[Point]: ...
def draw_trails(frame: "np.ndarray", trails: TrailBuffer) -> None:   # in-place

# night.py  (S4)
def is_low_light(frame: "np.ndarray", prev_state: bool = False) -> bool: ...   # hysteresis
def enhance_low_light(frame: "np.ndarray") -> "np.ndarray": ...                # returns new frame

# clips.py  (S5)
class ClipRecorder:
    def __init__(self, seconds_before: float = 4.0, seconds_after: float = 4.0, fps: float = 5.0, max_width: int = 480) -> None: ...
    def push(self, frame: "np.ndarray", now: float) -> None: ...
    def request(self, event_id: str, now: float) -> None: ...
    def poll(self, now: float, out_dir: str) -> list[tuple[str, str]]:   # [(event_id, path)] finished since last poll
```

Existing `events.py` fence/zone logic keeps its public behaviour. K3 adds `extra["direction"]` to fence candidates and honours `alert_direction`.

## 7. REST API additions (Divyansh implements; Himanshu consumes via mocks first)

| Endpoint | Response |
|---|---|
| `GET /cameras` | `[{camera_id, location, status:"LIVE"\|"OFFLINE"\|"DEGRADED", fps, latency_ms, last_frame_age_s, low_visibility:bool, counts:{person,vehicle,animal}}]` |
| `GET /video_feed/{camera_id}` | MJPEG; 404 if unknown id. Old `/video_feed` = first camera (compat). |
| `GET /cameras/{camera_id}/snapshot` | single JPEG of latest raw frame; 503 if offline |
| `GET /cameras/{camera_id}/config` | `{fence:{start,end,alert_direction}, zone:[[x,y],...], frame_size:[w,h]}` (normalized coords) |
| `PUT /cameras/{camera_id}/config` | same body; validates; writes `cameras.json` atomically (temp file + `os.replace`); hot-reloads the worker; returns saved config |
| `GET /stats?camera_id=` | `{person, vehicle, animal, suppressed_animal_events}`; omit `camera_id` for the sum |
| `GET /events` | existing filters + `severity`, `ack_status`; items as in §4 |

Status rules: `OFFLINE` after 5 s without frames; `DEGRADED` if an active `CAMERA_TAMPER` condition exists or FPS < 3.

## 8. Per-frame pipeline order (CameraWorker)

```
grab latest frame
 → health.update(raw)                  [flag: health]
 → low-light? enhance copy for inference [flag: night]
 → YOLO.track → TrackedObject[]
 → fence/zone (events.py)              → candidates
 → loitering.update                    [flag: loitering]
 → sequence.ingest(each candidate)     [flag: sequence]
 → trails.update + draw                [flag: trails]
 → per-candidate: assign_severity → cooldown/dedup → evidence save → clip.request → DB insert (+latency_ms)
 → annotate frame → publish to live_state[camera_id]
```

A module that throws is disabled for that camera for 60 s and logged; the worker continues.

## 9. Performance and reliability budget (dev laptop, 3 cameras, 640-wide)

- Sustained ≥ 8 processed FPS per camera at `inference_stride=2`.
- Analytics overhead per processed frame ≤ 5 ms combined; `health` ≤ 2 ms amortised; `enhance_low_light` ≤ 10 ms.
- Per-camera memory growth: none over 30 min (all per-track dicts are pruned by `stale_seconds`).
- A dead camera must never stall other cameras or the API.

## 10. Test requirements

Every module in §6 ships with `tests/analytics/test_<module>.py` using synthetic inputs (hand-built `TrackedObject` lists, NumPy images) and an injected `now`. No video files in tests.
