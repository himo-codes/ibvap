# Contributing to IBVAP

Thanks for building this. We have **until 20 Oct 2026**, four people, and one shared demo. These rules exist to keep four parallel streams of work from colliding. They are short on purpose; follow them exactly.

## 1. Roles

| Person | Role |
|---|---|
| **Divyansh** | Repo owner. Reviews, tests, merges, owns `main`, owns contracts and release. |
| **Kabir** | Event logic (severity, loitering, direction, suppression, sequences) |
| **Kasumi** | Video quality (health, trails, KPIs, night, clips) |
| **Himanshu** | Dashboard (`frontend/`) |

Your assignment is in `docs/tasks/<YOUR_NAME>.md`. Do **only** those tasks.

## 2. One-time setup

```powershell
# 1. Fork the repo on GitHub (button, top-right), then:
git clone https://github.com/<your-username>/ibvap-sih2026.git
cd ibvap-sih2026
git remote add upstream https://github.com/sahariya-divyansh/ibvap-sih2026.git
git remote -v                         # origin = your fork, upstream = Divyansh's repo

# 2. Python 3.13 environment (NOT 3.14)
py -3.13 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt -r requirements-dev.txt

# 3. Sanity check — both must pass on a clean checkout
pytest -q
ruff check .
```

If anything fails here, stop and tell Divyansh before writing code.

## 3. Daily workflow (every task, every time)

```powershell
git checkout main
git pull upstream main                 # always start from the latest
git push origin main                   # keep your fork's main in sync
git checkout -b feat/<short-name>      # one task = one branch

# ... work in small steps; commit often ...
git add <specific files>               # avoid `git add .` (you may add junk)
git commit -m "feat(analytics): add loitering detector [K2]"

# before pushing, replay your commits on the newest main:
git fetch upstream
git rebase upstream/main               # resolve conflicts here, then: git rebase --continue
pytest -q ; ruff check .
git push -u origin feat/<short-name>   # after a rebase use: git push --force-with-lease
```

Then open a Pull Request **from your fork's branch into `upstream:main`**. Open it as a **Draft** after your first working commit; mark "Ready for review" when the Definition of Done is met.

### Branch names
`feat/<name>` new feature · `fix/<name>` bug fix · `docs/<name>` documentation · `test/<name>` tests only.

### Commit messages (Conventional Commits)
`<type>(<scope>): <summary> [TASK-ID]` — types: `feat fix docs test refactor perf chore`. Imperative mood, ≤ 72 chars, e.g. `fix(health): avoid false BLACKOUT on dark textured scenes [S1]`.

## 4. Pull request rules

- **One task per PR.** Aim for ≤ 400 changed lines. Split if bigger.
- **Only edit files you own** (table in `CLAUDE.md` §4). Need a change elsewhere? Say so in the PR description.
- Fill in the PR template completely, including real test output. "Works on my machine" without output will be sent back.
- Do not change `docs/CONTRACTS.md` in a feature PR. Contract changes get their own PR approved by Divyansh.
- Never force-push to `main`. Force-push to **your own branch** only with `--force-with-lease`.
- Do not merge your own PR. Do not resolve review threads for the reviewer.

## 5. Review and merge (Divyansh)

Checklist applied to every PR: template complete · only owner's files · tests and lint pass on Divyansh's machine · diff read for global state, I/O in pure modules, unbounded growth, thread-safety, blocking calls · behaviour verified by running the app · squash-merge with a Conventional Commit title · `PROGRESS.md` and `CHANGELOG.md` updated.

Target response time: 60 minutes during working hours. Merge order follows `docs/ROADMAP.md` §3. After a merge, every contributor rebases their open branch.

## 6. Testing standards

- Pure modules (`backend/analytics/*`): unit tests with synthetic inputs and an injected `now`. No video files, no sleeps, no network.
- Test the edges listed in your task doc: empty input, flicker, time going backwards, degenerate geometry, pruning of old state.
- Frontend: manual test matrix in the PR (mock mode, empty state, error state, offline camera) with screenshots.
- Bug fix PRs include a test that fails before the fix and passes after.
- Performance-sensitive code reports a measured runtime against `docs/CONTRACTS.md` §9.

## 7. Code standards (summary — full list in `CLAUDE.md` §5)

Python: type hints, small functions, no globals, no `print`, thresholds as arguments, no bare `except`, thread-safety stated in a comment. JavaScript: vanilla, `textContent` not `innerHTML`, every fetch has timeout + error UI, no CDN. Naming: `snake_case` Python, `camelCase` JS, `UPPER_SNAKE` constants. Comments explain **why**, not what.

## 8. Security and privacy

- Never commit: `.env`, `cameras.json`, `*.db`, `evidence/`, videos, `*.pt`, `venv/`. Check `git status` before each commit.
- No real individuals' footage in the repo or in screenshots. Demos use team members.
- No secrets in code or PR text. Do not expose the API beyond the local network.
- Treat everything the server returns as untrusted in the browser.

## 9. Conflict resolution

If a rebase conflicts in a file you do not own, **stop** — you probably edited the wrong file. Abort (`git rebase --abort`), ask Divyansh. If you conflict in your own file, resolve it carefully, re-run tests, and say so in the PR.

## 10. Communication

Standups twice on Day 2 (written is fine): *done / doing / blocked*. Blocked for 30 minutes → post logs in the team chat and tag Divyansh. Announce slips early; a late warning is a failure, a late task is not.

## 11. Working with your AI assistant

Give your AI the repo's `CLAUDE.md` at the start of every session. Starter message:

> I am `<name>`. Read CLAUDE.md, docs/PROJECT_OVERVIEW.md, docs/CONTRACTS.md, docs/ROADMAP.md, docs/tasks/`<NAME>`.md and CONTRIBUTING.md. Summarise my task and propose a plan. Do not write code until I say go.

You remain responsible for every line you submit. Before opening a PR: read your own diff, run the code, and be able to explain each function. AI output that was never executed does not count as done.

## 12. Definition of Done

1. Acceptance criteria in your task doc pass (evidence in the PR).
2. `pytest -q` and `ruff check .` are clean.
3. No files outside your ownership changed.
4. PR template completed; integration notes written.
5. `PROGRESS.md` line added.

## 13. Troubleshooting

| Symptom | Fix |
|---|---|
| `pip install` tries to compile NumPy/OpenCV | You are on Python 3.14. Use 3.13. |
| Phone camera works in browser but not in OpenCV | Use the `/video` URL, check same WiFi/hotspot, allow Python through Windows Firewall |
| `database is locked` | A second process holds `ibvap.db`; stop stray `uvicorn` processes |
| Track IDs mix between cameras | Each camera needs its own `YOLO` instance (see D4) |
| Rebase conflict in a file you don't own | Abort and ask Divyansh |
