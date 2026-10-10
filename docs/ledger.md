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
| 9 | Panel part 2 | ✅ |
| 10 | Sensors and release | ✅ |
| 11 | Kids fix past days, audited taps, log review | ✅ |
| 12 | Database review and clean STRICT schema | ✅ |
| 13 | Replayable audit log | ✅ |
| 14 | Full code review: HA patterns, layering, panel | ✅ |

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
- **Commit:** 79ced0c

---

## Step 9: Panel part 2 (parent mode) ✅
**Built** (in `panel.js`):
- **PIN pad:** touch or keyboard. 🔒/🔓 in the header. Auto-lock after `pin_timeout_seconds`, and an expired session reopens the pad.
- **⋯ menu per chore:** offers only the allowed actions (`parentActions`, which mirrors D19) plus "Juster saldo". There is also a ± per kid. In the week grid, past cells open the same menu.
- **Tabs:**
  - Utbetaling: navigate weeks, pay or undo, after-payout amount, adjustments, close or reopen the week. A • dot shows when a payout is due today.
  - Administrer: kids, currencies, chores and settings forms, with delete confirmation and the payout warning.
  - Logg: the audit list.
- **Backend:** `get_week` rows now carry `ids` per day, so parents can edit past cells.

**How:**
- **Forms:** a generic dialog (text, number, bool, select and multi-chip fields). Inputs are uncontrolled: typed values are copied back before any re-render, and background reloads skip rendering while a form is open (D39).
- **Parent calls:** go through `_pws`, which adds the token and handles `invalid_token`.

**Verification:**
- **New `script/smoke`:** a happy-dom render test (6 scenarios) that drives the real element against a fake HA connection. It covers the overview, tap and confirm, the week view, PIN wrong/right, the ⋯ menu payload, payouts, and the admin form (typed values survive a background reload; the save payload is correct). It's also in CI, with happy-dom pinned to 20.14.4 and installed only in a temp dir.
- **Bug found by the smoke test:** timers kept running after the panel was removed from the page. The toast and reload timers are now cleared in `disconnectedCallback`.
- **Bug found in self-review:** the first version skipped all re-renders while a form was open, so closing a confirm dialog over a form, or an error toast, would not show. Fixed.

**Decisions added:** D38 (smoke-test strategy), D39 (forms vs live updates).

**Tests:** 130 Python, 16 JS unit and 6 JS smoke.

**Not verified by me:** pixel look and touch feel on the tablet.

**Commit:** f4898f7

---

## Review after step 9 ✅
Reviewed steps 5–9 (API, sessions, panel). Fixed:
- **Rule drift risk:** the parent status rules lived in both `logic.transition` (Python) and `parentActions` (JS). Both are now tested against one shared fixture, `tests/fixtures/parent_actions.json`, so the UI can't offer an action the server refuses.
- **Contract drift risk:** `tests/test_contracts.py` checks that `docs/ws-api.md` lists exactly the registered WS commands (24).
- **Bug:** a kid save with a max for an unknown currency raised a DB integrity error and returned `unknown_error`. The handler now maps `IntegrityError` to `not_found`, and the transaction rolls back. Test added.
- **Process:** dropped the separate "ledger hash" commits (7 of 30 commits were noise).

Checked, no action needed:
- XSS: all user text goes through `escapeHtml`.
- Thread safety: one connection per executor job, writes under the lock.
- Tokens: in memory only, sliding expiry.
- Scrypt runs in the executor.

User decisions (implemented in a follow-up commit, "feat: non-admin tablet users; escalating PIN lockout"):
- **D14 revised:** the user accepts the admin loophole, but wants the option to run the tablet as a normal user later. The panel and all commands now work for any logged-in HA user; parent and admin actions are gated by the PIN token.
- **D40:** escalating lockout of 60 s → 5 min → 30 min. A correct PIN or a PIN change in the options flow resets it, and the change also ends all parent sessions (entry update listener → `sessions.reset()`).

