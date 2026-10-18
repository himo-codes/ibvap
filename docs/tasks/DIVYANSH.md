# DIVYANSH — Multi-Camera Core, Integration, Release

**Role:** repo owner, integrator, release manager. You own the files that every other feature plugs into, so your first job is to unblock the others (D1) and your last job is to protect the demo (D10).

**Owns:** `backend/config.py, db.py, detector.py, event_runtime.py, live_state.py, main.py, camera_manager.py`, `run.bat`, `README.md`, `CHANGELOG.md`, `requirements*.txt`, shared docs.

**Read first:** `docs/CONTRACTS.md` (you are its author/arbiter), `docs/ROADMAP.md`.

---

## Task list

| ID | Task | Pri | Est. | Depends |
|---|---|---|---|---|
| D1 | Contracts commit | P0 | 2 h | — |
| D2 | `cameras.json` registry | P0 | 1.5 h | D1 |
| D3 | StreamReader + reconnect + offline events | P0 | 2 h | D2 |
| D4 | CameraWorker (one per camera) | P0 | 3 h | D2, D3 |
| D5 | Per-camera live state | P0 | 1 h | D4 |
| D6 | New endpoints | P0 | 2 h | D5 |
| D7 | DB migration, WAL, `evidence_url`, latency | P0 | 1 h | D1 |
| D8 | Wire analytics modules (flags) | P1 | 3 h | module PRs |
| D9 | PR review and merge operations | P0 | continuous | — |
| D10 | Release: `run.bat`, README, tag, dry runs | P0 | 2 h | all |
| D11 | Store-and-forward sync simulation | P2 | — | only if everything else merged |

---

## D1 — Contracts commit (do this FIRST, target: 3 hours from kickoff)

**Goal:** everyone can import their stubs and write tests immediately.

Steps
1. Reconcile `docs/CONTRACTS.md` with real code (see its §0). Keep existing class names where they exist; update the doc to match.
2. Create `backend/analytics/` with `__init__.py`, `types.py` (§2), and **stub modules** with the exact signatures in §6 (bodies `raise NotImplementedError` or return empty results so imports and flags never crash).
3. Add `cameras.example.json` (§5); add `cameras.json` to `.gitignore`.
4. Add `requirements-dev.txt` (`pytest`, `ruff`), `pytest.ini` (`testpaths = tests`), `tests/__init__.py`, `tests/analytics/__init__.py`, one passing smoke test.
5. Commit these docs (`CLAUDE.md`, `CONTRIBUTING.md`, `docs/`, `.github/`).
6. Push, announce in chat: "D1 merged, rebase now."

Acceptance: fresh clone → `pip install -r requirements.txt -r requirements-dev.txt` → `pytest -q` green → `ruff check .` clean → app still runs exactly as before.

## D2 — Camera registry

- `config.py`: load `cameras.json` (pydantic models are fine — FastAPI already brings pydantic). Validate with human-readable errors (which camera, which key).
- **Backward compatibility:** if `cameras.json` is missing, synthesize one camera `cam_01` from legacy `.env` values. Existing demo must not break.
- Provide `resolve_geometry(cam, frame_w, frame_h)` returning pixel-space fence/zone (normalized if all coords ≤ 1.0, as today).
- Unique `camera_id` enforced; unknown keys rejected (typos should fail loudly).

Acceptance: unit tests for normalized→pixel, legacy fallback, duplicate id, bad polygon (<3 points).

## D3 — StreamReader

- One daemon thread per camera. `cv2.VideoCapture(source)`; `CAP_PROP_BUFFERSIZE=1`. Keep **only the latest frame** (drop stale frames — latency beats completeness).
- Reconnect with exponential backoff (2 s → 4 → 8 → cap 10 s). Release capture on every failure.
- Status machine: `CONNECTING → LIVE → OFFLINE`. Emit `CAMERA_OFFLINE` once after 5 s without a frame; emit `CAMERA_ONLINE` once on recovery. No event spam while offline.
- File sources: `loop: true` rewinds at EOF (demo fallback); otherwise status `OFFLINE` at EOF.
- Track capture timestamp per frame (used for `latency_ms`) and measured FPS (rolling 2 s).
- Clean shutdown via `threading.Event`; no thread leaks on reload.

Acceptance: manual — disable phone WiFi → one `CAMERA_OFFLINE` in ≤ 6 s; re-enable → stream returns without restarting the app and exactly one `CAMERA_ONLINE`.

## D4 — CameraWorker

