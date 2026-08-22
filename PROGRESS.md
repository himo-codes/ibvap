# IBVAP Progress

## Section 5 - Phase 0 + Phase 1 Handoff

### Done

- Created a Python project skeleton for the perception layer under `backend/`.
- Added config-driven settings via `backend/config.py`, with optional `.env` support and `.env.example` as the template.
- Added OpenCV video-source handling in `backend/utils/video_source.py`.
- Added a class-based YOLOv8 detector in `backend/detector.py`.
- Restricted inference to COCO classes `0,2,3,5,7`: person, car, motorcycle, bus, truck.
- Added live OpenCV annotation with bounding boxes, labels, confidence scores, and clean exit on `q`.
- Moved frame drawing helpers into `backend/utils/annotation.py` so `detector.py` stays focused on the detection lifecycle.
- Added logging for model load, video source open, FPS every configured interval, missing frames, and OpenCV/runtime errors.
- Added `evidence/` and `sample_data/` placeholders with `.gitkeep`.
- Created a local `venv/` directory and pinned dependencies in `requirements.txt`.

### Exact Command To Test

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python backend\detector.py
```

Press `q` while the OpenCV window is focused to stop the detector.

### Configuration

Copy `.env.example` to `.env` if you want local overrides:

```powershell
Copy-Item .env.example .env
```

Use the default webcam:

```dotenv
IBVAP_VIDEO_SOURCE=0
```

Use a sample video after placing it in `sample_data/`:

```dotenv
IBVAP_VIDEO_SOURCE=sample_data/my_test_video.mp4
```

### Gotchas

- An earlier Python `3.14.3` install attempt failed while NumPy attempted a local build. The current venv reports Python `3.13.15` and dependency imports pass, but Python 3.11 or 3.12 is still the safest choice for this CV stack.
- The first run may download `yolov8n.pt` automatically through Ultralytics.
- This environment may not expose a webcam or GUI display. If `cv2.imshow` or camera access fails here, test locally on a machine with a webcam and desktop session.

### Next

- Phase 2 should extend `Detector` with tracking rather than replacing the detection pipeline.

## Section 5 - Phase 2 Tracking Handoff

### Done

- Extended `backend/detector.py` to call `model.track(..., persist=True)` with the existing confidence threshold and class filter.
- Added configurable tracker selection via `IBVAP_TRACKER_TYPE`, defaulting to `bytetrack.yaml`.
- Kept ByteTrack state alive across frames by reusing the loaded model and not resetting tracking inside the frame loop.
- Updated `backend/utils/annotation.py` to draw track IDs in labels when Ultralytics provides them, for example `person #4  0.87`.
- Handled missing first-frame track IDs without crashing by falling back to class and confidence labels.
- Added first-seen track logging in the detector, for example `New track: person #4`.

### Exact Command To Test

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python backend\detector.py
```

Walk across the camera view and confirm the number in the label stays stable as the object moves. Press `q` while the OpenCV window is focused to stop the detector.

### Configuration

Use the default ByteTrack tracker:

```dotenv
IBVAP_TRACKER_TYPE=bytetrack.yaml
```

You can swap this later to another Ultralytics tracker YAML without changing code.

### Gotchas

- Track IDs may be absent on the first frame while the tracker initializes; labels intentionally omit `#id` until one is available.
- The current venv reports Python `3.13.15` and an import/config smoke test passed. Python 3.11 or 3.12 remains the safest choice if dependency installation fails on another machine.
- In this sandbox, importing Ultralytics logs permission errors when it tries to write settings/cache files under `AppData`. That did not fail the import, and it should not happen in a normal user-run terminal.
- This environment may not expose a webcam or GUI display, so final visual confirmation should happen on a desktop session with camera/video access.

### Next

- Phase 3 should consume stable track IDs for virtual-fence/event logic rather than implementing tracking again.

## Section 5 - Phase 3 Virtual Fence Handoff

### Done