What we should have done from the start:
- Render smoke tests (happy-dom) from step 1, rather than shipping step 8 with no render check.
- Shared fixtures for any rule that exists on both sides.
- A docs ↔ code contract test as soon as the contract was written.

**Tests:** 145 Python, 17 JS unit and 6 smoke.

---

## Step 10: Sensors, E2E and release ✅
**Built:**
- `sensor.py`: balance sensors per kid × currency (D41).
- `e2e/run.py` (Playwright, Python) with `script/e2e` and `docker-compose.e2e.yml`, plus a CI `e2e` job that uploads screenshots.
- The dev scripts take `HA_URL` and `HA_CONFIG_DIR`, and `dev_onboard` also saves the full token set for browser login.
- README with install, first steps, tablet advice and dev commands, plus an overview screenshot.

**How:**
- **Sensors:** a `DataUpdateCoordinator` with `update_interval=None`, refreshed by the dispatcher signal. A listener adds new entities and removes stale ones.
- **E2E login:** puts HA's `hassTokens` and `selectedLanguage=nb` into localStorage. Two browser contexts act as two tablets.
- **Isolation:** the E2E HA runs as its own compose project (`-p chores-e2e`), so it never touches the dev HA or its data.

**Visual review:** I looked at the E2E screenshots myself for the first time and fixed four things:
- the lock emojis looked alike, so they're now mdi icons, orange when unlocked;
- the payout-due dot was hard to see, so it's now a badge;
- the "Til gode" header was misaligned;
- the admin list said "–" for every-day chores, so it now says "alle dager".

**Disk:** the Playwright Python package (134 MB) and its headless shell (196 MB) are about 330 MB, more than the ~150 MB I estimated. There's also an unrelated 530 MB June Playwright cache in `~/Library/Caches/ms-playwright`.

**Decisions added:** D41, D42.

**Tests:** 147 Python, 17 JS unit, 6 smoke and 1 E2E scenario (about 25 checks).

