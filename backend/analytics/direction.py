"""Crossing direction analytics module.

Owner: Kabir (K3) - stub.
"""

from __future__ import annotations

from typing import Literal

from backend.analytics.types import Point


def crossing_direction(
    prev: Point,
    curr: Point,
    a: Point,
    b: Point,
) -> Literal["A_TO_B", "B_TO_A"] | None:
    """Determine crossing direction relative to vector A -> B."""
    return None
