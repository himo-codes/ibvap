# KASUMI — Vision Quality: Camera Health, Trails, KPIs, Night, Clips

**Role:** you own everything that is about the *quality and trustworthiness of the video signal*, plus the measurements that prove the system works.

**Owns:** `backend/analytics/{health,trails,night,clips}.py`, `scripts/kpi_report.py`, `tests/analytics/test_{health,trails,night,clips}.py`, `tests/scripts/test_kpi_report.py`.
**Do not touch:** `detector.py`, `main.py`, `live_state.py`, `event_runtime.py`, `db.py`, `events.py`, `frontend/`. Integration needs go in your PR notes for Divyansh.

**Read first:** `CLAUDE.md`, `docs/CONTRACTS.md` §1–§2, §6, §8, §9, `CONTRIBUTING.md`.

---

## Task list

| ID | Task | Pri | Est. | Depends |
|---|---|---|---|---|
| S1 | Camera health monitor | P0 | 3 h | D1 |
| S2 | Trajectory trails | P1 | 2 h | D1 |
| S3 | KPI report script | P1 | 2 h | D7 (schema only) |
| S4 | Night / low-light | P2 | 2 h | D1 |
| S5 | Evidence clips | P2 | 3 h | D1 |

Open a draft PR after the first passing test. Branches: `feat/camera-health`, `feat/trails`, `feat/kpi-report`, ...

## Method for every task

Read the signature → write tests with synthetic NumPy frames → implement → measure runtime with `timeit` against the budget (CONTRACTS §9) → self-review → paste `pytest`/`ruff` output in the PR. Synthetic frames: build with `np.zeros`, `np.random.default_rng(0)`, `cv2.GaussianBlur`, `cv2.rectangle`. **Do not commit video files.**

---

## S1 — `FrameHealthMonitor` (`health.py`)

**Goal:** detect lens blocked, blur/defocus, and frozen feed, and emit `CAMERA_TAMPER` once per condition, without false alarms.

Design
- `update(frame, now)` is called every processed frame but **does real work only every `check_interval` seconds** (cheap on CPU). Downscale to ~160 px wide grayscale first.
- Signals
  - **BLUR:** variance of the Laplacian (`cv2.Laplacian(gray, cv2.CV_64F).var()`). Because absolute values differ per scene, learn a **baseline** during `warmup_seconds` (median of samples). Flag when score < `blur_ratio × baseline`.
  - **BLACKOUT / covered lens:** mean brightness < `dark_mean` **and** low standard deviation. (A dark night scene has texture; a covered lens is uniformly dark.)
  - **FROZEN:** mean absolute difference between consecutive checked frames ≈ 0 for `frozen_seconds`. Use a tiny epsilon, not exact equality (compression noise).
- **Hysteresis state machine** per condition: `OK → BAD` only after `confirm_checks` consecutive bad checks; emit exactly one candidate on the transition; return to `OK` after `confirm_checks` good checks. No repeated emissions while bad.
- Candidate: `EventType.CAMERA_TAMPER`, no track/object, `extra={"kind": "BLUR"|"BLACKOUT"|"FROZEN", "score": float}`.
- During warmup: emit nothing for BLUR; BLACKOUT and FROZEN may still fire.
- Frames that are `None`, empty, or the wrong dtype → return `[]` (never raise).

Acceptance (tests)
- Sharp random-texture image for 15 s → no events.
- Same stream then heavily blurred → exactly one `BLUR` after confirmation, not before.
- All-zero frame → `BLACKOUT`; returns to normal → state resets (a later blackout fires again).
- Identical frame repeated for > `frozen_seconds` → one `FROZEN`; slightly noisy frames → none.
- Dark-but-textured frame → no `BLACKOUT`.
- Average runtime of `update()` with 640×480 frames ≤ 2 ms amortised (document the measurement).

## S2 — Trails (`trails.py`)

- `TrailBuffer`: `dict[track_id → deque(maxlen=max_points)]` of centre points. `update()` appends; removes tracks unseen for `stale_seconds` (bounded memory).
- `points(track_id)` returns a **copy** (list), `[]` if unknown.
- `draw_trails(frame, trails)` draws in place with `cv2.polylines`, colour derived deterministically from `track_id`, thicker/brighter toward the newest point (draw a few segments, not 40 `line` calls per object if profiling says it is slow).
- Must not crash on a track with 0 or 1 point.