- Added `backend/events.py` with a YOLO/OpenCV-independent `Fence`, `TrackedDetection`, and `FenceEventManager`.
- Added cross-product side checks and per-track previous-side memory to detect line crossings.
- Added per-track event cooldown using `IBVAP_EVENT_COOLDOWN_SECONDS`, defaulting to `4.0` seconds.
- Added structured event dicts with `event_id`, `camera_id`, `timestamp`, `event_type`, `object_type`, `track_id`, `confidence`, and `evidence_path`.
- Added event evidence snapshots saved as `evidence/<event_id>.jpg`.
- Added visible virtual-fence drawing on the OpenCV output window.
- Added `backend/event_runtime.py` to keep event/evidence/logging orchestration outside the detector class.
- Added `backend/utils/detections.py` to adapt YOLO results into plain event-layer detections.
- Added `backend/utils/evidence.py` for bounding-box crop and JPEG writing.

### Exact Command To Test

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python backend\detector.py
```

Walk across the red horizontal line in the OpenCV window. You should see one pretty-printed `VIRTUAL_FENCE_CROSS` JSON event in the console for that track, then no duplicates until the cooldown expires. Confirm a matching JPEG appears under `evidence/`.

### Configuration

Default virtual fence and event settings:

```dotenv
IBVAP_CAMERA_ID=cam_01
IBVAP_FENCE_START=0.0,0.5
IBVAP_FENCE_END=1.0,0.5
IBVAP_EVENT_COOLDOWN_SECONDS=4.0
IBVAP_EVIDENCE_DIR=evidence
```

Fence coordinates from `0.0` to `1.0` are interpreted as normalized frame coordinates, so `0.0,0.5` to `1.0,0.5` becomes a horizontal mid-frame line regardless of camera resolution.

### Gotchas

- Crossing events require a valid track ID, so detections without tracker IDs are ignored by event logic.
- If a center point lands exactly on the fence line, that frame is ignored rather than firing a noisy event.
- Final visual confirmation still needs a desktop session with webcam or sample-video access.

### Next

- Phase 4 should persist these structured events through FastAPI and SQLite rather than changing the fence-crossing logic.

## Section 5 - Phase 4 FastAPI + SQLite Handoff

### Done

- Added FastAPI and Uvicorn dependencies in `requirements.txt`.
- Added `backend/db.py` with SQLite setup, an `events` table matching the event schema, thread-locked inserts, single-event lookup, and filtered event listing.
- Updated `backend/event_runtime.py` so every fired fence event is saved to SQLite and still logged as pretty JSON.
- Added `backend/main.py` with FastAPI routes: `GET /health`, `GET /events`, and `GET /events/{event_id}`.
- Mounted the configured evidence directory at `/evidence` for snapshot access by URL.
- Added a background detector thread started from FastAPI lifespan startup, with a stop event used during shutdown.
- Added `IBVAP_DISPLAY_ENABLED` so the detector can run headless under the API server while still tracking, firing events, saving evidence, and writing SQLite rows.
- Added `IBVAP_DATABASE_PATH`, defaulting to `ibvap.db`.
- Ignored generated SQLite files in `.gitignore`.

### Exact Command To Test

```powershell
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Then open:

```text
http://localhost:8000/health
http://localhost:8000/events
```

Trigger a virtual-fence crossing on the camera or sample video, wait a few seconds, then refresh `http://localhost:8000/events`. The newest event should appear first, and its `evidence_path` should correspond to a JPEG available under `/evidence/<filename>`.

### Configuration

Headless API mode is the default:

```dotenv
IBVAP_DISPLAY_ENABLED=false
IBVAP_DATABASE_PATH=ibvap.db
```

Set `IBVAP_DISPLAY_ENABLED=true` for the OpenCV preview window while the API runs.

### Gotchas

- `uvicorn --reload` uses a reloader process. The detector thread starts inside the serving process during FastAPI lifespan startup.
- If no webcam or configured video source is available, the API can still start, but the detector thread will log the camera/source failure and stop.
- SQLite access is serialized with a module-level lock so event writes from the detector thread and reads from API requests do not share raw mutable state.

### Next

- Stop here until Phase 4 is confirmed.
- Phase 5 should build the dashboard against these HTTP endpoints instead of reading SQLite directly.
