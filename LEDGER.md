# Ledger

Each step records its status, what was built, how it was solved, any deviations, tests, and the commit. The plan is in `CLAUDE.md` and `docs/`.

| Step | Title | Status |
|---|---|---|
| 1 | Scaffold and baseline | ✅ |
| 2 | Domain logic (`logic.py`) | ✅ |
| 3 | Persistence (`db.py`) | ✅ |
| 4 | Store and scheduler | ✅ |
| 5 | WS contract, PIN, admin CRUD | ✅ |
| 6 | Kid and read API | ✅ |
| 7 | Parent actions | ✅ |
| 8 | Panel part 1 | ✅ |
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

**Commit:** 9b939bf (+ 64bdc66, 370d10d, 0f3c8a3)

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

**Commit:** 813fdfd

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

**Commit:** fdaa523

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

**Commit:** 8def5d0

---

## Review after step 4 ✅
Reviewed everything built so far. Fixed:
- **Schema library:** HA 2026.10 uses `probatio`; `voluptuous` was only present as a side-dependency of other packages. The config flow now imports `probatio as vol`. This was a latent import-crash risk.
- **Type checking:** added mypy (`script/lint` and CI). It found 3 typing issues in `db.py`, now fixed.
- **Week for new rows:** `insert_instances` now derives each row's week from its day, so a caller can no longer pass the wrong week. Test added.
- **Midnight task:** the job runs as an entry-tracked task, so unload waits for a running rollover.
- **CI pinning:** pinned `hassfest` (commit SHA), `hacs/action@22.5.0`, `ruff` and `mypy`, so CI can't change underneath us.
- **Dev HA timezone:** set to Europe/Oslo to match the family.
- **Ledger:** commit hashes are filled in.

Carry-forward for steps 5–7 (not bugs yet):
- Kid or chore CRUD must call `ensure_today` and `delete_pending`/`resync_pending`, or today's view goes stale.
- Read endpoints should run a cheap "catch-up needed?" check as a safety net in case the midnight job is missed.
- WS schemas use `probatio`.

**Tests:** 90.

---

## Step 5: WS contract, PIN, admin CRUD ✅
**Built:**
- `docs/ws-api.md`: the full contract for steps 5–7.
- `sessions.py`: PIN sessions with sliding expiry and a 5-failure → 60 s lockout.
- `websocket_api.py`:
  - PIN: `pin/unlock`, `pin/status`, `pin/lock`.
  - Admin: `admin/list`, kid/currency/chore save and delete (soft), `admin/settings/save`.
- Store: `refresh_today_for_chore` and `refresh_today_for_kid`, so today's rows follow edits.
- `script/dev_ws.py`: sends WS commands to Docker HA from the shell.

**How:**
- **Command decorator:** one `command(schema, parent=)` decorator composes `websocket_command`, `require_admin` and `async_response`. It looks up the store, checks the token, and maps `RuleError` and `NotFound` to error codes.
- **Schemas:** written with `probatio`.
- **PIN check:** verifies the scrypt hash in the executor.
- **Admin writes:** each one runs in a single locked transaction that includes its audit row (before/after) and the refresh of today's rows.
- **Chore save:** returns the payout-day warnings (AC-5.5).

**Bugs caught by tests:**
- `id` and `type` in request fields collided with the WS envelope. Renamed (D27).
- HA's test access token expired when the fake clock jumped ahead. Fixed with the module-level `freeze_time` marker.

**Live check:** against Docker HA, wrong PIN → `wrong_pin`, correct PIN → token, kid saved, list returned.

**Decisions added:** D26–D28.

**Tests:** 109 (19 new). sessions, store and websocket_api at 100% branch coverage.

**Commit:** 4c947c5 (0795bdb was pushed by mistake without the new files; 4c947c5 completes it)

---

## Step 6: Kid and read API ✅
**Built:**
- WS commands: `subscribe`, `get_state`, `get_week`, `set_done`.
- In `store.py`, as read models:
  - `kid_balances`: pot from snapshots plus schedule, cap resolved per kid.
  - `board`: a typed `KidBoard` per kid.
  - `week_grid`.
- `async_ensure_current`: a safety-net rollover on reads and taps.

**How:**
- **Subscribe:** forwards the HA bus event `chores_and_rewards_updated` to the client via `connection.subscriptions`, which HA cleans up on disconnect.
- **Kid taps:** use `logic.transition(Actor.KID)` inside a locked transaction and are refused if the week is closed.
- **Sorting:** expected chores morning → afternoon → anytime, bonus chores separate.
- **Dates in requests:** parsed with HA's `cv.date`.

