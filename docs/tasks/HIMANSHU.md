# HIMANSHU — Dashboard: Camera Grid, Calibration, Alert Feed, Filters, Analytics

**Role:** you own everything the judges *see*. The backend is being rebuilt in parallel, so you work against **mock data that matches the contract**, then switch to the real API.

**Owns:** everything under `frontend/` (`index.html`, `app.js`, `style.css`, `calibrate.html`, `calibrate.js`, `mock/`).
**Do not touch:** anything under `backend/`. If you need a backend change, describe it precisely in the PR ("Integration notes for Divyansh").

**Read first:** `CLAUDE.md`, `docs/CONTRACTS.md` §4, §5, §7, `CONTRIBUTING.md`.

---

## Hard rules for the frontend

- Vanilla HTML/CSS/JS. **No frameworks, no npm, no CDN** (demo is offline). Charts are drawn with `<canvas>` or inline SVG.
- Server strings go in via `textContent` / `setAttribute`, **never `innerHTML`** (XSS).
- API base: `const API = ${location.protocol}//${location.hostname}:8000` (not hard-coded `localhost`).
- Every `fetch` has a timeout (`AbortController`, ~4 s), error handling, and a visible failure state ("Backend unreachable — retrying"). Never leave stale data looking live.
- Colour is never the only signal: severity and status also have text labels (accessibility and projector washout).
- One `state` object; render functions are pure-ish (`render(state)`); no scattered globals.
- Pause polling when the tab is hidden (`document.visibilityState`).

## Task list

| ID | Task | Pri | Est. | Depends |
|---|---|---|---|---|
| H1 | Multi-camera grid | P0 | 3 h | mock → D6 |
| H2 | Calibration page | P0 | 3 h | mock → D6 |
| H3 | Alert feed v2 | P0 | 1.5 h | D1 schema |
| H4 | Filters + search | P1 | 2 h | H3 |
| H5 | Analytics panel | P2 | 2 h | H3 |
| H6 | CSV export + print-to-PDF | P2 | 1 h | H4 |

Branches: `feat/ui-grid`, `feat/ui-calibration`, `feat/ui-alerts`, ... Open a draft PR after the first visible result.

## Step 0 — Mock mode (first hour, do not skip)

Create `frontend/mock/cameras.json`, `events.json`, `stats.json` exactly in the shapes of CONTRACTS §4 and §7 (include OFFLINE and DEGRADED cameras, LOW/MEDIUM/HIGH events, `evidence_url` null and non-null, `extra` with `dwell_seconds` and `kind`). In `app.js`, a `?mock=1` query param switches the data layer to read these files. Keep **all** network access in one module (`api.js` or one section) so switching is a one-line change. For mock video tiles use a static placeholder image/gradient.

---

## H1 — Camera grid (`index.html`, `app.js`, `style.css`)

Spec
- Responsive CSS grid, `repeat(auto-fit, minmax(320px, 1fr))`; 1–4 cameras look balanced on a 1080p projector; 2×2 for four.
- Tile: header (camera name + location), `<img src="/video_feed/{id}">`, footer (status badge LIVE/OFFLINE/DEGRADED as **text + colour**, FPS, latency, counts person/vehicle/animal, "LOW VISIBILITY" badge if `low_visibility`).
- Poll `/cameras` every 2 s. Rebuild tiles only when the camera list changes; otherwise update text nodes (do not recreate `<img>` — that restarts the MJPEG connection).
- OFFLINE: hide the stream, show a placeholder with "No signal — last seen Ns ago". Retry the stream with a cache-busting query (`?t=Date.now()`) every 5 s; when status returns to LIVE, restore the stream.
- Click a tile → focus mode (large view, other tiles shrink to a strip); `Esc` or click again to exit. Selecting a camera also filters the alert feed (H4 builds on this).
- **Performance:** a hidden/minimised tab or a tile scrolled off-screen should not hold an MJPEG connection open longer than needed (set `img.src = ""` when hidden; restore when visible).

Acceptance (screenshots in PR)
- 1, 2 and 4 cameras in mock mode; one OFFLINE and one DEGRADED visible; focus mode on/off.
- Killing the backend shows the "unreachable" banner within ~5 s and recovers on its own.

## H2 — Calibration page (`calibrate.html`, `calibrate.js`)

Purpose: set each camera's fence and zone **by clicking on the live frame**, so setup takes a minute and demonstrates "configurable border scenarios".