Acceptance: deque bound respected; pruning works; drawing changes pixels for a 5-point track and leaves the frame untouched for empty buffer; draw cost for 20 tracks ≤ 3 ms at 640×480.

## S3 — KPI report (`scripts/kpi_report.py`)

**Goal:** a command that turns the event DB into numbers we can put on a slide. **Never fabricate numbers** — if data is missing, print "n/a".

```
python scripts/kpi_report.py --db ibvap.db --hours 1 [--markdown docs/KPI_REPORT.md]
```
Outputs
- Events per camera-hour by event type and severity.
- Alert latency p50/p95 from `extra.latency_ms` (events without it are excluded and counted).
- Operator feedback: confirmed / rejected / pending; **rejection rate = rejected / (confirmed + rejected)** (n/a if denominator 0).
- Per-camera time window actually covered (first→last event) and event counts.
- Console table + optional Markdown file.

Implementation notes
- Open SQLite **read-only** (`file:...?mode=ro`, `uri=True`). Parse `extra` JSON defensively.
- Percentiles with `statistics.quantiles` or `numpy.percentile`; handle n < 2.
- Use argparse; exit code 2 with a clear message if the DB is missing.
- Business logic in pure functions (`compute_kpis(rows) -> dict`) so tests need no DB file; one test with an in-memory SQLite.

Acceptance: test with a handcrafted row set gives exact expected p50/p95 and rates; missing latency handled; empty DB prints n/a.

## S4 — Night / low light (`night.py`) — P2

- `is_low_light(frame, prev_state)` uses mean luminance of a downscaled gray frame with **hysteresis** (enter below ~55, leave above ~75; tune and document) so it does not flap.
- `enhance_low_light(frame)` returns a **new** frame: gamma correction (LUT) then CLAHE on the L channel in LAB. Must not modify the input. Budget ≤ 10 ms at 640×480.
- Tests: bright frame untouched decision; dark frame enhanced mean > original mean; hysteresis flap test; input immutability.
- Honest limit: enhancement cannot create detail that the sensor never captured; Divyansh shows a "LOW VISIBILITY" badge instead of claiming detection confidence.

## S5 — Clips (`clips.py`) — P2

- Rolling buffer of the last `seconds_before` of frames, **stored JPEG-encoded and downscaled** to `max_width` (raw 480p frames would cost ~1 MB each). Keep to ~`fps` frames per second regardless of input rate.
- `request(event_id, now)` marks a pending clip; frames keep arriving for `seconds_after`; `poll(now, out_dir)` writes finished clips and returns `[(event_id, path)]`.
- Output format: **animated GIF via Pillow** (renders in an `<img>` tag in any browser; OpenCV's `mp4v` MP4 will not play in browsers, and H.264 is usually unavailable in pip builds). Limit size (≤ ~3 MB): ≤ 5 fps, ≤ 480 px width, palette quantisation.
- Writing must not block the worker for long: build the GIF in `poll()` only when due and cap the work per call; document the cost you measured.
- Pending requests older than a limit are dropped (bounded).

Acceptance: synthetic frames at known timestamps → clip contains pre-roll and post-roll frame counts within ±1; file < size limit; two overlapping requests produce two files; buffer memory bounded.

---

## PR description must include
Task ID, behaviour summary, files touched (only yours), `pytest -q` + `ruff check .` output, measured runtime vs budget, and 5 lines of "Integration notes for Divyansh" (exact constructor args to put in `cameras.json`, where in the pipeline it is called).

## Starter prompt for your Claude

> I am Kasumi. Read CLAUDE.md, docs/CONTRACTS.md, docs/tasks/KASUMI.md and CONTRIBUTING.md. Start with S1 in `backend/analytics/health.py`. Write tests with synthetic NumPy frames first, then the implementation. Use a baseline-relative blur threshold and a hysteresis state machine. Measure runtime and show me results before declaring it done.