**Bugs caught by tests:**
- `probatio.Date()` returns a string, not a date. Switched to `cv.date`.
- The pushed event can come before the command's result. Tests accept either order, and the contract notes it.

**Live check:** against Docker HA, a chore save returned a payout warning (every-day chore paying screen time), and `get_state` returned the board.

**Decisions added:** D29, D30.

**Tests:** 118 (9 new). store and websocket_api at 100% branch coverage.

**Commit:** 71e071a

---

## Step 7: Parent actions ✅
**Built:** parent WS commands, all 🔒 and audited:
- `parent/set_status`
- `parent/adjust`
- `parent/payouts`
- `parent/payout`
- `parent/close_week`
- `parent/reopen_week`
- `parent/audit`

Supporting changes:
- `db.reopen_week`.
- The rollover and `ensure_today` skip weeks that were closed early.

**How:**
- **Status changes:** use `logic.transition(Actor.PARENT)`, so the D19 rules apply. Every change writes an audit row with before and after.
- **Payouts:** each kid × currency gets `amount_due` (the balance), `paid`, `after_payout` (earned since the tick), `payout_day` and `is_payout_day`. Ticking stores the current amount.
- **Adjustments:** need a non-blank note and a non-zero amount, and are refused in a closed week.

**Live check:** against Docker HA: adjust +20, tick payout → amount 20, payouts list shows it as paid.

**Decisions added:** D31 (early close freezes the week), D32 (late payouts allowed).

**Tests:** 126 (8 new). websocket_api and store at 100% branch coverage.

**Open:** the user wants a layout discussion before any UI code (step 8). Done: `docs/ui-layout.md`, D33–D35.

**Commit:** 5dbf963

---

## Step 8: Panel part 1 ✅
**Layout talk:** done before coding. Results are in `docs/ui-layout.md`:
- the overview has 3 kid columns;
- tapping a name opens a read-only week grid, where only today's cells can be tapped, with a confirmation;
- parent mode adds extras to the same screens (step 9);
- unchecking a chore ticked more than 30 s ago asks for confirmation.

**Built:**
- `frontend/panel.js`: one ES module, no build step. It has:
  - the overview: per-kid currency meters, chores grouped by slot, a muted bonus section, whole-row tap targets;
  - the kid week grid, with today's column highlighted and tappable with a confirmation;
  - the confirmation dialog;
  - the "Clean hands?" overlay after `wake_seconds` idle, and a return to the overview after `idle_seconds`;
  - an error toast with translated codes;
  - nb/en strings and HA theme variables.
- Panel registration (`panel_custom`, admin-only, `?v=version` cache-busting).
- The static path is registered once in `async_setup`.
- `status_at` was added to the instance API.
- `script/dev_seed.sh`: adds 3 kids and some chores to Docker HA.

**How:**
- **Data flow:** the panel subscribes to `subscribe`, re-reads `get_state` (debounced 150 ms) on each event and on reconnect, and updates the tapped row straight away.
- **Rendering:** one `innerHTML` render with `data-action` event delegation. User text is escaped.
- **Testability:** pure helpers are exported (i18n, progress, ISO week, uncheck rule, slot grouping, date labels), and the element is only defined when `customElements` exists, so Node can import the file.

**Bugs/lessons:**
- Node 22's `node --test` doesn't accept a directory, so we pass a glob (scripts, CI and CLAUDE.md updated).
- The dev access token expires after 30 min. Rerun `dev_onboard.py` to refresh it.

**Live check:** against Docker HA:
- The integration was removed, HA restarted, and the integration added again while HA was running. `panel.js` went from 404 to 200, with no errors, so registering after the web server has started works.
- `get_panels` shows "Gjøremål" (admin).
- The seeded board is correct.

**Not verified by me:** the visual rendering. No browser tool is available here. The user checks it in a browser or on the tablet.

**Decisions added:** D33–D36.

**Tests:** 129 Python (3 new) and 13 JS.

**Commit:** dd68a78

---

## Step 8b: Day switching on the overview ✅ (user request)
- **Panel:** ‹ › arrows in the header and an "I dag" button. The range is limited to the current Mon–Sun week (`dayNav`, `mondayOf` and `sameWeek` are pure and tested). Rows are read-only on other days. Idle and the week change snap back to today.
- **Backend:** `get_state(day=future)` returns an unsaved preview from the schedule plus `is_preview`. Nothing is written for future days.
- **Decision:** D37.
- **Tests:** 130 Python (+1) and 14 JS (+1).
- **Commit:** (pending)
