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

- Stop here until Phase 2 is confirmed.
- Phase 3 should consume stable track IDs for virtual-fence/event logic rather than implementing tracking again.
