# IBVAP — Project Overview

> Single source of truth for **what exists today** and **what we are adding before 20 Oct 2026**.
> Audience: all four contributors and their AI assistants. Read this before any task doc.

## 1. Purpose

IBVAP turns ordinary camera feeds into an alert-generating border-monitoring system. Operators should not stare at screens; the system detects people, vehicles and animals, tracks them, evaluates **virtual fences and restricted zones**, and raises **evidence-backed alerts** that a human confirms or rejects.

**Pitch:** *Retrofit-first, edge-first.* We do not replace cameras; we add a software layer. All inference runs locally on the laptop (the "edge node"); phones act as IP cameras over a local hotspot. No internet required.

SIH26187 · Team Clanaura · Rungta International Skills University.

## 2. Target architecture (after this sprint)

```
 Phone 1 (IP Webcam) ─┐
 Phone 2 (IP Webcam) ─┼─ WiFi hotspot ─►  LAPTOP (edge node)
 Phone 3 / video file ┘                    │
                                           ├─ StreamReader (1 thread / camera, latest-frame, auto-reconnect)
                                           ├─ CameraWorker (1 thread / camera, own YOLO + ByteTrack)
                                           │    health ► night-enhance ► detect+track ► fence/zone
                                           │    ► loitering ► sequence ► severity ► evidence/clip ► DB
                                           ├─ FastAPI  (/cameras /video_feed/{id} /events /stats ...)
                                           └─ Dashboard (camera grid, alert feed, calibration, analytics)
```

## 3. Current feature inventory (baseline v0.1.0)

| # | Feature | Notes |
|---|---|---|
| 1 | Detection of person, vehicle (car/motorcycle/bus/truck), animal (COCO 14–23) | YOLOv8n, CPU, confidence default 0.35 |
| 2 | Persistent tracking IDs | ByteTrack via Ultralytics; short-term only (no re-ID after full occlusion) |
| 3 | Virtual fence line crossing | Centre-point side-flip, per-track cooldown |
| 4 | Restricted-zone polygon entry | Configurable polygon, same cooldown |
| 5 | `NEW_OBJECT_DETECTED` quiet event | Informational, no alarm |
| 6 | Live annotated MJPEG stream | Boxes, labels, IDs, fence, zone, counts overlay |
| 7 | Current-frame counts | `/stats`, not cumulative |
| 8 | Evidence crops | Timestamp + location label stamped on image |
| 9 | Alarm UX | Audible beep + flashing red banner for fence/zone events |
| 10 | Human-in-the-loop | Confirm / Reject via `POST /events/{id}/ack` |
| 11 | REST API + SQLite | Filters: camera, type, time range, limit |
| 12 | Vanilla dashboard | No build step; camera open/close toggle |
| 13 | `.env` configuration | Model, thresholds, fence, zone, cooldown, paths |

### Known limitations of the baseline
- Single camera only. No loitering. No severity. No camera-health alerts.
- API exposes absolute `evidence_path` (Windows path). Replaced by `evidence_url` (see CONTRACTS §4).
- Fence/zone configured via `.env` only; no UI.

## 4. Planned features (this sprint)

Priority: **P0** must ship · **P1** should ship · **P2** ship only if time remains (cut first).

| ID | Feature | Owner | Pri | Depends on |
|---|---|---|---|---|
| D1 | Contracts commit (types, schema migration, config template, test scaffold) | Divyansh | P0 | — |
| D2 | `cameras.json` registry + per-camera config | Divyansh | P0 | D1 |
| D3 | Threaded stream reader, auto-reconnect, `CAMERA_OFFLINE/ONLINE` | Divyansh | P0 | D2 |
| D4 | Per-camera worker (own YOLO/tracker, frame stride, error isolation) | Divyansh | P0 | D2, D3 |
| D5 | Per-camera live state | Divyansh | P0 | D4 |
| D6 | New endpoints: `/cameras`, `/video_feed/{id}`, snapshot, config GET/PUT | Divyansh | P0 | D5 |
| D7 | DB migration, WAL, `evidence_url`, `latency_ms` | Divyansh | P0 | D1 |
| D8 | Wire analytics modules into worker behind feature flags | Divyansh | P1 | K*/S* PRs |
| D10 | `run.bat`, README, tag `v1.0-demo`, dry runs | Divyansh | P0 | all |
| K1 | Severity scoring (LOW/MEDIUM/HIGH) | Kabir | P0 | D1 |
| K2 | Loitering / dwell-time (`LOITERING`) | Kabir | P0 | D1 |
| K3 | Direction-aware fence crossing | Kabir | P1 | D1 |
| K4 | Animal suppression + "false alerts avoided" counter | Kabir | P1 | K1 |
| K5 | Suspicious sequence (`SUSPICIOUS_SEQUENCE`) | Kabir | P2 | K2 |
| S1 | Camera health: blur / blackout / frozen (`CAMERA_TAMPER`) | Kasumi | P0 | D1 |
| S2 | Trajectory trails | Kasumi | P1 | D1 |
| S3 | KPI report script | Kasumi | P1 | D7 |
| S4 | Night / low-light enhancement + badge flag | Kasumi | P2 | D1 |
| S5 | Evidence clip (rolling buffer → GIF) | Kasumi | P2 | D1 |
| H1 | Multi-camera grid UI | Himanshu | P0 | mock API → D6 |
| H2 | Fence/zone calibration page | Himanshu | P0 | mock API → D6 |
| H3 | Alert feed v2 (severity, camera, `evidence_url`, alarm w/ camera name) | Himanshu | P0 | D1 |
| H4 | Filters + search | Himanshu | P1 | H3 |
| H5 | Analytics panel (events/hour, confirmed vs rejected) | Himanshu | P2 | H3 |
| H6 | CSV export + print-to-PDF | Himanshu | P2 | H4 |

### Explicitly OUT of scope for 20 Oct
ANPR, face recognition, cross-camera re-identification, store-and-forward sync, Telegram alerts, auth/RBAC, Docker. They remain in the roadmap pitch ("future work") but must not consume sprint time.

## 5. Demo scenario (judges, on Divyansh's laptop, hotspot only)

1. Dashboard shows 3 camera tiles (2 phones + 1 recorded clip), all LIVE.
2. Person crosses fence on phone 1 → HIGH alert, alarm, banner names the camera, evidence image.
3. Person stays in zone → `LOITERING` alert.
4. Animal/vehicle shown → lower severity; "false alerts avoided" counter increments.
5. Cover a phone lens → `CAMERA_TAMPER`; kill phone WiFi → `CAMERA_OFFLINE`; restore → auto reconnect.
6. Operator confirms one alert, rejects another.
7. Open calibration page, move the fence live. Show filters/search.
8. Show `scripts/kpi_report.py` output (false alerts per camera-hour, latency p50/p95).
9. Say: "Internet is off. Everything you saw ran on this laptop."

## 6. KPIs we will report (measured, never invented)

FPS per camera · end-to-end alert latency p50/p95 · alerts per camera-hour by type · rejected/(confirmed+rejected) ratio · camera reconnect time. Produced by `scripts/kpi_report.py` (S3).

## 7. Glossary

**Edge node** the laptop running inference · **Track** persistent object ID within one camera · **Fence** line segment; crossing = centre point changes side · **Zone** polygon · **Dwell** continuous time inside a zone · **Candidate** an `EventCandidate` before severity/cooldown/persistence · **Contract** the types and interfaces in `docs/CONTRACTS.md`.
