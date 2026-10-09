# Chores and Rewards: agent guide

The source of truth is `chores-app-spec.md`. Gap decisions are in `docs/decisions.md`, testable rules in `docs/acceptance.md`, and progress in `LEDGER.md`.

## Commands
- Setup: `script/setup` (Python 3.14 venv in `.venv`)
- Test: `script/test` (pytest, then `node --test tests/js/`; node runs via Docker if it isn't installed)
- Lint: `script/lint` to fix, `script/lint --check` for CI
- Real HA: `script/develop` starts HA 2026.10 in Docker at http://localhost:8123. Then `.venv/bin/python script/dev_onboard.py` onboards it (login dev/dev) and adds the integration (PIN 1234).

## Rules
- No third-party Python dependencies at runtime. Only stdlib and HA are allowed.
- `logic.py` has no HA imports, and all chore rules live there.
- Run every sqlite call through `hass.async_add_executor_job`, and serialize writes with the store lock.
- Frontend is one plain JS file (`frontend/panel.js`). No framework and no build step. Export pure helpers so `node --test` can test them.
- Use only stable public HA APIs. For schemas use `import probatio as vol`; HA 2026.10 no longer ships voluptuous.
- `script/lint --check` also runs mypy and must stay clean.
- Every behaviour change needs a test. Reference acceptance IDs (e.g. `AC-5.2`) in test names or docstrings.
- At the end of each step: lint and tests green, `LEDGER.md` updated, one concise commit.

## Non-goals (spec §10). Do not add:
- Gamification: leaderboards, badges, streaks, confetti, points counters on bonus chores.
- Make-up chores, device control, auto payments, rewards shop, carry-over, photo proof, approval queue, notifications.

## Communication
Be extremely concise. Ask only when blocked. Explain HA-specific concepts in a single "junior dev" line.
