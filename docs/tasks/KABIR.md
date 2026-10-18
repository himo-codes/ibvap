# KABIR — Event Logic: Severity, Loitering, Direction, Suppression, Sequences

**Role:** you own the *decision layer*: given tracked objects, decide what is worth interrupting an operator for, and how urgently.

**Owns:** `backend/events.py`, `backend/analytics/{severity,loitering,direction,sequence}.py`, `tests/analytics/test_{severity,loitering,direction,sequence}.py`.
**Do not touch:** `detector.py`, `main.py`, `live_state.py`, `event_runtime.py`, `db.py`, `frontend/`. Put integration needs in your PR under "Integration notes for Divyansh".

**Read first:** `CLAUDE.md`, `docs/CONTRACTS.md` §1–§3, §6, §8, `CONTRIBUTING.md`.

---

## Task list

| ID | Task | Pri | Est. | Depends |
|---|---|---|---|---|
| K1 | Severity scoring | P0 | 1.5 h | D1 |
| K2 | Loitering detector | P0 | 3 h | D1 |
| K3 | Direction-aware fence crossing | P1 | 2 h | D1 |
| K4 | Animal suppression + counter | P1 | 1 h | K1 |
| K5 | Suspicious sequence | P2 | 3 h | K2 |

Open a **draft PR after the first passing test** of K1. One task = one branch = one PR (`feat/severity`, `feat/loitering`, ...).

## Method for every task (senior workflow)

1. Read the contract signature. Do not change it.
2. Write the failing tests first, from the acceptance list below.
3. Implement the smallest thing that passes.
4. Review your own diff against CLAUDE.md §5.
5. Run `pytest -q` and `ruff check .`. Paste output in the PR.

---

## K1 — Severity scoring (`severity.py`)

**Goal:** a deterministic function mapping an `EventCandidate` to LOW/MEDIUM/HIGH, following the table in CONTRACTS §3.

Spec
- `assign_severity(c, now_local) -> Severity`. Base severity from a module-level **immutable mapping** `BASE_SEVERITY: Final[Mapping[EventType, Severity]]`.
- Modifiers, in this order: (1) animal → LOW for fence/zone/loitering; (2) night window 22:00–05:00 raises one level (cap HIGH) for `LOITERING` only. Animal wins over night.
- Night window crosses midnight: implement as `hour >= 22 or hour < 5`.
- Unknown/new event type: fall back to MEDIUM and log once at WARNING, do not raise.
- Does not mutate its input.

Acceptance (each is a test)
- Person fence cross at 14:00 → HIGH; animal fence cross → LOW.
- Loitering person at 14:00 → MEDIUM; at 23:30 → HIGH; at 04:59 → HIGH; at 05:00 → MEDIUM; animal at 23:30 → LOW.
- `CAMERA_ONLINE` → LOW; `CAMERA_OFFLINE` → HIGH; `NEW_OBJECT_DETECTED` → LOW.
- Input candidate unchanged after call.

## K2 — Loitering (`loitering.py`)

**Goal:** fire `LOITERING` when a tracked object stays inside the restricted zone longer than `dwell_seconds`.

Algorithm
- State per `track_id`: `entered_at`, `last_inside_at`, `last_seen_at`, `fired_at`.
- Point-in-polygon with your own ray-casting function (no new dependencies). Use `obj.center`. Zone is pixel-space polygon (≥3 points, else `ValueError`).
- Inside this frame → set `entered_at` if unset; update `last_inside_at`.
- Outside: keep the dwell timer alive for `grace_seconds` (detections flicker); after the grace period, reset the track's timer.
- Dwell = `now - entered_at`. When `dwell >= dwell_seconds` and not fired (or `cooldown_seconds` elapsed since `fired_at`): emit one candidate and set `fired_at`.
- **Prune** tracks not seen for `stale_seconds` (prevents unbounded memory growth — this will be reviewed).
- Candidate: `EventType.LOITERING`, `object_type`, `track_id`, `confidence=obj.confidence`, `extra={"dwell_seconds": round(dwell,1)}`.
- `update()` must be O(n objects) per call and allocate little.

