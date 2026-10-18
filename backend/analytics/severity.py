"""Severity assignment analytics module.

Owner: Kabir (K1, K4) - stub.
"""

from __future__ import annotations

from datetime import datetime

from backend.analytics.types import EventCandidate, Severity


def assign_severity(c: EventCandidate, now_local: datetime) -> Severity:
    """Assign severity level to an event candidate."""
    return Severity.MEDIUM


def is_suppressed(c: EventCandidate) -> bool:
    """True when an animal-triggered fence/zone/loitering candidate was downgraded to LOW (K4)."""
    return False
