# Acceptance criteria

IDs follow the spec sections. Tests reference these IDs.

## §3 Currencies
- AC-3.1 WHEN a new week starts THEN each kid's balance is 0 in every currency.
- AC-3.2 WHEN an expected chore is missed AND its currency can be lost THEN the balance drops by the chore's value, never below 0.
- AC-3.3 WHEN an expected chore is missed AND its currency cannot be lost THEN the balance is unchanged.
- AC-3.4 WHEN a currency has decimals (0–2, fixed once created) THEN its amounts are shown and entered in the user's locale (0,50 € / 0.50 €) and stored exactly, without floats (D50).
- AC-3.4 WHEN a currency is inactive THEN it is hidden and earns nothing.

## §4 / D4 Caps
- AC-4.1 WHEN `cap_mode=fixed` THEN earnings stop at the kid's max (override, or the currency default).
- AC-4.2 WHEN `cap_mode=pot` THEN the max equals the sum of that kid's chore values scheduled this week.
- AC-4.3 WHEN no max is set (fixed mode, no default) THEN there is no cap.

## §5 Chores
- AC-5.1 WHEN a chore is scheduled for a weekday and assigned to a kid THEN that kid sees it that day, in its slot.
- AC-5.2 WHEN an expected chore is done THEN its value is earned.
- AC-5.3 WHEN midnight passes with an expected chore pending THEN it becomes missed.
- AC-5.4 WHEN a bonus chore is not done THEN nothing is lost and it is never marked missed.
- AC-5.5 WHEN a chore pays a currency on a day after that currency's payout day THEN saving shows a warning but succeeds.
- AC-5.6 WHEN a chore is edited THEN past instances keep their snapshot.

## §6 Daily flow
- AC-6.1 WHEN a kid taps a chore THEN it is done immediately (no approval) and progress updates live.
- AC-6.2 WHEN a kid unticks a chore today THEN it returns to pending. WHEN they tick or untick a past day in the open week THEN it is allowed (untick → missed), audited and flagged late (D8, D43). WHEN the week is closed THEN it is refused.
- AC-6.3 WHEN HA was off across midnight(s) THEN on startup each missed day is processed in order, exactly once.
- AC-6.6 WHEN a kid ticks an extra chore THEN it earns one currency: a can't-be-lost currency (payment) is always on offer, a can-be-lost one only while the kid has lost some this week. WHEN there are two options THEN the kid picks; WHEN one THEN no question (D49).
- AC-6.7 WHEN an extra chore refills a lost currency THEN the balance rises by at most what was lost, and never above the cap (D49).

## §7 PIN
- AC-7.1 WHEN the correct PIN is given THEN a session opens that expires after 5 min idle.
- AC-7.2 WHEN 5 wrong PINs are given THEN unlock is blocked for 60 s.
- AC-7.3 WHEN a parent action runs without a valid session THEN it is refused.
- AC-7.4 WHEN a parent rejects a completion THEN it counts as missed.
- AC-7.5 WHEN a parent marks done or excused THEN the state changes. Excused earns 0 and loses 0.
- AC-7.6 WHEN a parent adjusts a balance THEN a note is required and stored.
- AC-7.7 WHEN any parent action runs THEN an audit log row is written.

## §8 Screen
- AC-8.1 The daily view shows morning, afternoon and anytime groups, then muted bonus chores.
- AC-8.2 Progress bars show earned (and lost, for currencies that can be lost) against the weekly max.
- AC-8.3 The weekly view shows Mon–Sun columns with done/missed per chore. It returns to the daily view after idle.
- AC-8.4 WHEN the screen wakes from idle AND the reminder is enabled THEN "Clean hands?" shows first; one tap continues.
- AC-8.5 The UI language follows HA (nb or en), with en as fallback.

## §9 Settlement
- AC-9.1 WHEN it is a currency's payout day THEN the PIN view shows the amount per kid and lets the parent tick "paid" or "entered".
- AC-9.2 WHEN a week closes (manually or at Monday 00:00) THEN it is archived and a clean week starts.

## §12 Sensors
- AC-12.1 Each kid × active currency has a sensor whose state is the current balance, updated live.
