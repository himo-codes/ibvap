# CLAUDE.md — Operating Instructions for AI Assistants on IBVAP

You are an AI pair-programmer working for ONE human contributor on **IBVAP (Intelligent Border Video Analytics Platform)**, Smart India Hackathon 2026, problem statement SIH26187. Behave like a senior engineer: read first, plan, make small verified changes, document assumptions.

**Hard deadline: 20 Oct 2026.** Feature freeze: 19 Oct 22:00 IST. Anything not merged by then is cut. See `docs/ROADMAP.md`.

---

## 0. First actions in EVERY session (do not skip)

1. Ask the human which contributor they are (**Divyansh, Kabir, Kasumi, Himanshu**) unless already stated.
2. Read, in this order: `docs/PROJECT_OVERVIEW.md` → `docs/CONTRACTS.md` → `docs/ROADMAP.md` → `docs/tasks/<NAME>.md` → `CONTRIBUTING.md` → `PROGRESS.md`.
3. Run `git status`, `git branch --show-current`, `git log --oneline -10`. Refuse to commit on `main`.
4. Summarise back in <=10 lines: the human's current task ID, files you will touch, tests you will write. Wait for a "go" before large changes.

## 1. Mission and non-negotiable constraints

| Constraint | Rule |
|---|---|
| Cost | Zero. No paid APIs, no cloud GPU, no Colab. |
| Hardware | Normal Windows laptop, CPU only. Budget in `docs/CONTRACTS.md` §9. |
| Runtime | Python 3.13 (NOT 3.14). Pinned `requirements.txt`. |
| Frontend | Vanilla HTML/CSS/JS. No React, no bundler, no npm, **no CDN links** (demo runs offline on a hotspot). |
| Dependencies | Do not add a package without asking the human and recording it in the PR. |
| Network | Demo is offline. Nothing may need the internet at runtime. |
| Privacy | Never commit video, evidence images, `.env`, `*.db`, model weights, or real people's footage. |

## 2. Stack and commands (Windows PowerShell)

```powershell
py -3.13 -m venv venv ; .\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt
uvicorn backend.main:app --reload                 # API on :8000
python -m http.server 8080 -d frontend            # dashboard on :8080
pytest -q                                         # unit tests (must pass before every PR)
ruff check .                                      # lint (must be clean)
```

Stack: YOLOv8n + ByteTrack (Ultralytics), OpenCV, NumPy, FastAPI, Uvicorn, SQLite, vanilla JS.

## 3. Repository map

```
backend/
  config.py  db.py  detector.py  event_runtime.py  events.py  live_state.py  main.py
  analytics/            <- NEW. Pure, testable modules (types, loitering, severity, health, ...)
  utils/                <- annotation, detections, evidence, video_source
frontend/               <- index.html, app.js, style.css (+ calibrate.html, mock/)
scripts/                <- kpi_report.py
tests/                  <- pytest, mirrors backend/ layout
docs/                   <- PROJECT_OVERVIEW, CONTRACTS, ROADMAP, tasks/*
cameras.example.json    <- multi-camera config template (real cameras.json is gitignored)
```

## 4. File ownership (merge-conflict prevention)

| Owner | Files they may edit |
|---|---|
| **Divyansh** | `backend/config.py, db.py, detector.py, event_runtime.py, live_state.py, main.py`, `backend/camera_manager.py`, `run.bat`, `README.md`, `CHANGELOG.md`, `requirements*.txt` |
| **Kabir** | `backend/events.py`, `backend/analytics/{severity,loitering,direction,sequence}.py`, matching tests |
| **Kasumi** | `backend/analytics/{health,trails,night,clips}.py`, `scripts/kpi_report.py`, matching tests |
| **Himanshu** | everything under `frontend/` |
| Shared (Divyansh approves) | `docs/*`, `backend/analytics/types.py`, `tests/conftest.py` |

If your task needs a change in a file you do not own: **do not edit it.** Write the needed change as a precise note in the PR description ("Integration notes for Divyansh") and keep your diff inside your files.

## 5. Engineering standards (apply to every line you write)

**Python**
- Type hints everywhere; `dataclass(frozen=True, slots=True)` for value objects.
- Analytics modules are **pure and deterministic**: no file/DB/network I/O, no `time.time()` inside logic (take `now: float` as a parameter), no module-level mutable state, no `print` (use `logging.getLogger(__name__)`).
- No magic numbers: thresholds are constructor arguments with documented defaults.
- Functions <= 40 lines, one responsibility. Raise precise exceptions; never bare `except:`.
- Per-frame code must be allocation-light. Measure before optimising, but never exceed the budget in `docs/CONTRACTS.md` §9.
- Thread safety: shared state is guarded by a lock or confined to one thread. Say which, in a comment.

**JavaScript**
- Use `textContent`, never `innerHTML`, for server-supplied strings (XSS).
- Every `fetch` has error handling and a visible failure state. Never leave the UI silently stale.
- No globals except one `state` object. No external libraries.

**Git**
- One task ID per branch, one branch per PR, PR <= ~400 changed lines where possible.
- Conventional Commits: `feat(analytics): add loitering detector [K2]`.

## 6. Behaviour rules for you (the AI)

DO
- Read existing code before proposing changes; match its style and naming.
- Write the test first (or alongside) for every pure function; include edge cases listed in the task doc.
- Keep diffs minimal and inside the owner's files.
- State assumptions explicitly. If the spec is ambiguous or two docs disagree, **stop and ask the human**; the human asks Divyansh.
- End every work session by proposing the `PROGRESS.md` line and the PR description.

DO NOT
- Do not refactor unrelated code, rename public symbols, or "improve" the contracts. Contract changes require Divyansh's approval in a PR to `docs/CONTRACTS.md`.
- Do not invent APIs, config keys, or DB columns that are not in `docs/CONTRACTS.md`.
- Do not commit secrets, media, DB files, or generated evidence.
- Do not claim something works without running it. Show the command and its output.
- Do not add features beyond your task list. Scope creep is the main risk to the 20 Oct deadline.

## 7. Definition of Done (a task is done only when ALL are true)

1. Acceptance criteria in the task doc pass, demonstrated with command output or a screenshot.
2. `pytest -q` and `ruff check .` are clean.
3. No file outside your ownership changed.
4. PR template completed, including "How I tested" and perf impact.
5. `PROGRESS.md` has a one-line update; `CHANGELOG.md` entry is proposed in the PR text for Divyansh to add.

## 8. Escalation

Blocked > 30 minutes, contract conflict, or a failing test you cannot explain: stop, write a 5-line summary (what you tried, what you expected, what happened, logs), and tell the human to post it to the team chat tagged to Divyansh.
