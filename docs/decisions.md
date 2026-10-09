# Decisions

These fill gaps in the spec. A ✔ means the owner confirmed it.

| # | Topic | Decision |
|---|---|---|
| D1 ✔ | Week close | Auto-close at Monday 00:00. The parent can also close early. Unpaid payouts are flagged in history; nothing carries over. |
| D2 ✔ | Balance sensors | Yes: one sensor per kid × currency. |
| D3 ✔ | PIN setup | Set in the config flow and reset in the options flow (HA admin). Stored as a salted scrypt hash; 4–8 digits. |
| D4 ✔ | Weekly cap | Set per currency via `cap_mode`. `fixed` is a hard max (e.g. screen time), with an optional per-kid override of the currency default. `pot` means the max is the sum of all chore values scheduled for that kid this week (e.g. allowance). |
| D5 | Balance | `min(earned, cap) − lost (only if the currency can be lost) + adjustments`, clamped at ≥0 once on the total. Recomputed from rows, never stored. |
| D6 | Instances | One row per kid × chore × day, created eagerly at rollover, startup and catch-up. Idempotent through UNIQUE. Name and values are snapshotted onto the row. |
| D7 | States | `pending → done / missed / excused / rejected`. Excused earns 0 and loses 0. Rejected counts as missed. Pending rows for today re-sync when their chore is edited. |
| D8 | Edit rights | A kid can undo only today. A parent with the PIN can edit any day in the open week. |
| D9 | Bonus | At most once per scheduled day, never missed. |
| D10 | Anytime slot | A third group after afternoon. |
| D11 | Payout amount | The balance at the moment the payout is ticked. Anything earned later shows as "after payout". |
| D12 | Deletion | Soft delete only. The DB lives at `/config/chores_and_rewards.db`. |
| D13 | Timeouts | Idle returns to the daily view after 60 s. "Clean hands?" shows on wake after 5 min idle. The PIN locks after 5 min, sliding with activity. 5 wrong PINs → 60 s lockout. All configurable. |
| D14 | Permissions | The panel and all WS commands are `require_admin`. PIN actions also need a session token. |
| D15 ✔ | Repo URL | `malbrigt/ha-chores-and-rewards`, as in the spec. |
| D16 | Days | A day is a local date in HA's timezone. Catch-up processes each missed day in order. |
| D17 | Weekdays | An empty weekday set means every day. |
| D18 | Cap on total | The total is clamped to `0..cap` after adjustments, so screen time never exceeds its max. In pot mode the cap mostly sets the progress-bar scale. |
| D19 | Parent transitions | A parent can set: done or excused from any state; rejected only from done; pending only today; missed only for past expected chores. No future days. |
| D20 | Losses | Only expected chores cost; a rejected bonus earns 0 and loses 0. |
| D21 | Instance values | Stored as a JSON column on `instances`, not a separate `instance_values` table. Simpler, and it's always read as a whole. |
| D22 | Seed data | Currencies are seeded with Norwegian names: Skjermtid (min, Friday, can be lost, fixed cap) and Ukepenger (kr, Saturday, can't be lost, pot cap). Screen time has no default max until a parent sets one. |
| D23 | Backup | The pre-backup hook only checkpoints the WAL under the lock. Writes aren't blocked during a backup, so kids can still tap. |
| D24 | Removal | Removing the integration keeps `chores_and_rewards.db`, so no data is lost by accident. |
| D25 | Store module | `store.py` was added (not in the spec layout). It holds the HA ↔ db/logic glue and the rollover. |
| D26 | PIN sessions | Live in `sessions.py`, a pure class with an injectable clock. Tokens are in memory only, so an HA restart locks the panel. Failures are counted globally (one shared PIN, one screen). |
| D27 | WS field names | Never `id` or `type` in requests, since they clash with HA's message envelope. Use `kid_id`, `chore_id`, `currency_id`, `chore_type`. |
| D28 | WS registration | Commands are registered once in `async_setup` (HA can't unregister them). They answer `not_loaded` when no entry is loaded. |
| D29 | Kid taps | Not written to the audit log (only PIN and admin actions are, per §7). The row still records `status_by="kid"` and `status_at`. |
| D30 | Live updates | Events carry no data, just "something changed". The panel re-reads `get_state`. Simple, and the payload is small for one family. |
| D31 | Early close | Closing the week early freezes it: no kid or parent status changes, no adjustments, no new rows, and no midnight losses for the rest of that week. `parent/reopen_week` undoes it; days skipped while frozen stay as they were. |
| D32 | Late payout | Payouts can be ticked or unticked for any week, including closed ones, because parents forget. Adjustments and status changes only work in an open week. |
| D33 ✔ | Layout | Overview is 3 kid columns for today. Tapping a name opens that kid's week grid. Parent mode adds extras to the same screens. See `docs/ui-layout.md`. |
| D34 ✔ | Week grid taps | Kids can tick today's cells in the week grid, with a confirmation. Past days are parent-only. |
| D35 ✔ | Uncheck guard | Unchecking a chore ticked more than 30 s ago asks for confirmation. Needs `status_at` in the API. |
| D36 | Sidebar title | "Gjøremål" (Norwegian default). Custom panels can't translate their sidebar title. |
| D37 ✔ | Day switching | The overview can switch days within the current week. Past days are read-only for kids (parents: step 9). Future days show an unsaved preview built from the schedule. Idle returns to today. |
| D38 | UI verification | Rendering is tested with a happy-dom smoke test (`script/smoke` and CI) that drives the real element against a fake HA connection. Pixel-level look is still checked by a person on the tablet. |
| D39 | Forms vs live updates | Form inputs are uncontrolled. Typed values are copied back before any re-render, and background reloads don't re-render while a form is open. |