Edge cases to test
- Object enters and leaves in 3 s → no event.
- Object leaves for 1 s (< grace) and returns → timer continues, event fires on schedule.
- Object leaves for 3 s (> grace) → timer resets.
- Fires once, not every frame; fires again only after cooldown.
- Two tracks independent. Track disappears (no more updates) → state pruned after `stale_seconds`.
- Empty `objects` list is valid. Degenerate polygon raises `ValueError`.
- Non-monotonic `now` (goes backwards) must not crash; treat as no elapsed time.

Acceptance: all tests pass; a 10-minute simulated run with 200 random tracks keeps the internal dict size bounded (assert in a test).

## K3 — Direction-aware fence (`direction.py` + `events.py`)

**Goal:** know *which way* the object crossed and alert only for the configured direction.

Math
- Fence from `a` to `b`. Side of point `p` = sign of cross product `(b-a) × (p-a)`. Positive = left of `a→b` = "A side".
- Crossing from A side to B side = `"A_TO_B"`; reverse = `"B_TO_A"`; same side or exactly on the line = `None` (treat zero as "no change" to avoid jitter).
- `crossing_direction(prev, curr, a, b)` is pure and tested independently.
- In `events.py`: add `extra["direction"]` to fence candidates. If `alert_direction` is not `"ANY"` and direction does not match, **do not emit** (keep side-state updated either way).
- Do not change the public behaviour for `"ANY"`.

Acceptance: horizontal, vertical, diagonal fences × both directions tested; jitter near the line does not create duplicate events beyond the existing cooldown; existing `events.py` tests (or the baseline manual test) still pass.

## K4 — Animal suppression + counter (`severity.py`)

- `is_suppressed(c)`: True iff `object_type == "animal"` and event type in {fence, zone, loitering} (i.e. it was downgraded to LOW by K1).
- Divyansh counts these and exposes `suppressed_animal_events` in `/stats`. You only provide the predicate and tests.
- Do not drop animal events (operators may still want to see them); they are LOW, not deleted.

Acceptance: truth-table test over (event type × object type).

## K5 — Suspicious sequence (`sequence.py`) — P2, only if P0/P1 merged

`SequenceDetector.ingest(candidate, now) -> list[EventCandidate]`

- **Rule A:** same `track_id` produces `LOITERING` then `VIRTUAL_FENCE_CROSS` within `window_seconds` → one `SUSPICIOUS_SEQUENCE` (`extra={"rule":"LOITER_THEN_CROSS"}`).
- **Rule B:** `repeat_count` or more `VIRTUAL_FENCE_CROSS` candidates (any tracks) within `repeat_window` → one `SUSPICIOUS_SEQUENCE` (`extra={"rule":"REPEATED_CROSSING","count":n}`); re-arm only after the window has passed.
- Keep a bounded `deque` of recent candidates; evict by time.
- Never emit a sequence from `SUSPICIOUS_SEQUENCE` input (no feedback loops).

Acceptance: both rules positive and negative tests; eviction test; no duplicate emission for the same trigger.

---

## PR description must include

- Task ID(s), what changed, files touched (only yours).
- `pytest -q` output (paste), `ruff check .` output (paste).
- A 5-line "Integration notes for Divyansh": how to construct/call your class, with the exact constructor values you expect from `cameras.json`.
- Perf: time of `update()` for 50 objects (use `timeit`; must be far below 1 ms).

## Starter prompt for your Claude

> I am Kabir. Read CLAUDE.md, docs/CONTRACTS.md, docs/tasks/KABIR.md and CONTRIBUTING.md. Start with K1. Write tests first from the acceptance list, then the implementation, in `backend/analytics/severity.py` only. Show me the plan before coding, and run pytest and ruff before you say it is done.
