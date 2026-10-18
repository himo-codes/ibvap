## Summary
<!-- 2-3 sentences: what and why. -->

## Task
<!-- Task ID(s) from docs/tasks/<NAME>.md, e.g. K2 -->

## Type
- [ ] feat  - [ ] fix  - [ ] docs  - [ ] test  - [ ] refactor  - [ ] perf

## What changed
<!-- Bullet list of behaviour changes. -->

## Files touched
<!-- Paste `git diff --stat upstream/main`. Only files you own (CLAUDE.md section 4). -->

## How I tested
<!-- Real commands + real output. -->
```
pytest -q
ruff check .
```
<!-- Manual test steps and results. For UI: screenshots (normal, empty, error, offline-camera states). -->

## Acceptance criteria
<!-- Copy the task's acceptance list and tick each item with evidence. -->
- [ ] ...

## Performance impact
<!-- Measured runtime vs budget in docs/CONTRACTS.md section 9. "None" only if truly none. -->

## Contract impact
- [ ] No change to docs/CONTRACTS.md needed
- [ ] Needs a contract change (separate PR proposed): ...

## Integration notes for Divyansh
<!-- How to construct/call this, exact cameras.json values, where it runs in the pipeline. -->

## Proposed CHANGELOG entry
<!-- One line. -->

## Checklist
- [ ] Rebased on latest `upstream/main`
- [ ] Only my owned files changed
- [ ] No secrets, media, `.env`, `*.db`, `evidence/`, or model files committed
- [ ] Tests added/updated and passing; `ruff check .` clean
- [ ] I ran the code myself and can explain every function
- [ ] `PROGRESS.md` line added
