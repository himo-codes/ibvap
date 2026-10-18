"""Low-light detection and enhancement.

Owner: Kasumi (S4) - stub.
"""

from __future__ import annotations

import numpy as np


def is_low_light(frame: np.ndarray, prev_state: bool = False) -> bool:
    """Determine whether frame is low light using hysteresis."""
    return False


def enhance_low_light(frame: np.ndarray) -> np.ndarray:
    """Enhance low light frame; returns copy of frame."""
    return frame.copy()