- One thread per camera, owns: StreamReader, **its own `YOLO(...)` instance** (tracker state lives in the model; sharing one instance mixes track IDs across cameras), analytics detectors, cooldown dict keyed by `(camera_id, track_id)`.
- Honour `inference_stride` (process every Nth frame; reuse last annotations in between so the stream stays smooth).
- Resize to `target_width` before inference.
- `torch.set_num_threads(max(1, cpu_count // n_cameras))` at startup.
- **Error isolation:** wrap the per-frame body in try/except; log with camera id; after 5 consecutive failures restart that worker with backoff. One bad camera never affects others.
- Pipeline order is normative: CONTRACTS §8.
- Evidence stamp uses the camera's own `location`.

Acceptance: 2 phones + 1 video file run simultaneously ≥ 8 FPS each (read from `/cameras`); killing one stream does not change the other two's FPS by more than ~20%.

## D5 — Live state

`live_state.py`: `dict[camera_id] → {annotated_jpeg, raw_frame, counts, status, fps, latency_ms, last_frame_ts, low_visibility}` behind one lock. Writers copy-then-swap; readers never hold the lock while encoding JPEG.

## D6 — Endpoints (CONTRACTS §7)

- `/cameras`, `/video_feed/{id}`, `/cameras/{id}/snapshot`, `/cameras/{id}/config` GET/PUT, `/stats?camera_id=`, `/events` new filters.
- MJPEG generator: sleep ~1/15 s between frames, stop on client disconnect, never busy-loop.
- `PUT config`: validate (fence has 2 points, zone ≥ 3, values finite), write `cameras.json` via temp file + `os.replace`, hot-swap into the worker under a lock. Reject with 422 and a clear message on invalid input.
- CORS stays permissive for the LAN demo; do not expose beyond localhost in the README.

Acceptance: `curl` examples for each endpoint in the PR description; Himanshu's mocks match real shapes (diff them).

## D7 — Database

- Migration exactly as CONTRACTS §4, idempotent, run in lifespan startup.
- WAL mode. Use a **single writer** (a `queue.Queue` consumed by one thread) or a connection per thread; never share one `sqlite3.Connection` across threads.
- API returns `evidence_url`, never `evidence_path`.
- Write `extra.latency_ms`.

Acceptance: app starts on an old `ibvap.db` without data loss; new columns present; 3 workers writing concurrently produce no "database is locked" errors in a 5-minute soak.

## D8 — Wire analytics (flags)

As each module PR merges, call it from the worker exactly per CONTRACTS §8, guarded by `analytics.<name>` flags. A module that raises is disabled for that camera for 60 s and logged. Convert normalized geometry to pixels before constructing detectors. Count `is_suppressed()` into `suppressed_animal_events`. Record integration notes in `CHANGELOG.md`.

## D9 — PR review checklist (use on every PR)

1. Template complete; task ID present; only owner's files changed (`git diff --stat`).
2. `pytest -q` and `ruff check .` pass locally on **your** machine after checkout.
3. Read the diff for: global state, I/O in pure modules, unbounded dicts (memory leaks), thread safety, blocking calls on the request path.
4. Run the app with the PR and exercise the acceptance criteria yourself.
5. Squash-merge with a Conventional Commit title; tell the author to rebase siblings.
6. Update `PROGRESS.md` and `CHANGELOG.md [Unreleased]`.

Be fast and specific: comment with the exact change wanted. Prefer "merge now, follow-up PR" for non-blocking nits during Day 2.

## D10 — Release and demo hardening

- `run.bat` (activate venv, start backend on 127.0.0.1:8000, frontend on :8080, open browser).
- Update README: multi-camera setup, phone apps, hotspot, `cameras.json`, tests.
- Fresh-clone test on a **second machine** (Python 3.13). Fix what breaks.
- `yolov8n.pt` present locally (offline run must not download).
- Two rehearsals with the real phones on the real hotspot, **internet disabled**. Record a 2–3 min backup video.
- Recorded-clip fallback source prepared for every camera in a `cameras.demo-fallback.json`.
- Laptop: plugged in, best-performance mode, notifications off, browser at 100% zoom, F11.
- Tag: `git tag v1.0-demo && git push --tags`. Freeze `main`.

### Demo-day checklist
`[ ]` hotspot on, phones joined, IPs verified in browser · `[ ]` phones on tripods, charging, screen-sleep off · `[ ]` `run.bat` tested · `[ ]` DB/evidence cleaned · `[ ]` fallback config ready · `[ ]` backup video on desktop · `[ ]` roles assigned (who walks, who narrates, who clicks) · `[ ]` KPI output saved.

---

## Working method (senior habits)

- Merge D1 before anything else; unblocking three people is worth more than perfecting D4.
- Never batch-merge at night; merge one PR, run the app, then the next.
- Keep a running list of "integration notes" from PR descriptions and apply them in D8 in one sitting.
- When two docs disagree, fix the doc first, then the code.
