# IBVAP - Intelligent Border Video Analytics Platform

Phase 0 through Phase 2 prototype for the IBVAP perception layer. This stage
runs YOLOv8 tracking on a webcam or video file and annotates people and vehicles
with persistent track IDs.

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

## Run

```powershell
python backend/detector.py
```

The OpenCV window should show live tracked detections for people, cars,
motorcycles, buses, and trucks. Labels include persistent track IDs, such as
`person #4  0.87`. Press `q` while the window is focused to exit.

If `py -3.12` is unavailable, install Python 3.12 or 3.11, recreate the venv,
and run the install command again.