**Release:** v0.1.0 tagged and published on GitHub (https://github.com/malbrigt/ha-chores-and-rewards/releases/tag/v0.1.0). CI fully green on c46186a, including E2E.

---

## Step 11: Kids fix past days, audited taps, log review ✅ (user request)
**Why:** kids forget to tick, and having a parent fix it later becomes a chore. Possible foul play should be reviewable instead.

**Built:**
- **`logic.py`:** kids may tick or untick any day of the open week (`undo_status`, `is_late`). Excused and rejected stay parent-only.
- **Schema v2:** the first real migration. It adds `kid_id`, `day` and `late` to `audit_log`, with a backfill and the backup-before-upgrade from step 3.
- **API:**
  - `set_done` audits every tap.
  - `parent/set_status`, `adjust` and `payout` fill kid and day.
  - `parent/audit` gets filters.
  - Instances and week cells carry `late`.
- **Panel:**
  - kids can tap rows on past days and past week-grid cells, with a confirmation that names the day;
  - ⚠ on late ticks (parent mode only);
  - the log tab has filters (kid, group, late only, week) and column headers;
  - "Detaljer" on payout rows opens the pre-filtered log.

**How:**
- The tap rules exist on both server and panel, so they share `tests/fixtures/kid_actions.json` (per the CLAUDE.md rule).
- The user suggested a link from payouts to the filtered log instead of a separate receipt. I agreed: it reuses code, and the log already answers "which day, ticked when". The payout row already shows the total.

**Decisions:** D8 and D29 revised, D43 and D44 added.

**Tests:** 165 Python (migration upgrade, audit filters, kid past-day fixes and refusals, review filters), 19 JS unit, 8 smoke and E2E (now including Detaljer → log).

---

## Step 12: Database review and clean rebuild ✅ (user request)
**Why:** the user asked for a critical review (normal forms, datatypes, proven SQLite patterns), and to recreate the schema rather than migrate it, since there is no production data.

**Review result:** the schema was in 3NF overall; the `instances` and `audit_log` snapshots are intentional history. Fixed:
1. `instances."values"` was JSON, breaking 1NF with no FK. It's now the `instance_values` table, with FKs and `ON DELETE CASCADE`.
2. `instances.week` is derived from `day` (3NF). It's kept for the FK and index, and enforced by `CHECK (week = date(day,'-6 days','weekday 1'))`. A Monday check was added to `weeks.start`.
3. All 14 tables are `STRICT`. Booleans, dates and timestamps are validated by CHECKs.
4. `weekdays` had two encodings of "every day" (0 and 127). It's now 1..127, with every day stored as 127 and read back as empty.
5. Added missing CHECKs: snapshot type/slot, amounts, non-empty names, week status matching `closed_at`, and `status_at` set on any non-pending status.
6. FK child columns are indexed.
7. Case-insensitive unique active names, via partial indexes. Duplicates return the new `duplicate_name` WS error.
8. `audit_log`: `entity_id` is INTEGER, `kid_id` has an FK, JSON is validated, `ts` is indexed. Week rows now use `day` instead of `entity_id`.
9. The version moved from the meta table to `PRAGMA user_version`.
10. PRAGMAs: `synchronous=NORMAL`, and the duplicate busy timeout is gone. `optimize` runs after migrations and in the daily rollover.
    - **CI caught a bug:** my first version ran `PRAGMA optimize` on every connection close. Unlocked reads then raced for the write lock, and on CI's Linux runner that failed with `database is locked`; it passed locally. `optimize` now runs only under the write lock.

**Rebuild:**
- Migrations were squashed into one schema. The runner and its backup-before-upgrade stay for future changes.
- Pre-0.2 files are detected, backed up as `.legacy-<ts>.bak` and replaced. Verified live: dev HA restarted, the old file was set aside, and a fresh DB was created.

**Verified:** on the dev DB, `PRAGMA integrity_check` returns ok, `foreign_key_check` finds nothing, `user_version` is 1, WAL is on and all tables are STRICT. A test asserts the same.

**Decisions:** D21 revised, D45 added. Sources: sqlite.org docs on stricttables, datatype3, foreignkeys, pragma and partialindex.

**Tests:** 182 Python (constraint tests, legacy reset, normalized values, one-encoding weekdays, duplicate names over WS), JS, smoke and E2E unchanged and green.

---

## Step 13: Replayable audit log ✅ (user request)
**Goal:** the full usage of the integration can be replayed from the audit log.

**Gaps found** by listing every DB write. These writes were not audited:
- chore rows created at rollover, on startup and after edits;
- pending rows refreshed or deleted after chore or kid edits;
- automatic "missed" at midnight;
- new weeks;
- the rollover progress marker;
- the DB's creation and its seeded currencies;
- PIN usage.

Adjustments also lacked their own id and week.

**Built:**
- **`db.py`:** the write methods audit themselves (`week_open`, `instance_create`/`update`/`delete` with full snapshots via `instance_snapshot`). The schema seeds `db_created` plus `currency_save` rows.
- **`store.py`:** `auto_missed` and `rollover` (marker) entries, plus `async_audit` for events that change no stored state.
- **API:** admin-triggered refreshes are attributed to the parent's HA user. `adjust` is logged as entity "adjustment". PIN unlock, wrong PIN, lockout, lock and reset are logged.
- **`tests/replay.py`** (folds the log into state) and **`tests/test_replay.py`**: a two-week scenario with every change type, then `replay(log) == snapshot(db)`.

**Bug found by mutation-testing the replay test:** I removed one audit call on purpose, and the test still passed. Cause: SQLite reused the id of a deleted chore row, so two different rows shared one id in the history. `instances` now uses `AUTOINCREMENT` (D46), and a test asserts ids are never reused. After the fix, the same mutation fails the state comparison as it should.

**Decisions:** D46.

**Tests:** 184 Python. JS, smoke and E2E green.

---

## Step 14: Full code review before testing ✅ (user request)
Three parallel reviews: UI against HA frontend conventions, backend against HA integration guidelines and the quality scale, and backend duplication/design. User decisions: plain JS done right (no Lit, no internal `ha-*` beyond `ha-icon`/`ha-menu-button`), and the dispatcher signal only, with no bus events.

**A. HA patterns (`a89e9b5`)**
- **Backup:** holds the write lock from pre to post, like the recorder (D23 revised).
- **PIN change:** now the **reconfigure** flow (reload), replacing an options flow that also fired on an entry rename.
- **Setup errors:** translated `ConfigEntryError`/`ConfigEntryNotReady`.
- **Sensors:** one **device per kid**, `has_entity_name`; device renamed with the kid and removed when the kid is deleted; `PARALLEL_UPDATES`; debounced refresh.
- **Signals:** dispatcher only, so nothing reaches the recorder.
- **Other:** `sqlite_errorname` instead of message matching; translations get `data_description`.

**B. Layering and duplication (`79ffe0a`)**
- **New modules:**
  - `actions.py`: use cases, audited.
  - `views.py`: pure read models, with balances batched instead of N+1 queries.
  - `serialize.py`: one JSON shape per type, shared by the API, the audit log and replay.
  - `audit.py`: an `AuditAction` enum that drives the replay and contract tests.
- **Handlers:** WS handlers are thin and typed (`Handler` Protocol). `store.py` is only HA glue.
- **Repo:** `save_x`/`get_x` by id, a `_where` builder, `RETURNING` instead of re-reads, and the `WeekStatus` enum.
- **Dead code removed:** `group_by_slot`, `transition(open_week)`, session helpers used only by tests, `list_weeks`.
- **Tests:** helpers consolidated into `ws_helpers` (`midnight`, `kid_board`, one `TEST_PIN`).

**C. Panel rebuilt, plain JS done right (this commit)**
- **Bugs fixed:**
  - the reconnect `ready` listener was added again on every re-attach;
  - a failed subscription was never retried;
  - overlapping reloads could finish out of order (now a request counter);
  - the PIN keyboard listener was on `window`.
- **Rendering:** the persistent shell is built once (constructable stylesheet). `<main>` updates with focus restored, and an open select/input is never yanked.
- **Dialogs:** native `<dialog>` for confirm, sheet, form, PIN and "Clean hands?" (Escape, focus trap, inert background). Enter saves a form. "Clean hands?" never covers a form or the PIN pad.
- **Templating:** the escaping `html` template replaces hand-escaping.
- **Theming:** HA 2026 tokens (font, header height and border, safe area, radii). On-colour text uses `--text-primary-color`; a screenshot showed `--text-light-primary-color` is dark text.
- **Icons:** mdi via `ha-icon`.
- **Layout and accessibility:** ARIA labels and roles (checkbox, progressbar, status, cell labels), 44px targets, one-column layout when narrow.
- **Found while building:** a dialog was never stored, so each render created another. The smoke test caught it, and a per-test timeout now turns such hangs into failures.

**Tests:** 186 Python, 20 JS unit, 9 smoke (now also covering Escape, Enter-to-save and focus across a reload), and E2E. Screenshots reviewed.

**Spec:** updated to Draft 7 at the user's request: §6.2 and §8 (kids fix past days, D8/D34), §11 (any HA user, escalating lockout, Reconfigure), and §12 (sensors decided).

---

## Docs reorganised (user request)
- `chores-app-spec.md` moved to `docs/spec.md`, and `LEDGER.md` to `docs/ledger.md` (git history kept).
- New `docs/database.md`: tables, relations (a mermaid ER diagram), derived values and schema rules.
- README rewritten to be short: vibe-coded and use-at-your-own-risk notice, key concepts, how a week works, install, how it was built (spec → plan → ledger).
- `CLAUDE.md` points to the ledger and decisions when debugging.
