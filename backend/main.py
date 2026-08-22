"""FastAPI entrypoint for the IBVAP backend."""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from backend.config import Settings, get_settings
from backend.db import get_event, init_db, list_events
from backend.detector import Detector

LOGGER = logging.getLogger(__name__)

settings = get_settings()
detector_stop_event = threading.Event()
detector_thread: threading.Thread | None = None
detector_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize storage and start/stop the detector worker."""
    init_db(settings.database_path)
    settings.evidence_dir.mkdir(parents=True, exist_ok=True)
    start_detector_thread(settings)
    yield
    detector_stop_event.set()


app = FastAPI(title="IBVAP Backend", lifespan=lifespan)
app.mount("/evidence", StaticFiles(directory=settings.evidence_dir), name="evidence")


@app.get("/health")
def health() -> dict[str, str]:
    """Return API health status."""
    return {"status": "ok"}


@app.get("/events")
def read_events(
    camera_id: str | None = None,
    event_type: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> list[dict[str, Any]]:
    """Return stored events newest first."""
    return list_events(
        camera_id=camera_id,
        event_type=event_type,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        db_path=settings.database_path,
    )


@app.get("/events/{event_id}")
def read_event(event_id: str) -> dict[str, Any]:
    """Return one stored event by ID."""
    event = get_event(event_id, settings.database_path)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def start_detector_thread(settings: Settings) -> None:
    """Start the blocking detector loop in a background thread."""
    global detector_thread
    with detector_lock:
        if detector_thread is not None and detector_thread.is_alive():
            return
        detector_stop_event.clear()
        detector_thread = threading.Thread(
            target=run_detector,
            args=(settings, detector_stop_event),
            name="ibvap-detector",
            daemon=True,
        )
        detector_thread.start()
        LOGGER.info("Detector thread started")


def run_detector(settings: Settings, stop_event: threading.Event) -> None:
    """Run detector worker and keep API alive if camera startup fails."""
    try:
        Detector(settings, stop_event=stop_event).run()
    except (RuntimeError, ValueError) as exc:
        LOGGER.error("Detector worker stopped: %s", exc)
