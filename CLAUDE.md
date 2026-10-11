# Chores and Rewards: agent guide

Docs live in `docs/`:
- `spec.md`: what the app does.
- `ledger.md`: how each step was built, including the bugs found along the way.
- `decisions.md` (D-numbers), `acceptance.md` (AC-ids), `ws-api.md`, `ui-layout.md`, `database.md`.

When debugging an existing problem, check `ledger.md` and `decisions.md` first. The cause or the intended behaviour is often recorded there.

## Commands
- `script/setup`: create the Python 3.14 venv.
- `script/check`: lint + mypy, pytest + node tests, smoke, E2E. **Run before every push.**
- `script/develop`: dev HA on :8123. Then `.venv/bin/python script/dev_onboard.py && script/dev_seed.sh` (login dev/dev, PIN 1234).
- After UI changes, look at `e2e/artifacts/*.png`.

## Rules
- Runtime may use only the stdlib and HA. Use stable public HA APIs, and `import probatio as vol` for schemas.
- Layers (D47): `websocket_api` (thin) → `actions` (use cases, audited) / `views` (read models) → `db` (storage) + `logic` (rules). `store` is only HA glue. Keep `actions`, `views`, `db` and `logic` free of HA imports.
- DB: follow the conventions at the top of `db.py` (D45). Schema changes go into a new `MIGRATIONS` entry.
- Frontend: one plain JS file, no build step. Export pure helpers for tests.
- Every behaviour change needs a test that names its `AC-x.y`.
- A rule that exists on both server and panel shares a fixture in `tests/fixtures/`.
- A new WS command needs an entry in `docs/ws-api.md` (enforced by a test).
- Every state change must be audited with enough data to replay it (D46). A new audit action must be handled in `tests/replay.py`; `test_replay` enforces this.
- Never tag or publish a release without the user's explicit go-ahead.
- Commit: `git status` first (`git add -A` for new files), and one concise commit per step. Update `docs/ledger.md`. After a push, check CI by commit SHA.

## Non-goals (spec §10)
No gamification (leaderboards, badges, streaks, confetti, bonus counters). No device control, auto payments, shop, carry-over, photo proof, approval queue or notifications.

## Communication
Extremely concise. Ask only when blocked. Explain HA concepts in one "junior dev" line.
