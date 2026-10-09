# Ledger

Each step records its status, what was built, how it was solved, any deviations, tests, and the commit. The plan is in `CLAUDE.md` and `docs/`.

| Step | Title | Status |
|---|---|---|
| 1 | Scaffold and baseline | ✅ |
| 2 | Domain logic (`logic.py`) | ✅ |
| 3 | Persistence (`db.py`) | ✅ |
| 4 | Store and scheduler | ✅ |
| 5 | WS contract, PIN, admin CRUD | ⏳ |
| 6 | Kid and read API | ⏳ |
| 7 | Parent actions | ⏳ |
| 8 | Panel part 1 | ⏳ |
| 9 | Panel part 2 | ⏳ |
| 10 | Sensors and release | ⏳ |

---

## Step 1: Scaffold and baseline ✅
**Built**
- Integration skeleton: `manifest.json`, `const.py`, `__init__.py`, `config_flow.py`, nb/en translations, and a generated `brand/icon.png`.
- `hacs.json`, LICENSE, `pyproject.toml` (ruff and pytest).
- Scripts: `script/{setup,test,lint,develop}`. CI covers ruff, pytest, node, hassfest and HACS.
- `docker-compose.yml` with HA 2026.10.
- `CLAUDE.md`, `docs/decisions.md`, `docs/acceptance.md`.

**How**
- **Config flow:** asks for the PIN twice, validates 4–8 digits, and stores only a salted scrypt hash, computed in the executor because scrypt is deliberately slow. Single instance comes from `single_config_entry` in the manifest. The options flow resets the PIN by updating `entry.data`.
- **Test environment:** `pytest-homeassistant-custom-component==0.13.371` pins HA 2026.10.0. The tests also need `home-assistant-frontend==20260930.2`, because our manifest depends on `frontend` and `panel_custom`.
- **Toolchain:** this machine has no `uv` or `node`, so we use a plain `python3.14 -m venv`. JS tests fall back to `node:22-alpine` in Docker.

**Deviations**
- The PIN hash helpers live in `logic.py`, since they are pure and testable.
- The repo was renamed to `malbrigt/ha-chores-and-rewards` (D15).

**Tests:** 15 passing (PIN helpers, user flow, errors, single instance, options reset, setup/unload).

**Docker check:** `script/dev_onboard.py` onboards the Docker HA headlessly (user `dev`/`dev`) and adds the integration with PIN `1234`. Result: entry `loaded` in HA 2026.10.

**CI:** pushed to the public GitHub repo. lint-test, hassfest and HACS all pass. HACS needed a repo description and topics, set with `gh repo edit`.

**Commit:** (see git log)

---

## Step 2: Domain logic ✅
**Built:** `logic.py` with:
- Enums: ChoreType, Slot, Status, CapMode, Actor.
- Frozen dataclasses: Currency, Chore, Instance, Balance.
- `RuleError(code)`.
- Week maths: `week_start`, `week_days`, `days_to_finalize`, `weeks_to_close`.
- Scheduling: `is_scheduled`, `instances_for_day`, `snapshot`, `group_by_slot`.
- Transitions: `finalize`, `transition`.
- Balance: `week_pot`, `resolve_cap`, `compute_balance`.
- Payout: `payout_warnings`, `is_payout_day`.

**How:**
- **Dates:** all date maths uses plain local `date` objects, so DST can't cause trouble.
- **Catch-up:** returns the list of days still to process.
- **Balance:** recomputed from instances every time. Order: cap earnings, subtract losses, add adjustments, clamp to `0..cap`.
- **Pot cap:** snapshots for past days plus the current schedule for future days.
- **Rule errors:** each refusal raises a stable error code. The API and UI will map these codes to translated text.

**Decisions added:** D17–D20.

**Tests:** 51 logic and PIN tests, 100% branch coverage on `logic.py`. Total 56.

**Commit:** (see git log)

---

## Step 3: Persistence ✅
**Built:**
- `db.py`: schema v1 with 13 tables, CHECK and foreign-key constraints, and indexes.
- The `Database` class: `migrate`, `run(fn)`, `transaction`, `backup`, `checkpoint`.
- The `Repo` class: queries for meta, settings, kids, per-kid max, currencies, chores, weeks, instances, adjustments, payouts and audit.
- `logic.py` gained `Kid`, `sort` fields and `Instance.id`.

**How:**
- **Connections:** short-lived, one per `run`, so it's thread-safe in HA's executor. WAL is on, with `busy_timeout`.
- **Migrations:** each one is a SQL script wrapped in BEGIN/COMMIT, so a failure rolls back. The DB is copied to `*.bak-vN` via `sqlite3.backup()` before upgrading existing data.
- **Instances:** inserted with `INSERT OR IGNORE` on UNIQUE(kid, chore, day), so catch-up is idempotent.
- **Chore edits:** `resync_pending` and `delete_pending` touch only pending rows, so history keeps its snapshots.
- **Deletes:** soft delete via `deleted_at`.

**Decisions added:** D21 (JSON values column), D22 (seed data).

**Tests:** 80 total (24 new for db). Run with `-W error::ResourceWarning` clean. db.py at 99% branch coverage.

**Commit:** (see git log)

---

## Step 4: Store and scheduler ✅
**Built:**
- `store.py`: `ChoresStore` with `async_read`, `async_write` (locked), `async_notify` (bus event + dispatcher) and `async_rollover`. The rollover itself is a pure sync function.
- `__init__.py`: opens the DB at `/config/chores_and_rewards.db`, catches up on startup, and runs the midnight job via `async_track_time_change`. The store lives on `entry.runtime_data`.
- `backup.py`: checkpoints the WAL before a backup.
- `diagnostics.py`: counts, schema, open weeks, settings. The PIN hash is redacted.

**How:**
- **Rollover:** one transaction. For each unfinalized past day: insert instances (rows for days HA was off are created then), then `finalize`, so pending expected chores become missed.
- **Weeks:** weeks before the current one are auto-closed and audited as `system`. Then today's rows are created.
- **Idempotency:** `last_finalized` in meta plus INSERT OR IGNORE make it safe to rerun.
- **Fresh install:** `last_finalized` starts at yesterday.

**Tests:** 9 new, using the fake clock (`freezer`) and `async_fire_time_changed`:
- normal midnight
- a done chore survives midnight
- HA off Fri evening → Tue (week closed, Sat/Sun created and missed, bonus never missed)
- restart twice on the same day (idempotent)
- unload stops the job
- DST night
- backup hook
- diagnostics redaction

Total 89; coverage 99% branch.

**Docker:** reloaded in HA 2026.10. The DB was created at schema v1 and the entry is loaded. `dev_onboard.py` was fixed for HA that is already onboarded.

**Decisions added:** D23–D25.

**Commit:** (see git log)
