# IBVAP - Intelligent Border Video Analytics Platform

Phase 0 through Phase 6 prototype for the IBVAP perception and backend layer.
This stage runs YOLOv8 tracking in a background thread, stores virtual-fence,
restricted-zone, and new-object events in SQLite, serves annotated MJPEG video
and live stats through FastAPI, and displays alerts in a browser dashboard.

## Setup

Use Python 3.11 or 3.12 for the virtual environment. Python 3.14 currently lacks
prebuilt wheels for parts of this stack on Windows, so it may try and fail to
compile NumPy locally.

Create and activate the virtual environment:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Configure

The detector reads settings from environment variables, with defaults in
`backend/config.py`.

Optionally copy the example file:

```powershell
Copy-Item .env.example .env
```

Default webcam:

```dotenv
IBVAP_VIDEO_SOURCE=0
```

Sample video:

```dotenv
IBVAP_VIDEO_SOURCE=sample_data/my_test_video.mp4
```

Tracker type:

```dotenv
IBVAP_TRACKER_TYPE=bytetrack.yaml
```

Virtual fence defaults to a horizontal line halfway down the frame. The
restricted zone defaults to a right-side polygon. Values from `0.0` to `1.0`
are treated as normalized frame coordinates:

```dotenv
IBVAP_CAMERA_ID=cam_01
IBVAP_LOCATION_LABEL=BOP West Gate - Camera 1
IBVAP_FENCE_START=0.0,0.5
IBVAP_FENCE_END=1.0,0.5
IBVAP_RESTRICTED_ZONE=0.62,0.18;0.95,0.18;0.95,0.82;0.62,0.82
IBVAP_EVENT_COOLDOWN_SECONDS=4.0
IBVAP_EVIDENCE_DIR=evidence
IBVAP_DATABASE_PATH=ibvap.db
IBVAP_DISPLAY_ENABLED=false
```

Default detected COCO classes include people, vehicles, and animals:

```dotenv
IBVAP_CLASS_FILTER=0,2,3,5,7,14,15,16,17,18,19,20,21,22,23
```

## Run

Start the API and detector together:

```powershell
uvicorn backend.main:app --reload
```

Open these URLs:

```text
http://localhost:8000/health
http://localhost:8000/events
http://localhost:8000/stats
http://localhost:8000/video_feed
http://localhost:8000/evidence/<event_id>.jpg
```

Serve the dashboard with `http.server` while the backend is running:

```powershell
python -m http.server 8080 -d frontend
```

Then open:

```text
http://localhost:8080/
```

With `IBVAP_DISPLAY_ENABLED=false`, the detector runs headless and still writes
crossing events to SQLite. Set it to `true` to show the OpenCV preview window.

You can still run the detector directly for local camera debugging:

```powershell
python backend/detector.py
```

The dashboard loads with the counts panel and alert feed visible and the video
hidden. Click `Open Camera` to set the MJPEG image source and show the annotated
stream; click `Close Camera` to hide the panel and clear the image source so the
browser stops pulling video. The annotated stream includes boxes, labels, track
IDs, the red virtual fence, the amber restricted-zone polygon, and current
person/vehicle/animal counts.

Crossing the virtual fence creates `VIRTUAL_FENCE_CROSS`; entering the polygon
creates `RESTRICTED_ZONE_ENTRY`; a first-seen track creates
`NEW_OBJECT_DETECTED`. Fence and zone events play the dashboard beep, flash the
red banner, and save cropped evidence photos with the timestamp and configured
location label burned into the image. New-object events appear quietly in the
feed without the alarm.

If `py -3.12` is unavailable, install Python 3.12 or 3.11, recreate the venv,
and run the install command again.