Spec
- Camera selector. Load `GET /cameras/{id}/snapshot` into an `<img>`; overlay a `<canvas>` of the **same displayed size** (handle responsive resizing).
- Tools: "Fence" (exactly 2 points), "Zone" (≥ 3 points, double-click or button to close), Undo, Clear, Direction selector (`ANY / A_TO_B / B_TO_A`) with an arrow drawn on the fence showing the A→B side.
- Convert click positions to **normalized** coordinates: `x / displayedWidth`, `y / displayedHeight`, clamp to [0,1], round to 4 decimals. (Use `getBoundingClientRect()`; account for scaling.)
- Draw existing config on load (`GET /cameras/{id}/config`), live preview of the polygon being edited.
- Save → `PUT /cameras/{id}/config`; show success/failure message; show the returned (server-validated) config. Disable Save until the geometry is valid.
- "Refresh snapshot" button (phones move).
- Keyboard: `Esc` cancels the current drawing.

Acceptance: in mock mode, saved JSON printed in a debug panel equals the CONTRACTS body shape; point placement is accurate when the browser window is resized; invalid shapes cannot be saved. Against the real API (after D6): move the fence, and the live stream's red line moves within a few seconds.

## H3 — Alert feed v2

- Each alert row: severity badge (text + colour), event type (human label, e.g. "Fence crossed"), **camera name**, relative + absolute time, object type, track id, confidence, evidence thumbnail from **`evidence_url`** (never a filesystem path), `extra` highlights (`dwell 12.4 s`, `direction`, `kind`), Confirm / Reject buttons, current `ack_status` visibly.
- Sort newest first; `HIGH` rows visually dominant. `NEW_OBJECT_DETECTED` is compact and quiet (no alarm).
- Alarm: beep + flashing banner for **new HIGH** events only; banner text names the camera and event ("HIGH — Fence crossed — BOP West Gate"). Do not re-alarm for events already seen (keep a `Set` of seen `event_id`s; poll with the newest timestamp). Browsers block audio before a user gesture: add a visible "Enable alarm sound" button and show its state.
- Confirm/Reject: optimistic UI update, roll back and show an error if the POST fails.
- Thumbnail click → modal with the full image (and `clip_url` if present, as `<img>`).
- Cap the DOM at ~200 rows; poll `/events?limit=...` every 2 s.

Acceptance: mock events render correctly for every severity; duplicate polling does not re-trigger the alarm; no `innerHTML` with server data (grep in review).

## H4 — Filters + search

Controls: camera, event type, severity (multi), ack status, time range (last 15 min / 1 h / today / all). Free-text search over track id / object type / camera name. Use server query params where supported (`camera_id`, `event_type`, `severity`, `ack_status`, `start_time`); do text search client-side. Filter state in the URL hash (shareable, survives refresh). Show result count and a "clear filters" button.

## H5 — Analytics panel (P2)

Pure-canvas/SVG charts, no libraries: events per hour (bar, last 12 h), severity split, confirmed vs rejected. Compute from `/events` (limit 1000) client-side. Include an empty-state ("No events yet").

## H6 — Export (P2)

"Export CSV" for the **currently filtered** events (`Blob` + `URL.createObjectURL`; escape quotes/newlines; include a UTF-8 BOM so Excel opens it cleanly). "Print report" uses `window.print()` with a print stylesheet that hides controls and shows a clean table.

---

## Design standards (judge-facing polish)

- Dark theme suitable for a control room; large type for projector (base 16 px+, key numbers 24 px+); consistent 8 px spacing grid.
- Loading, empty, and error states for **every** panel.
- Test at 1366×768 and 1920×1080; no horizontal scroll.
- Do not use red for anything except HIGH severity/alarms.

## PR description must include
Task ID, screenshots (desktop + the states above), steps to reproduce in mock mode, any contract questions, and "Integration notes for Divyansh" (endpoints you assumed and their exact shapes).

## Starter prompt for your Claude

> I am Himanshu. Read CLAUDE.md, docs/CONTRACTS.md, docs/tasks/HIMANSHU.md and CONTRIBUTING.md. Start with Step 0 (mock mode) then H1 in `frontend/` only. Vanilla JS, no CDN, no innerHTML for server data, all fetches with timeout and error states. Show me the plan and the file structure before coding, and give me steps to open it in mock mode.
