# ROADMAP — Execution Order to 20 Oct 2026

> Dates are IST. Today = Sun 18 Oct. Deadline = Tue 20 Oct. This leaves **~2.5 working days**, so scope is cut hard. P2 items exist only to absorb spare time.
> If the real demo time is earlier than assumed below, Divyansh moves the freezes earlier and cuts P2 first.

## 1. Dependency hierarchy

```
WAVE 0 — Unblock (Day 1, first ~3 h)
  D1 Contracts commit ───────────────► MERGE FIRST. Everyone rebases on it.
  (meanwhile everyone: fork, clone, venv, read docs, write tests against CONTRACTS signatures)

WAVE 1 — Parallel P0 (Day 1 → Day 2 noon)           [no cross-dependencies; each works in own files]
  Divyansh : D2 → D3 → D4 → D5 → D6 → D7           (multi-camera core)
  Kabir    : K1 severity → K2 loitering
  Kasumi   : S1 camera health
  Himanshu : H1 grid (mock API) → H2 calibration (mock API) → H3 alert feed v2

WAVE 2 — Integrate + P1 (Day 2 noon → 18:00)
  Divyansh : D8 wires K1,K2,S1 into workers; merges PRs; switches Himanshu from mocks to real API
  Kabir    : K3 direction → K4 animal suppression
  Kasumi   : S2 trails → S3 KPI script
  Himanshu : H4 filters/search, connect to real endpoints, fix integration bugs

WAVE 3 — P2 only if Wave 2 is fully merged (Day 2 18:00 → 22:00)
  K5 sequence · S4 night · S5 clips · H5 analytics · H6 export

WAVE 4 — Stabilise (Day 3, bug-fix only)
  Divyansh : D10 run.bat, README, dry runs (hotspot only), backup video, tag v1.0-demo
  Everyone : bug fixes, rehearsal roles, no new features
```

## 2. Hard checkpoints

| When (IST) | Gate | Owner | If missed |
|---|---|---|---|
| Day 1 +3 h | **D1 merged** | Divyansh | Others continue on stubs from CONTRACTS; slip must be announced |
| Day 1 night | Each person has a **draft PR** open for their first P0 task | all | Divyansh reassigns in morning |
| Day 2 12:00 | All P0 PRs merged; 2-camera run works end-to-end | Divyansh | Cut D8 flags for incomplete modules; keep stable |
| Day 2 18:00 | All P1 PRs merged; tag `v0.9-rc` | Divyansh | Remaining P1 become P2 |
| **Day 2 22:00** | **FEATURE FREEZE.** Only bug-fix PRs after this | Divyansh | Unmerged feature = cut |
| Day 3 12:00 | `v1.0-demo` tagged; 2 full rehearsals done | Divyansh | Roll back to `v0.9-rc` |
| Day 3 | Buffer: backup video, laptop power/network checks | all | — |

## 3. Merge order (reduces conflicts)

1. `docs/contracts` (D1) → 2. `feat/multicam-config` (D2) → 3. `feat/stream-reader` (D3) → 4. `feat/camera-worker` (D4–D7) → 5. analytics modules in any order (they only add new files) → 6. frontend PRs (touch only `frontend/`) → 7. `feat/wire-analytics` (D8) → 8. release PR (D10).

Rule: **a contributor rebases on `upstream/main` before every push.** Divyansh merges with **squash**.

## 4. Cut line (decide now, not at 3 a.m.)

| Always ship | Ship if on time | Cut first |
|---|---|---|
| D1–D7, D10, K1, K2, S1, H1–H3 | D8, K3, K4, S2, S3, H4 | K5, S4, S5, H5, H6 |

A half-working P2 feature is worse than none: it must be behind its `analytics.*` flag **off** in the demo config or not merged.

## 5. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| CPU too slow for 3 cameras | High | High | `inference_stride`, 640 width, ≤2 live phones + 1 recorded clip; show FPS honestly |
| Merge conflicts in shared files | Med | High | Ownership table in CLAUDE.md; analytics as new files; D1 first |
| Phone WiFi drops / IP changes in venue | High | High | Reconnect logic; recorded-clip fallback per camera; fixed IPs checked before demo |
| Python 3.14 / wheel problems on a teammate's PC | Med | Med | Python 3.13 only; fresh-clone test by a teammate on Day 2 |
| AI-written code that "looks right" but is untested | High | Med | Tests mandatory; PR must include real command output |
| Scope creep | High | High | Cut line above; Divyansh is the only person who can add scope |
| Tracker ID switches after occlusion | Med | Low | Documented limitation; never claim re-ID |
| Demo laptop thermal throttling | Med | Med | Power plugged, best-performance mode, close other apps |

## 6. Communication cadence

- **Kickoff (15 min)**: confirm owners, fork/clone done, everyone can run `pytest -q`.
- **Standup** twice a day (Day 2 ~10:00 and ~18:00), 5 minutes each: *done / doing / blocked*. Written in team chat if a call is not possible.
- **Blocker rule**: blocked > 30 min → post in chat with logs. Do not wait silently.
- **Status**: each merged PR adds one line to `PROGRESS.md`.

## 7. Review SLA

Divyansh targets first response on a PR within 60 minutes during working hours. Contributors should open **draft PRs early** (after the first working commit) so integration issues surface on Day 1, not Day 2.
