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
- 🔒 opens a PIN pad. Once unlocked (🔓), the same screens gain extras:
  - a ⋯ menu per chore: mark done, excused, reject, adjust balance;
  - editable week cells;
  - top tabs: I dag · Utbetaling (• when due today) · Administrer · Logg.
- It auto-locks after 5 min.

## Idle
- After `idle_seconds` (60) the screen returns to the overview.
- After `wake_seconds` (300) it shows the "Clean hands?" overlay; one tap continues.
