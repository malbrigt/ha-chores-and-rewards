# Chores and Rewards for Home Assistant: Spec

Draft 9, 11 Oct 2026. No open decisions. What it does, not how. Custom build (TaskMate, ChoreOps reviewed; neither fits).

## 1. Principles

1. Expected chores are a duty. Missing them can cost.
2. Bonus chores are optional. Skipping them never looks like failure.
3. Feedback only: progress bars, done/not done. No leaderboards, badges, streaks, confetti.
4. Expected chores are mostly family-care, done unasked.
5. Strict week-to-week, Monday to Sunday. Nothing carries over.
6. No more rigid than necessary: warn, don't block; leave edge cases to the parent.

## 2. Roles

- **Kids:** configurable number, names and settings. Pick own name on the kitchen touchscreen (no login); mark own chores done; see own progress and week history.
- **Parent:** same for any kid, plus PIN actions (section 7).

## 3. Currencies

Configurable set. Each has: name, unit, icon, active, **payout day**, **can be lost** (yes/no), and **decimals** (0–2, e.g. whole minutes, or cents for €/$; chosen once when the currency is created).

- Always earned, starting at 0 each week.
- Can be lost = yes: a missed expected chore deducts its own value. Balance never goes below 0.
- Can be lost = no: a missed chore just earns nothing.

Start with:

- **Screen time** (minutes): payout Friday; parent enters it into devices.
- **Allowance** (NOK): payout Saturday morning; parent pays.

## 4. Per-kid settings

Name, plus an optional **weekly maximum** per currency.

## 5. Chores (in a database, parent-managed)

Fields: name, icon, description; type (expected/bonus); assigned kids; weekdays; time of day (morning/afternoon/anytime); value per currency (zero or more); once a day (extras only); active.

**Expected**
- Shown each scheduled day in their slot. Mostly afternoon, a few morning.
- Done = earns its value. Not done by midnight = missed.

**Bonus**
- Allowance-focused; earns up to the weekly maximum.
- Earns **one** currency. A currency that can't be lost is payment. One that can be lost is offered only to **win back** what was lost this week, never more. If both are on offer, the kid picks ("1 €, or win back 10 min?"); otherwise the tap just ticks.
- Muted section below expected chores. No highlighting or counters.
- Always available; not locked behind expected chores.
- **Once a day** (optional per extra): the first kid to do it that day takes it; the others see "Taken by Ada". Off for chores like the trash, which every kid can do.

**Scheduling after payout**
- Scheduling a chore that pays a currency on a day after that currency's payout day shows a warning. It is not blocked.
- Anything earned after payout is not paid automatically; the parent handles it manually.

## 6. Daily flow

1. Screen shows morning chores, then afternoon chores, per kid.
2. Tap = done, counted immediately, no approval. Kids can tick or untick any day of the open week (forgotten ticks happen); late ticks are flagged for the parent.
3. Midnight: undone expected chores become missed.

## 7. Parent PIN

Unlocks, with every action logged:

- Reject a false completion (counts as missed).
- Mark done or excused for a kid.
- Adjust a balance, with a note.
- Manage kids, chores, currencies, settings.
- Mark a payout as done; close the week.

## 8. Screen

**Daily view (default), per kid**
- Today's expected chores by morning/afternoon.
- Progress bar per currency: earned (and lost, if the currency can be lost) against the weekly maximum.
- Bonus chores, muted, at the bottom.

**Weekly view (switchable)**
- Calendar-style: Monday to Sunday as columns, each chore marked done or missed per day.
- Today and earlier days of the open week can be ticked (with a confirmation). Returns to the daily view after idle.

**Clean-hands reminder**
- When the screen wakes from idle, it shows "Clean hands?" first; one tap continues.
- A reminder, not a check. Text and on/off are parent-configurable.

## 9. Weekly settlement

- No screen time on weekdays; earned time is used at the weekend.
- On each currency's payout day, a PIN view shows the amount per kid. Parent ticks "entered" or "paid".
- Closing the week archives it and starts a clean one.

## 10. Later, not version 1

- Device control, automatic payments, rewards shop, carry-over or savings, photo proof, approval queue, phone notifications.

Never: gamification.

## 11. Technical decisions

| Area | Decision |
|---|---|
| Name | Chores and Rewards; domain `chores_and_rewards`; repo `ha-chores-and-rewards` (public, MIT) |
| Form | Custom integration, runs 100% inside HA. Not an app, no separate backend. |
| Install | Manual upload to `/config/custom_components/`. Repo kept HACS-compliant. |
| Backend | Python, no third-party dependencies |
| Database | SQLite file in `/config`, Python's built-in driver, versioned schema with migrations |
| UI | Sidebar panel (like Calendar), HA theme colours, live updates over HA's WebSocket API |
| Frontend | One plain JavaScript file, no framework, no build step |
| Languages | Norwegian (default) and English |
| Kitchen screen | Any HA user. An admin user can reach HA settings from the sidebar; use a normal user to prevent that. Parent actions always need the PIN |
| PIN | One shared parent PIN, separate from HA login, checked on the server, auto-locks after 5 minutes, longer lockouts after repeated wrong PINs, reset by an HA admin (Reconfigure) |
| Time | HA's timezone; midnight rollover with catch-up if HA was off |
| HA versions | Current releases only |
| Update policy | Feature-conservative: stable public HA APIs only |

Layout:

```
custom_components/chores_and_rewards/
├── __init__.py        # setup, panel registration, midnight job
├── manifest.json
├── config_flow.py     # one-click setup
├── const.py
├── db.py              # SQLite access and migrations
├── logic.py           # chore rules, no HA imports, testable
├── websocket_api.py   # panel API, PIN sessions
├── translations/
├── brand/icon.png
└── frontend/panel.js
hacs.json
tests/
```

Baselines: jpawlowski/hacs.integration_blueprint (scaffold), HA forum sidebar-panel guide (Jan 2026), fireriver84/home-chores (PIN sessions, versioned frontend assets), HACS integration requirements.

## 12. Decided

Balance sensors: yes. One HA device per kid, one sensor per currency (e.g. `sensor.<kid>_screen_time`), usable in automations and other dashboards.

## 13. Research basis

- Routine chores correlate with self-competence, prosocial behaviour and executive function (not proven causal).
- Family-care chores, more than self-care, link to concern for others.
- Rewards undermine motivation mainly for tasks kids already enjoy; low risk for chores.
- Leaderboards and badges have reduced motivation in classroom studies; plain feedback helps.
