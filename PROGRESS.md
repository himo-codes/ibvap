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

- The current machine reports Python `3.14.3`, and dependency installation failed while NumPy attempted a local build. Use Python 3.11 or 3.12 for the venv before running the test command.
- The first run may download `yolov8n.pt` automatically through Ultralytics.
- This environment may not expose a webcam or GUI display. If `cv2.imshow` or camera access fails here, test locally on a machine with a webcam and desktop session.

### Next

- Stop here until Phase 1 is confirmed.
- Phase 2 should extend `Detector` with tracking rather than replacing the detection pipeline.
