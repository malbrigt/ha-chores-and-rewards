# WebSocket API contract

The panel talks to the integration over HA's WebSocket connection (`hass.connection`).

## Conventions
- Every type is prefixed `chores_and_rewards/`; the prefix is left out below.
- Every command requires an HA **admin** user (D14).
- Commands marked 🔒 also need `token`, a parent session from `pin/unlock` (AC-7.3).
- Errors are `{success: false, error: {code, message}}`. The panel translates `code`.
- IDs are integers. Request fields never use `id` or `type`, because those are the WebSocket message id and command. Use `kid_id`, `chore_id`, `chore_type`, and so on. Dates are ISO `YYYY-MM-DD`. Weekdays run 0 = Monday … 6 = Sunday.
- Maps keyed by currency id (`values`, `max`) use string keys in JSON, e.g. `{"1": 30}`.

## Error codes

| Code | Meaning |
|---|---|
| `invalid_token` | Missing or expired parent session. Show the PIN pad. |
| `wrong_pin` | Wrong PIN. |
| `locked_out` | Too many wrong PINs. Wait, then try again (AC-7.2). |
| `not_found` | Unknown or deleted id. |
| `not_loaded` | The integration isn't set up. |
| `not_today`, `not_allowed`, `not_done`, `future_day`, `week_closed` | Status-change refusals from `logic.transition`. |
| `invalid_format` | The schema rejected the message (HA built-in). |

## PIN (step 5)

| Type | Request | Result |
|---|---|---|
| `pin/unlock` | `pin` | `{token, expires_in}` |
| `pin/status` | `token` | `{valid, expires_in}` |
| `pin/lock` | `token` | `{}` |

- A session expires after `pin_timeout_seconds` (default 300) of inactivity.
- Every 🔒 call extends it.
- 5 wrong PINs → `locked_out` for 60 s.

## Admin CRUD 🔒 (step 5)

| Type | Request | Result |
|---|---|---|
| `admin/list` | (nothing) | `{kids, currencies, chores, settings}`, including inactive items |
| `admin/kid/save` | `kid_id?`, `name`, `sort?`, `active?`, `max?: {cid: int\|null}` | `{id}` |
| `admin/kid/delete` | `kid_id` | `{}` |
| `admin/currency/save` | `currency_id?`, `name`, `unit`, `icon?`, `payout_weekday`, `can_be_lost`, `cap_mode` (`fixed`\|`pot`), `default_max?`, `active?`, `sort?` | `{id}` |
| `admin/currency/delete` | `currency_id` | `{}` |
| `admin/chore/save` | `chore_id?`, `name`, `icon?`, `description?`, `chore_type` (`expected`\|`bonus`), `slot`, `weekdays: [int]`, `kid_ids: [int]`, `values: {cid: int}`, `active?`, `sort?` | `{id, warnings: [cid]}` |
| `admin/chore/delete` | `chore_id` | `{}` |
| `admin/settings/save` | `settings: {key: value}` (known keys only) | `{settings}` |

How the saves behave:
- **Save in general:** a save without the id creates; with it, it updates. Deletes are soft (D12).
- **Chore save:**
  - `warnings` lists currencies paid after their payout day (AC-5.5). It's a warning only; the save succeeds.
  - Today's rows are refreshed. Pending rows are re-snapshotted, rows for chores or kids that are no longer scheduled are dropped, and new rows are added (D7).
- **Kid save or delete:** a deactivated or deleted kid's pending rows for today are dropped. A new or reactivated kid gets today's rows.
- **Audit:** every admin action writes an audit row with the before and after state (AC-7.7).

Settings keys:

| Key | Type |
|---|---|
| `clean_hands_enabled` | bool |
| `clean_hands_text` | str |
| `idle_seconds` | int, at least 10 |
| `wake_seconds` | int, at least 10 |
| `pin_timeout_seconds` | int, at least 30 |

## Kid and read API (step 6)

| Type | Request | Result |
|---|---|---|
| `get_state` | `day?` (default today) | `{today, day, week, week_status, kids, currencies, settings, board: {kid_id: {chores: [instance], bonus: [instance], balances: {cid: balance}}}}`. `chores` holds expected chores ordered morning → afternoon → anytime. Also runs the catch-up rollover if the midnight job was missed. |
| `get_week` | `kid_id`, `week?` (any date in that week) | `{week, week_status, days: [date], rows: [{chore_id, name, slot, type, cells: {date: status}}], balances}` |
| `set_done` | `instance_id`, `done: bool` | `{instance}`. Kid rules: today only, and the week must be open (AC-6.1, AC-6.2). |
| `subscribe` | (nothing) | Pushes `{event: "updated"}` after any change; the panel then re-reads `get_state`. The event can arrive before the result of the command that caused it. |

- `instance` = `{id, kid_id, chore_id, day, type, slot, name, icon, values, status}`
- `balance` = `{earned, lost, adjustments, cap, total}`

## Parent actions 🔒 (step 7)

| Type | Request | Result |
|---|---|---|
| `parent/set_status` | `instance_id`, `status` (`done`, `excused`, `rejected`, `missed`, `pending`) | `{instance}` |
| `parent/adjust` | `kid_id`, `currency_id`, `amount` (± int, not 0), `note` (required) | `{id}`. Applies to the current week, which must be open. |
| `parent/payouts` | `week?` | `{week, week_status, items: [{kid_id, currency_id, amount_due, paid: {amount, done_at}\|null, after_payout, payout_day, is_payout_day}], adjustments}` |
| `parent/payout` | `kid_id`, `currency_id`, `paid: bool`, `week?` | `{amount}`. Ticking stores the current balance as the amount (D11). Also works for closed weeks, so late payouts are possible. |
| `parent/close_week` | (nothing) | `{}`. Closes the current week early. The week freezes: no taps, no midnight losses, no new rows (D31). |
| `parent/reopen_week` | (nothing) | `{}`. Undoes an early close of the current week. Errors with `not_allowed` if the week isn't closed. |
| `parent/audit` | `limit?` (default 100) | `{entries}` |
