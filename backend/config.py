"""Configuration for the IBVAP detection prototype."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"

DEFAULT_MODEL_PATH = "yolov8n.pt"
DEFAULT_CONFIDENCE_THRESHOLD = 0.35
DEFAULT_CLASS_FILTER = (0, 2, 3, 5, 7)
DEFAULT_VIDEO_SOURCE = "0"
DEFAULT_FRAME_LOG_INTERVAL = 30

WINDOW_NAME = "IBVAP Detection"
EXIT_KEY = "q"
BOX_COLOR = (0, 255, 0)
TEXT_COLOR = (255, 255, 255)
TEXT_BACKGROUND_COLOR = (0, 128, 0)
BOX_THICKNESS = 2
TEXT_FONT = 0
TEXT_SCALE = 0.6
TEXT_THICKNESS = 2
TEXT_PADDING = 6


def _load_env_file(path: Path = ENV_FILE) -> None:
    """Load simple KEY=VALUE pairs from a local .env file if present."""
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _parse_class_filter(raw_value: str) -> tuple[int, ...]:
    """Parse a comma-separated list of COCO class ids."""
    return tuple(int(item.strip()) for item in raw_value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    """Runtime settings for the detector."""

    model_path: str
    confidence_threshold: float
    class_filter: tuple[int, ...]
    video_source: str
    frame_log_interval: int


def get_settings() -> Settings:
    """Build settings from .env/environment values with project defaults."""
    _load_env_file()

    return Settings(
        model_path=os.getenv("IBVAP_MODEL_PATH", DEFAULT_MODEL_PATH),
        confidence_threshold=float(
            os.getenv("IBVAP_CONFIDENCE_THRESHOLD", str(DEFAULT_CONFIDENCE_THRESHOLD))
        ),
        class_filter=_parse_class_filter(
            os.getenv(
                "IBVAP_CLASS_FILTER",
                ",".join(str(class_id) for class_id in DEFAULT_CLASS_FILTER),
            )
        ),
        video_source=os.getenv("IBVAP_VIDEO_SOURCE", DEFAULT_VIDEO_SOURCE),
        frame_log_interval=int(
            os.getenv("IBVAP_FRAME_LOG_INTERVAL", str(DEFAULT_FRAME_LOG_INTERVAL))
        ),
    )
