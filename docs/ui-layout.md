# UI layout (agreed 2026-10-09)

The screen is a landscape kitchen tablet. There are 3 kids, 2 of whom mainly use it.

## Overview (default): today, all kids side by side
```
┌──────────────────────────────────────────────────────────────┐
│ Fredag 9. okt                                          🔒    │
├───────────────────┬───────────────────┬──────────────────────┤
│ ▸ Ada             │ ▸ Bo              │ ▸ Cato               │
│ ⏱ ████░░ 40/60 min│ ⏱ ██░░░░ 20/60 min│ ⏱ ░░░░░░  0/60 min   │
│ kr ██░░░ 30/80    │ kr █░░░░ 10/80    │ kr ░░░░░  0/50       │
│ MORGEN            │ MORGEN            │ MORGEN               │
│ [✓] Re opp sengen │ [ ] Re opp sengen │ [ ] Re opp sengen    │
│ ETTERMIDDAG       │ ETTERMIDDAG       │ ETTERMIDDAG          │
│ [✓] Dekke bordet  │ [ ] Oppvask       │ [ ] Mate katten      │
│ - - - - - - - - - │ - - - - - - - - - │ - - - - - - - - -    │
│ ekstra (muted)    │ ekstra (muted)    │ ekstra (muted)       │
│ ( ) Vaske vinduer │ ( ) Vaske vinduer │ ( ) Rydde garasjen   │
└───────────────────┴───────────────────┴──────────────────────┘
```
- One column per kid. The whole chore row is the tap target.
- Tapping a kid's name opens that kid's week.
- Header: `‹ Fredag 9. okt ›`, plus an "I dag" button when another day is shown.
  - You can move between days within the current Mon–Sun week.
  - Past days are read-only for kids. Future days are a read-only preview of the schedule.
  - Idle returns to today.

## Kid week (tap a name)
```
│ ← Ada · uke 41                                         🔒    │
│ ⏱ ████░░ 40/60 min (−10 tapt)     kr ██░░░ 30/80             │
│                  │ M │ T │ O │ T │ F │ L │ S │
│ Re opp sengen    │ ✓ │ ✓ │ ✗ │ ✓ │ ✓ │ · │ · │
│ ekstra: Vinduer  │   │   │ ✓ │   │ · │ · │ · │
```
- `✓` means done, `✗` missed or rejected, `–` excused, `·` open, and a blank cell means not scheduled.
- Today's column is highlighted, and its cells can be tapped, with a confirmation because the cells are small. Past days are read-only for kids.
- Back arrow or idle returns to the overview.

## Confirmations
- Unchecking a chore that was ticked more than 30 s ago asks "Are you sure?". This applies in both the overview and the week view.
- Ticking from the week grid always asks for confirmation.

## Parent mode (step 9)
- 🔒 opens a PIN pad (also works with a keyboard). Once unlocked (🔓), the same screens gain extras:
  - a ⋯ menu per chore with only the allowed actions (D19), plus "Juster saldo";
  - a ± button per kid for adjustments;
  - past cells in the week grid open the same ⋯ menu.
- Tabs: I dag · Utbetaling (• when a payout is due today and unpaid) · Administrer · Logg.
  - **Utbetaling:** week ‹ › (any past week), one card per currency with each kid's amount and "Merk utbetalt"/"Angre" (shows "+N etter utbetaling"), adjustments, and "Avslutt uka"/"Gjenåpne uka".
  - **Administrer:** kids, currencies, settings | chores. Edit forms open as dialogs; delete asks to confirm. Chore save shows the payout-day warning (AC-5.5).
  - **Logg:** latest 200 audit entries.
- It auto-locks after `pin_timeout_seconds` of no parent actions. An expired session reopens the PIN pad.

## Implementation notes (D48)
- Icons are `ha-icon` with mdi names (lock, chevrons, dots-vertical, alert, hand-wash); no emoji.
- All modals are native `<dialog>`s: Escape closes them, and Enter saves a form.
- On a phone, or when HA reports `narrow`, the overview and admin collapse to one column.

## Idle
- After `idle_seconds` (60) the screen returns to the overview.
- After `wake_seconds` (300) it shows the "Clean hands?" overlay; one tap continues.
