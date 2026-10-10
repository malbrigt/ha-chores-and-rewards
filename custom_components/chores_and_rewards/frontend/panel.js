// Chores and Rewards: sidebar panel for Home Assistant.
// One plain ES module, no framework, no build step. Layout: docs/ui-layout.md.
// Pure helpers are exported so `node --test` can test them; the custom element is only
// defined when running in a browser.

export const DOMAIN = "chores_and_rewards";
const P = `${DOMAIN}/`;
export const UNCHECK_GRACE_MS = 30_000; // D35
const SLOTS = ["morning", "afternoon", "anytime"];

// --- i18n -------------------------------------------------------------------------

export const STRINGS = {
  nb: {
    morning: "Morgen",
    afternoon: "Ettermiddag",
    anytime: "Når som helst",
    bonus: "Ekstra",
    expected: "Forventet",
    week: "Uke {n}",
    lost: "−{n} tapt",
    back: "Tilbake",
    today: "I dag",
    prev_day: "Forrige dag",
    next_day: "Neste dag",
    loading: "Laster …",
    no_kids: "Ingen barn er lagt til ennå.",
    no_chores: "Ingen gjøremål i dag.",
    clean_hands: "Rene hender?",
    tap_to_continue: "Trykk for å fortsette",
    confirm_uncheck: "Fjerne avkrysningen for «{name}»?",
    confirm_check: "Merke «{name}» som gjort?",
    confirm_check_day: "Merke «{name}» som gjort for {day}?",
    confirm_uncheck_day: "Fjerne avkrysningen for «{name}» ({day})?",
    late_hint: "Krysset av på en senere dag",
    details: "Detaljer",
    log_all_kids: "Alle barn",
    log_all_weeks: "Alle uker",
    log_late_only: "Kun sene",
    g_all: "Alt",
    g_review: "Gjennomgang",
    g_checks: "Avkrysninger",
    g_parent: "Foreldreendringer",
    g_money: "Saldo og utbetaling",
    g_admin: "Administrasjon",
    g_week: "Uke",
    a_check: "Krysset av",
    log_when: "Registrert",
    log_event: "Hendelse",
    log_what: "Hva",
    log_day: "Gjelder dag",
    a_uncheck: "Fjernet kryss",
    confirm_delete: "Slette «{name}»? Historikken beholdes.",
    confirm_close_week: "Avslutte uka nå? Resten av uka fryses.",
    yes: "Ja",
    cancel: "Avbryt",
    save: "Lagre",
    delete: "Slett",
    edit: "Rediger",
    new: "Ny",
    // parent
    lock: "Lås",
    unlock: "Foreldre",
    enter_pin: "Skriv inn PIN",
    tab_today: "I dag",
    tab_payouts: "Utbetaling",
    tab_admin: "Administrer",
    tab_log: "Logg",
    act_done: "Merk som gjort",
    act_excused: "Fritatt",
    act_rejected: "Avvis (teller som ikke gjort)",
    act_pending: "Nullstill",
    act_missed: "Merk som ikke gjort",
    adjust: "Juster saldo",
    amount: "Beløp (+/−)",
    note: "Notat",
    currency: "Valuta",
    payout_day: "Utbetaling {day}",
    payout_today: "i dag",
    amount_due: "Til gode",
    mark_paid: "Merk utbetalt",
    paid: "Utbetalt {amount}",
    undo: "Angre",
    after_payout: "+{amount} etter utbetaling",
    adjustments: "Justeringer",
    close_week: "Avslutt uka",
    reopen_week: "Gjenåpne uka",
    week_closed: "Uka er avsluttet.",
    kids: "Barn",
    chores: "Gjøremål",
    currencies: "Valutaer",
    settings: "Innstillinger",
    inactive: "inaktiv",
    f_name: "Navn",
    f_sort: "Rekkefølge",
    f_active: "Aktiv",
    f_max: "Ukemaks {name}",
    f_unit: "Enhet",
    f_icon: "Ikon (mdi:…)",
    f_payout_weekday: "Utbetalingsdag",
    f_can_be_lost: "Kan tapes",
    f_cap_mode: "Maks-type",
    cap_fixed: "Fast maks",
    cap_pot: "Sum av gjøremål",
    f_default_max: "Standard ukemaks",
    f_description: "Beskrivelse",
    f_chore_type: "Type",
    f_slot: "Tid på dagen",
    f_weekdays: "Dager (ingen = alle)",
    every_day: "alle dager",
    f_kids: "Barn",
    f_value: "Verdi {name}",
    f_clean_hands_enabled: "Vis «Rene hender?»",
    f_clean_hands_text: "Tekst (tom = standard)",
    f_idle_seconds: "Tilbake til i dag etter (sek)",
    f_wake_seconds: "«Rene hender?» etter (sek)",
    f_pin_timeout_seconds: "Lås foreldremodus etter (sek)",
    warn_after_payout: "Advarsel: betaler {names} etter utbetalingsdagen.",
    saved: "Lagret.",
    log_empty: "Ingen hendelser.",
    a_set_status: "Endret status",
    a_adjust: "Justerte saldo",
    a_payout: "Utbetalt",
    a_payout_undo: "Angret utbetaling",
    a_close_week: "Avsluttet uka",
    a_reopen_week: "Gjenåpnet uka",
    a_kid_save: "Lagret barn",
    a_kid_delete: "Slettet barn",
    a_chore_save: "Lagret gjøremål",
    a_chore_delete: "Slettet gjøremål",
    a_currency_save: "Lagret valuta",
    a_currency_delete: "Slettet valuta",
    a_settings_save: "Lagret innstillinger",
    error_not_today: "Det kan bare endres samme dag.",
    error_week_closed: "Uka er avsluttet.",
    error_not_allowed: "Det er ikke lov.",
    error_not_done: "Bare gjorte gjøremål kan avvises.",
    error_not_found: "Fant ikke det du lette etter.",
    error_wrong_pin: "Feil PIN.",
    error_locked_out: "For mange forsøk. Vent litt.",
    error_invalid_format: "Sjekk feltene.",
    error_generic: "Noe gikk galt. Prøv igjen.",
  },
  en: {
    morning: "Morning",
    afternoon: "Afternoon",
    anytime: "Anytime",
    bonus: "Extra",
    expected: "Expected",
    week: "Week {n}",
    lost: "−{n} lost",
    back: "Back",
    today: "Today",
    prev_day: "Previous day",
    next_day: "Next day",
    loading: "Loading …",
    no_kids: "No kids added yet.",
    no_chores: "No chores today.",
    clean_hands: "Clean hands?",
    tap_to_continue: "Tap to continue",
    confirm_uncheck: "Uncheck “{name}”?",
    confirm_check: "Mark “{name}” as done?",
    confirm_check_day: "Mark “{name}” as done for {day}?",
    confirm_uncheck_day: "Uncheck “{name}” ({day})?",
    late_hint: "Ticked on a later day",
    details: "Details",
    log_all_kids: "All kids",
    log_all_weeks: "All weeks",
    log_late_only: "Late only",
    g_all: "Everything",
    g_review: "Review",
    g_checks: "Ticks",
    g_parent: "Parent changes",
    g_money: "Balance and payouts",
    g_admin: "Admin",
    g_week: "Week",
    a_check: "Ticked",
    log_when: "Recorded",
    log_event: "Event",
    log_what: "What",
    log_day: "For day",
    a_uncheck: "Unticked",
    confirm_delete: "Delete “{name}”? History is kept.",
    confirm_close_week: "Close the week now? The rest of the week is frozen.",
    yes: "Yes",
    cancel: "Cancel",
    save: "Save",
    delete: "Delete",
    edit: "Edit",
    new: "New",
    lock: "Lock",
    unlock: "Parent",
    enter_pin: "Enter PIN",
    tab_today: "Today",
    tab_payouts: "Payouts",
    tab_admin: "Manage",
    tab_log: "Log",
    act_done: "Mark done",
    act_excused: "Excused",
    act_rejected: "Reject (counts as missed)",
    act_pending: "Reset",
    act_missed: "Mark not done",
    adjust: "Adjust balance",
    amount: "Amount (+/−)",
    note: "Note",
    currency: "Currency",
    payout_day: "Payout {day}",
    payout_today: "today",
    amount_due: "Due",
    mark_paid: "Mark paid",
    paid: "Paid {amount}",
    undo: "Undo",
    after_payout: "+{amount} after payout",
    adjustments: "Adjustments",
    close_week: "Close week",
    reopen_week: "Reopen week",
    week_closed: "The week is closed.",
    kids: "Kids",
    chores: "Chores",
    currencies: "Currencies",
    settings: "Settings",
    inactive: "inactive",
    f_name: "Name",
    f_sort: "Order",
    f_active: "Active",
    f_max: "Weekly max {name}",
    f_unit: "Unit",
    f_icon: "Icon (mdi:…)",
    f_payout_weekday: "Payout day",
    f_can_be_lost: "Can be lost",
    f_cap_mode: "Max type",
    cap_fixed: "Fixed max",
    cap_pot: "Sum of chores",
    f_default_max: "Default weekly max",
    f_description: "Description",
    f_chore_type: "Type",
    f_slot: "Time of day",
    f_weekdays: "Days (none = every day)",
    every_day: "every day",
    f_kids: "Kids",
    f_value: "Value {name}",
    f_clean_hands_enabled: "Show “Clean hands?”",
    f_clean_hands_text: "Text (empty = default)",
    f_idle_seconds: "Back to today after (s)",
    f_wake_seconds: "“Clean hands?” after (s)",
    f_pin_timeout_seconds: "Lock parent mode after (s)",
    warn_after_payout: "Warning: pays {names} after the payout day.",
    saved: "Saved.",
    log_empty: "No events.",
    a_set_status: "Changed status",
    a_adjust: "Adjusted balance",
    a_payout: "Paid out",
    a_payout_undo: "Undid payout",
    a_close_week: "Closed the week",
    a_reopen_week: "Reopened the week",
    a_kid_save: "Saved kid",
    a_kid_delete: "Deleted kid",
    a_chore_save: "Saved chore",
    a_chore_delete: "Deleted chore",
    a_currency_save: "Saved currency",
    a_currency_delete: "Deleted currency",
    a_settings_save: "Saved settings",
    error_not_today: "This can only be changed on the same day.",
    error_week_closed: "The week is closed.",
    error_not_allowed: "That is not allowed.",
    error_not_done: "Only done chores can be rejected.",
    error_not_found: "Not found.",
    error_wrong_pin: "Wrong PIN.",
    error_locked_out: "Too many attempts. Please wait.",
    error_invalid_format: "Please check the fields.",
    error_generic: "Something went wrong. Please try again.",
  },
};

/** Map HA's language to one we ship: Norwegian variants → nb, everything else → en. */
export function langOf(haLanguage) {
  const lang = String(haLanguage || "").toLowerCase();
  return ["nb", "nn", "no"].some((p) => lang === p || lang.startsWith(`${p}-`)) ? "nb" : "en";
}

/** Translate `key`, falling back to English, then to the key itself. */
export function t(lang, key, vars = {}) {
  const text = STRINGS[lang]?.[key] ?? STRINGS.en[key] ?? key;
  return text.replace(/\{(\w+)\}/g, (_, k) => String(vars[k] ?? ""));
}

export function errorText(lang, code) {
  const key = `error_${code}`;
  return key in STRINGS.en ? t(lang, key) : t(lang, "error_generic");
}

// --- pure view helpers --------------------------------------------------------

export function escapeHtml(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
  );
}

/** Progress bar data for one balance: percentage of the cap, or null if uncapped. */
export function progress(balance) {
  const { total = 0, cap = null, lost = 0 } = balance || {};
  const pct = cap ? Math.min(100, Math.round((total / cap) * 100)) : null;
  return { total, cap, lost, pct };
}

/** ISO 8601 week number for a YYYY-MM-DD date. */
export function isoWeek(dateStr) {
  const d = new Date(`${dateStr}T00:00:00Z`);
  const day = (d.getUTCDay() + 6) % 7; // Monday = 0
  d.setUTCDate(d.getUTCDate() - day + 3); // Thursday of this week
  const firstThursday = new Date(Date.UTC(d.getUTCFullYear(), 0, 4));
  const firstDay = (firstThursday.getUTCDay() + 6) % 7;
  firstThursday.setUTCDate(firstThursday.getUTCDate() - firstDay + 3);
  return 1 + Math.round((d - firstThursday) / (7 * 864e5));
}

/** True if unchecking this done chore should ask first (ticked > 30 s ago). */
export function needsUncheckConfirm(inst, nowMs, graceMs = UNCHECK_GRACE_MS) {
  if (inst?.status !== "done" || !inst.status_at) return false;
  return nowMs - Date.parse(inst.status_at) > graceMs;
}

/** Expected chores grouped by slot in display order, empty groups left out. */
export function groupBySlot(chores) {
  return SLOTS.map((slot) => ({ slot, items: chores.filter((c) => c.slot === slot) })).filter(
    (g) => g.items.length,
  );
}

const CELL = { done: "✓", missed: "✗", rejected: "✗", excused: "–", pending: "·" };

export function cellSymbol(status) {
  return CELL[status] ?? "";
}

/** Add days to a YYYY-MM-DD date. */
export function addDays(dateStr, n) {
  const d = new Date(`${dateStr}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

/** Monday of the week containing a YYYY-MM-DD date. */
export function mondayOf(dateStr) {
  return addDays(dateStr, -((new Date(`${dateStr}T12:00:00Z`).getUTCDay() + 6) % 7));
}

/** True if `day` is in the same Mon–Sun week as `today`. */
export function sameWeek(today, day) {
  return mondayOf(today) === mondayOf(day);
}

/** Day navigation on the overview, limited to the current Mon–Sun week (D37). */
export function dayNav(today, day) {
  const monday = mondayOf(today);
  const sunday = addDays(monday, 6);
  const prev = addDays(day, -1);
  const next = addDays(day, 1);
  return { prev: prev >= monday ? prev : null, next: next <= sunday ? next : null };
}

/** Status changes a parent may make (mirrors logic.transition, D19). */
export function parentActions(inst, today) {
  if (!inst?.id || inst.day > today) return [];
  const isToday = inst.day === today;
  const out = [];
  if (inst.status !== "done") out.push("done");
  if (inst.status !== "excused") out.push("excused");
  if (inst.status === "done") out.push("rejected");
  if (isToday && inst.status !== "pending") out.push("pending");
  if (!isToday && inst.type === "expected" && inst.status !== "missed") out.push("missed");
  return out;
}

/** What a kid's tap does (mirrors logic.transition for kids, D8): tick, untick or nothing. */
export function kidTap(inst, today) {
  if (!inst?.id || inst.day > today) return null;
  if (inst.status === "done") return "untick";
  if (inst.status === "pending" || inst.status === "missed") return "tick";
  return null; // excused / rejected: decided by a parent
}

/** Audit log filter groups (D44). `review` is what "Detaljer" on a payout opens. */
export const LOG_GROUPS = {
  all: null,
  review: ["check", "uncheck", "set_status", "adjust", "payout", "payout_undo"],
  checks: ["check", "uncheck"],
  parent: ["set_status"],
  money: ["adjust", "payout", "payout_undo"],
  admin: [
    "kid_save",
    "kid_delete",
    "chore_save",
    "chore_delete",
    "currency_save",
    "currency_delete",
    "settings_save",
  ],
  week: ["close_week", "reopen_week"],
};

/** "" → null, "12" → 12; anything non-numeric → null. */
export function parseOptionalInt(value) {
  const text = String(value ?? "").trim();
  if (!/^-?\d+$/.test(text)) return null;
  return Number(text);
}

const LOCALE = { nb: "nb-NO", en: "en-GB" };

/** "Fredag 9. okt." style header date. */
export function formatDay(dateStr, lang) {
  const d = new Date(`${dateStr}T12:00:00Z`);
  const text = new Intl.DateTimeFormat(LOCALE[lang], {
    weekday: "long",
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  }).format(d);
  return text.charAt(0).toUpperCase() + text.slice(1);
}

/** "man. 12.10." style short date for log rows and confirmations. */
export function shortDay(dateStr, lang) {
  const d = new Date(`${dateStr}T12:00:00Z`);
  return new Intl.DateTimeFormat(LOCALE[lang], {
    weekday: "short",
    day: "numeric",
    month: "numeric",
    timeZone: "UTC",
  }).format(d);
}

/** One-letter weekday for the week grid header. */
export function weekdayLetter(dateStr, lang) {
  const d = new Date(`${dateStr}T12:00:00Z`);
  return new Intl.DateTimeFormat(LOCALE[lang], { weekday: "narrow", timeZone: "UTC" })
    .format(d)
    .toUpperCase();
}

/** Full weekday name for 0 = Monday … 6 = Sunday. */
export function weekdayName(index, lang) {
  const monday = new Date(Date.UTC(2026, 9, 5, 12)); // a known Monday
  monday.setUTCDate(monday.getUTCDate() + index);
  return new Intl.DateTimeFormat(LOCALE[lang], { weekday: "long", timeZone: "UTC" }).format(monday);
}

/** Value with unit, e.g. "40/60 min" or "40 kr" when uncapped. */
export function amountLabel({ total, cap }, unit) {
  return cap ? `${total}/${cap} ${unit}` : `${total} ${unit}`;
}

/** Local "9.10. 14:05" style timestamp for the log. */
export function formatTimestamp(iso, lang) {
  return new Intl.DateTimeFormat(LOCALE[lang], {
    day: "numeric",
    month: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

// --- styles ---------------------------------------------------------------------

const STYLES = `
  :host {
    display: block;
    min-height: 100vh;
    background: var(--primary-background-color);
    color: var(--primary-text-color);
    font-family: var(--paper-font-body1_-_font-family, system-ui, sans-serif);
    -webkit-tap-highlight-color: transparent;
    user-select: none;
  }
  header {
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 56px;
    padding: 0 16px;
    background: var(--app-header-background-color, var(--primary-color));
    color: var(--app-header-text-color, var(--text-primary-color, #fff));
    font-size: 1.3rem;
  }
  header .title { flex: 1; display: flex; align-items: center; gap: 8px; }
  header .nav { font-size: 1.8rem; width: 44px; height: 44px; text-align: center; }
  header .nav[disabled] { opacity: 0.3; }
  header .pill {
    padding: 4px 12px;
    border: 1px solid currentColor;
    border-radius: 16px;
    font-size: 1rem;
  }
  header .pill.active { background: rgba(255, 255, 255, 0.25); }
  header .other-day { font-style: italic; }
  header .tabs { display: flex; gap: 6px; }
  header .lock { width: 44px; height: 44px; display: grid; place-items: center; border-radius: 50%; }
  header .lock ha-icon { --mdc-icon-size: 26px; }
  header .lock.open { background: var(--warning-color, #ffa600); color: #fff; }
  .dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--warning-color, #ffa600);
    margin-left: 4px;
    vertical-align: middle;
  }
  button {
    font: inherit;
    color: inherit;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
    text-align: left;
  }
  main { padding: 12px; }
  .columns { display: grid; gap: 12px; }
  .card, .kid {
    background: var(--card-background-color);
    border-radius: var(--ha-card-border-radius, 12px);
    padding: 12px 14px 16px;
    box-shadow: var(--ha-card-box-shadow, none);
    border: 1px solid var(--divider-color);
  }
  .card { margin-bottom: 12px; }
  .card h2 { margin: 4px 0 10px; font-size: 1.2rem; display: flex; align-items: center; gap: 8px; }
  .card h2 .grow { flex: 1; }
  .kid-head { display: flex; align-items: center; }
  .kid-name {
    flex: 1;
    font-size: 1.5rem;
    font-weight: 600;
    padding: 4px 0 8px;
  }
  .kid-name::after { content: " ›"; color: var(--secondary-text-color); }
  .small-btn {
    padding: 6px 12px;
    border-radius: 16px;
    border: 1px solid var(--divider-color);
    font-size: 0.95rem;
  }
  .primary-btn {
    padding: 8px 16px;
    border-radius: 10px;
    background: var(--primary-color);
    color: var(--text-primary-color, #fff);
  }
  .meter { margin: 6px 0; }
  .meter-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.95rem;
    color: var(--secondary-text-color);
  }
  .meter-label .amount { margin-left: auto; color: var(--primary-text-color); }
  .meter-label .lost { color: var(--error-color); font-size: 0.85rem; }
  ha-icon { --mdc-icon-size: 18px; }
  .bar {
    height: 10px;
    border-radius: 5px;
    background: var(--divider-color);
    overflow: hidden;
    margin-top: 3px;
  }
  .fill { height: 100%; background: var(--primary-color); border-radius: 5px; }
  .slot {
    margin: 14px 0 4px;
    font-size: 0.8rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--secondary-text-color);
  }
  .row { display: flex; align-items: center; border-bottom: 1px solid var(--divider-color); }
  .chore {
    display: flex;
    align-items: center;
    gap: 12px;
    flex: 1;
    min-height: 56px;
    font-size: 1.15rem;
  }
  .more { width: 44px; height: 44px; text-align: center; font-size: 1.4rem; color: var(--secondary-text-color); }
  .box {
    flex: none;
    display: grid;
    place-items: center;
    width: 34px;
    height: 34px;
    border-radius: 8px;
    border: 2px solid var(--secondary-text-color);
    font-size: 1.3rem;
  }
  .chore.done .box {
    background: var(--success-color, #43a047);
    border-color: var(--success-color, #43a047);
    color: #fff;
  }
  .chore.missed .box,
  .chore.rejected .box { border-color: var(--error-color); color: var(--error-color); }
  .chore.excused .box { color: var(--secondary-text-color); }
  .chore[disabled] { cursor: default; opacity: 0.75; }
  .bonus { margin-top: 18px; padding-top: 6px; border-top: 2px dashed var(--divider-color); opacity: 0.6; }
  .bonus .chore { min-height: 48px; font-size: 1rem; }
  .bonus .box { border-radius: 50%; width: 28px; height: 28px; }
  .empty { color: var(--secondary-text-color); padding: 12px 0; }
  .muted { color: var(--secondary-text-color); }
  .warn { color: var(--warning-color, #ffa600); }
  .week-meters { display: flex; flex-wrap: wrap; gap: 8px 32px; margin-bottom: 12px; }
  .week-meters .meter { flex: 1 1 260px; }
  table { width: 100%; border-collapse: collapse; }
  table.week {
    background: var(--card-background-color);
    border-radius: var(--ha-card-border-radius, 12px);
    overflow: hidden;
    font-size: 1.1rem;
  }
  table.week th, table.week td, table.list td, table.list th {
    border-bottom: 1px solid var(--divider-color);
    padding: 10px 6px;
    text-align: center;
  }
  table.week th:first-child, table.week td:first-child,
  table.list td, table.list th { text-align: left; }
  table.week th:first-child, table.week td:first-child { padding-left: 14px; }
  table.list td.num, table.list th.num { text-align: right; white-space: nowrap; }
  table.list td.actions { text-align: right; white-space: nowrap; }
  table.week .today { background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.12); }
  table.week tr.bonus-row { opacity: 0.6; }
  table.week td.cell { font-size: 1.4rem; width: 9%; }
  table.week td.cell.done { color: var(--success-color, #43a047); }
  table.week td.cell.missed, table.week td.cell.rejected { color: var(--error-color); }
  table.week td button { width: 100%; text-align: center; font-size: 1.4rem; min-height: 44px; }
  .overlay {
    position: fixed;
    inset: 0;
    display: grid;
    place-items: center;
    background: rgba(0, 0, 0, 0.55);
    z-index: 10;
  }
  .clean-hands {
    background: var(--primary-background-color);
    font-size: 3rem;
    text-align: center;
  }
  .clean-hands small { display: block; font-size: 1.2rem; color: var(--secondary-text-color); margin-top: 16px; }
  .dialog {
    background: var(--card-background-color);
    border-radius: 16px;
    padding: 24px;
    min-width: 320px;
    max-width: 90vw;
    max-height: 90vh;
    overflow: auto;
    font-size: 1.2rem;
  }
  .dialog h3 { margin: 0 0 16px; }
  .dialog .actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px; }
  .dialog .actions button, .sheet button {
    padding: 12px 24px;
    border-radius: 10px;
    font-size: 1.1rem;
    border: 1px solid var(--divider-color);
  }
  .dialog .actions .danger { color: var(--error-color); margin-right: auto; }
  .dialog .actions .primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border: none; }
  .sheet { display: flex; flex-direction: column; gap: 10px; min-width: 300px; }
  .field { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; user-select: text; }
  .field label { font-size: 0.9rem; color: var(--secondary-text-color); }
  .field input[type="text"], .field input[type="number"], .field select {
    font: inherit;
    font-size: 1.1rem;
    padding: 8px 10px;
    border-radius: 8px;
    border: 1px solid var(--divider-color);
    background: var(--primary-background-color);
    color: var(--primary-text-color);
  }
  .field.check { flex-direction: row; align-items: center; gap: 10px; }
  .field input[type="checkbox"] { width: 24px; height: 24px; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; }
  .chips label {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    border: 1px solid var(--divider-color);
    border-radius: 16px;
    color: var(--primary-text-color);
  }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px; }
  .pinpad { text-align: center; }
  .pin-dots { font-size: 2rem; letter-spacing: 0.4em; min-height: 2.6rem; margin-bottom: 12px; }
  .keys { display: grid; grid-template-columns: repeat(3, 80px); gap: 12px; justify-content: center; }
  .keys button {
    height: 64px;
    border-radius: 12px;
    border: 1px solid var(--divider-color);
    font-size: 1.6rem;
    text-align: center;
  }
  .toast {
    position: fixed;
    left: 50%;
    bottom: 24px;
    transform: translateX(-50%);
    background: var(--error-color);
    color: #fff;
    padding: 12px 20px;
    border-radius: 10px;
    font-size: 1.1rem;
    z-index: 20;
  }
  .toast.info { background: var(--primary-color); }
  .late { color: var(--warning-color, #ffa600); margin-left: 6px; font-size: 0.9em; }
  .filters { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .filters select {
    font: inherit;
    padding: 6px 10px;
    border-radius: 8px;
    border: 1px solid var(--divider-color);
    background: var(--primary-background-color);
    color: var(--primary-text-color);
  }
  .filters .check { display: flex; align-items: center; gap: 6px; }
  .filters .grow { flex: 1; }
`;

// --- the panel element ---------------------------------------------------------

const Base = globalThis.HTMLElement ?? class {};

export class ChoresPanel extends Base {
  constructor() {
    super();
    this._lang = "nb";
    this._state = null; // get_state result
    this._week = null; // get_week result for the open kid
    this._view = { name: "overview" };
    this._day = null; // overview day; null = follow today
    this._tab = "today"; // parent tabs: today | payouts | admin | log
    this._token = null; // parent PIN session
    this._tokenUntil = 0;
    this._pin = null; // PIN pad input while open, else null
    this._payouts = null;
    this._payoutWeek = null; // null = current week
    this._admin = null;
    this._log = null;
    this._logFilter = { kidId: null, group: "all", late: false, week: null };
    this._dialog = null; // {text, onYes}
    this._sheet = null; // {title, items: [{label, run}]}
    this._form = null; // {title, fields, values, onSave, onDelete}
    this._toast = null;
    this._cleanHands = false;
    this._lastActivity = Date.now();
    this._onActivity = () => {
      this._lastActivity = Date.now();
    };
    this._onKey = (ev) => this._pinKey(ev);
  }

  // HA sets these properties on the panel element.
  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    const lang = langOf(hass.language);
    if (lang !== this._lang) {
      this._lang = lang;
      this._render();
    }
    this._syncMenuButton();
    if (first && this.isConnected) this._connect();
  }

  get hass() {
    return this._hass;
  }

  set narrow(narrow) {
    this._narrow = narrow;
    this._syncMenuButton();
  }

  set panel(panel) {
    this._panelConfig = panel;
  }

  set route(route) {
    this._route = route;
  }

  connectedCallback() {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
      this.shadowRoot.addEventListener("change", (ev) => this._onChange(ev));
    }
    for (const type of ["pointerdown", "keydown"]) {
      window.addEventListener(type, this._onActivity, { capture: true });
    }
    window.addEventListener("keydown", this._onKey);
    this._idleTimer = setInterval(() => this._checkIdle(), 2000);
    this._render();
    if (this._hass) this._connect();
  }

  disconnectedCallback() {
    for (const type of ["pointerdown", "keydown"]) {
      window.removeEventListener(type, this._onActivity, { capture: true });
    }
    window.removeEventListener("keydown", this._onKey);
    clearInterval(this._idleTimer);
    clearTimeout(this._toastTimer);
    clearTimeout(this._reloadTimer);
    this._unsubscribe?.then((unsub) => unsub()).catch(() => {});
    this._unsubscribe = null;
  }

  get _parent() {
    return Boolean(this._token);
  }

  // --- data ---------------------------------------------------------------------

  _ws(type, data = {}) {
    return this._hass.connection.sendMessagePromise({ type: P + type, ...data });
  }

  /** A parent (PIN) command. Expired sessions lock the panel and show the PIN pad. */
  async _pws(type, data = {}) {
    try {
      const result = await this._ws(type, { ...data, token: this._token });
      this._tokenUntil = Date.now() + this._pinTimeoutMs();
      return result;
    } catch (err) {
      if (err?.code === "invalid_token") {
        this._lockLocal();
        this._pin = "";
      }
      throw err;
    }
  }

  _pinTimeoutMs() {
    return (this._state?.settings?.pin_timeout_seconds ?? 300) * 1000;
  }

  async _connect() {
    if (this._unsubscribe || !this._hass) return;
    // HA's websocket library re-subscribes by itself after a reconnect.
    this._unsubscribe = this._hass.connection.subscribeMessage(() => this._scheduleReload(), {
      type: `${P}subscribe`,
    });
    this._hass.connection.addEventListener("ready", () => this._scheduleReload());
    try {
      await this._unsubscribe;
    } catch (err) {
      this._showError(err);
    }
    await this._reload();
  }

  _scheduleReload() {
    clearTimeout(this._reloadTimer);
    this._reloadTimer = setTimeout(() => this._reload(), 150);
  }

  async _reload() {
    try {
      this._state = await this._ws("get_state", this._day ? { day: this._day } : {});
      // A new week (midnight Sunday) or a stale day snaps back to today.
      if (this._day && !sameWeek(this._state.today, this._day)) {
        this._day = null;
        this._state = await this._ws("get_state");
      }
      if (this._view.name === "week") {
        this._week = await this._ws("get_week", { kid_id: this._view.kidId });
      }
      if (this._parent) await this._reloadParent();
    } catch (err) {
      this._showError(err);
    }
    this._render({ background: true });
  }

  async _reloadParent() {
    const week = this._payoutWeek ? { week: this._payoutWeek } : {};
    this._payouts = await this._pws("parent/payouts", week);
    if (this._tab === "admin") this._admin = await this._pws("admin/list");
    if (this._tab === "log") {
      const f = this._logFilter;
      const query = { limit: 200, late_only: f.late };
      if (LOG_GROUPS[f.group]) query.actions = LOG_GROUPS[f.group];
      if (f.kidId) query.kid_id = f.kidId;
      if (f.week) query.week = f.week;
      this._log = (await this._pws("parent/audit", query)).entries;
    }
  }

  async _goDay(day) {
    this._day = day && day !== this._state?.today ? day : null;
    await this._reload();
  }

  async _openWeek(kidId) {
    this._view = { name: "week", kidId };
    this._week = null;
    this._render();
    await this._reload();
  }

  _findInstance(id) {
    for (const kid of Object.values(this._state?.board ?? {})) {
      const found = [...kid.chores, ...kid.bonus].find((i) => i.id === id);
      if (found) return found;
    }
    return null;
  }

  async _setDone(inst, done) {
    try {
      const { instance } = await this._ws("set_done", { instance_id: inst.id, done });
      Object.assign(inst, instance); // instant feedback; the update event reloads the rest
      this._render();
    } catch (err) {
      this._showError(err);
    }
  }

  async _run(fn, { reload = true, info = null } = {}) {
    try {
      await fn();
      if (info) this._showInfo(info);
      if (reload) await this._reload();
    } catch (err) {
      this._showError(err);
    }
  }

  // --- parent session -----------------------------------------------------------

  async _submitPin() {
    const pin = this._pin;
    this._pin = "";
    try {
      const { token, expires_in } = await this._ws("pin/unlock", { pin });
      this._token = token;
      this._tokenUntil = Date.now() + expires_in * 1000;
      this._pin = null;
      await this._reload();
    } catch (err) {
      this._showError(err);
    }
  }

  _lockLocal() {
    this._token = null;
    this._tab = "today";
    this._payouts = this._admin = this._log = null;
    this._payoutWeek = null;
    this._form = this._sheet = null;
  }

  async _lock() {
    const token = this._token;
    this._lockLocal();
    this._render();
    if (token) await this._ws("pin/lock", { token }).catch(() => {});
  }

  _pinKey(ev) {
    if (this._pin === null) return;
    if (/^\d$/.test(ev.key)) this._pinDigit(ev.key);
    else if (ev.key === "Backspace") this._pin = this._pin.slice(0, -1);
    else if (ev.key === "Enter") this._submitPin();
    else if (ev.key === "Escape") this._pin = null;
    else return;
    this._render();
  }

  _pinDigit(digit) {
    if (this._pin.length < 8) this._pin += digit;
  }

  // --- interaction ----------------------------------------------------------------

  _onClick(ev) {
    const el = ev.composedPath().find((n) => n.dataset?.action);
    if (!el) return;
    const { action } = el.dataset;
    const id = Number(el.dataset.id);
    const handlers = {
      "clean-hands": () => {
        this._cleanHands = false;
      },
      kid: () => this._openWeek(Number(el.dataset.kid)),
      day: () => this._goDay(el.dataset.day || null),
      back: () => {
        this._view = { name: "overview" };
        this._week = null;
      },
      toggle: () => this._toggle(id, el.dataset.confirm === "1", el.dataset.day),
      details: () => {
        this._logFilter = {
          kidId: Number(el.dataset.kid),
          group: "review",
          late: false,
          week: this._payouts?.week ?? null,
        };
        this._openTab("log");
      },
      "log-week": () => {
        this._logFilter.week = el.dataset.week || null;
        this._reload();
      },
      more: () => this._openSheet(id, el.dataset.day),
      "dialog-yes": () => {
        const { onYes } = this._dialog;
        this._dialog = null;
        onYes();
      },
      "dialog-cancel": () => {
        this._dialog = null;
      },
      "sheet-item": () => {
        const item = this._sheet.items[Number(el.dataset.index)];
        this._sheet = null;
        item.run();
      },
      "sheet-close": () => {
        this._sheet = null;
      },
      // parent
      "lock-toggle": () => (this._parent ? this._lock() : (this._pin = "")),
      "pin-digit": () => this._pinDigit(el.dataset.digit),
      "pin-back": () => {
        this._pin = this._pin.slice(0, -1);
      },
      "pin-ok": () => this._submitPin(),
      "pin-cancel": () => {
        this._pin = null;
      },
      tab: () => this._openTab(el.dataset.tab),
      adjust: () => this._openAdjust(Number(el.dataset.kid)),
      "payout-week": () => {
        this._payoutWeek = el.dataset.week || null;
        this._reload();
      },
      pay: () =>
        this._run(() =>
          this._pws("parent/payout", {
            kid_id: Number(el.dataset.kid),
            currency_id: Number(el.dataset.currency),
            paid: el.dataset.paid === "1",
            ...(this._payoutWeek ? { week: this._payoutWeek } : {}),
          }),
        ),
      "close-week": () => {
        this._dialog = {
          text: t(this._lang, "confirm_close_week"),
          onYes: () => this._run(() => this._pws("parent/close_week")),
        };
      },
      "reopen-week": () => this._run(() => this._pws("parent/reopen_week")),
      "edit-kid": () => this._openKidForm(el.dataset.id ? id : null),
      "edit-chore": () => this._openChoreForm(el.dataset.id ? id : null),
      "edit-currency": () => this._openCurrencyForm(el.dataset.id ? id : null),
      "edit-settings": () => this._openSettingsForm(),
      "form-save": () => this._saveForm(),
      "form-delete": () => this._deleteForm(),
      "form-cancel": () => {
        this._form = null;
      },
    };
    const result = handlers[action]?.();
    if (result instanceof Promise) return;
    this._render();
  }

  _onChange(ev) {
    const el = ev.composedPath().find((n) => n.dataset?.filter);
    if (!el) return;
    const f = this._logFilter;
    if (el.dataset.filter === "kid") f.kidId = el.value ? Number(el.value) : null;
    if (el.dataset.filter === "group") f.group = el.value;
    if (el.dataset.filter === "late") f.late = el.checked;
    this._reload();
  }

  _toggle(id, alwaysConfirm, day) {
    const inst = this._findInstance(id) ?? this._weekInstance(id, day);
    if (!inst || !kidTap(inst, this._state.today)) return;
    const done = inst.status !== "done";
    if (inst.day !== this._state.today) {
      // A past day: always confirm, and say which day (D8).
      const key = done ? "confirm_check_day" : "confirm_uncheck_day";
      const vars = { name: inst.name, day: shortDay(inst.day, this._lang) };
      this._dialog = { text: t(this._lang, key, vars), onYes: () => this._setDone(inst, done) };
      return;
    }
    if (done && !alwaysConfirm) {
      this._setDone(inst, true);
      return;
    }
    if (!done && !alwaysConfirm && !needsUncheckConfirm(inst, Date.now())) {
      this._setDone(inst, false);
      return;
    }
    const key = done ? "confirm_check" : "confirm_uncheck";
    this._dialog = { text: t(this._lang, key, { name: inst.name }), onYes: () => this._setDone(inst, done) };
  }

  _openTab(tab) {
    this._tab = tab;
    this._view = { name: "overview" };
    this._form = this._sheet = null;
    this._render();
    this._reload();
  }

  /** Parent ⋯ menu for one chore instance (status actions allowed by D19). */
  _openSheet(id, day) {
    const L = this._lang;
    const inst = this._findInstance(id) ?? this._weekInstance(id, day);
    if (!inst) return;
    const items = parentActions(inst, this._state.today).map((status) => ({
      label: t(L, `act_${status}`),
      run: () =>
        this._run(() => this._pws("parent/set_status", { instance_id: inst.id, status })),
    }));
    items.push({ label: t(L, "adjust"), run: () => this._openAdjust(inst.kid_id) });
    this._sheet = { title: inst.name, items };
  }

  /** Build a minimal instance from the week grid (past days aren't in today's board). */
  _weekInstance(id, day) {
    const row = this._week?.rows.find((r) => r.ids?.[day] === id);
    if (!row) return null;
    return { id, day, type: row.type, status: row.cells[day], name: row.name, kid_id: this._view.kidId };
  }

  _checkIdle() {
    const settings = this._state?.settings;
    if (!settings) return;
    const now = Date.now();
    const idle = now - this._lastActivity;
    let changed = false;
    if (this._parent && now > this._tokenUntil) {
      this._lock();
      changed = true;
    }
    const away = this._view.name !== "overview" || this._day;
    if (away && !this._form && idle > settings.idle_seconds * 1000) {
      this._view = { name: "overview" };
      this._day = null;
      this._dialog = this._sheet = null;
      this._scheduleReload();
      changed = true;
    }
    if (settings.clean_hands_enabled && !this._cleanHands && idle > settings.wake_seconds * 1000) {
      this._cleanHands = true;
      changed = true;
    }
    if (changed) this._render();
  }

  _showError(err) {
    this._setToast(errorText(this._lang, err?.code), "error");
  }

  _showInfo(text) {
    this._setToast(text, "info");
  }

  _setToast(text, kind) {
    this._toast = { text, kind };
    this._render();
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => {
      this._toast = null;
      this._render();
    }, 4000);
  }

  // --- forms ----------------------------------------------------------------------
  // Inputs are uncontrolled: values are read from the DOM. Before any re-render the typed
  // values are copied back into the form, and background data reloads skip rendering
  // while a form is open, so live updates never steal focus mid-typing.

  _openForm(form) {
    this._form = form;
    this._render();
  }

  _readForm() {
    const root = this.shadowRoot.querySelector("form.form");
    const values = {};
    for (const f of this._form.fields) {
      if (f.type === "bool") values[f.key] = root.querySelector(`[name="${f.key}"]`).checked;
      else if (f.type === "multi") {
        values[f.key] = [...root.querySelectorAll(`[name="${f.key}"]:checked`)].map((i) =>
          Number(i.value),
        );
      } else if (f.type === "number") {
        values[f.key] = parseOptionalInt(root.querySelector(`[name="${f.key}"]`).value);
      } else values[f.key] = root.querySelector(`[name="${f.key}"]`).value;
    }
    return values;
  }

  async _saveForm() {
    const values = this._readForm();
    try {
      await this._form.onSave(values);
      this._form = null;
      await this._reload();
    } catch (err) {
      this._showError(err);
    }
  }

  _deleteForm() {
    const { onDelete, name } = this._form;
    this._dialog = {
      text: t(this._lang, "confirm_delete", { name }),
      onYes: async () => {
        this._form = null;
        await this._run(onDelete);
      },
    };
    this._render();
  }

  _openAdjust(kidId) {
    const L = this._lang;
    const kid = this._state.kids.find((k) => k.id === kidId);
    this._openForm({
      title: `${t(L, "adjust")}: ${kid?.name ?? ""}`,
      fields: [
        {
          key: "currency_id",
          type: "select",
          label: t(L, "currency"),
          options: this._state.currencies.map((c) => [c.id, c.name]),
        },
        { key: "amount", type: "number", label: t(L, "amount") },
        { key: "note", type: "text", label: t(L, "note") },
      ],
      values: {},
      onSave: (v) =>
        this._pws("parent/adjust", {
          kid_id: kidId,
          currency_id: Number(v.currency_id),
          amount: v.amount ?? 0,
          note: v.note,
        }),
    });
  }

  _openKidForm(kidId) {
    const L = this._lang;
    const kid = this._admin.kids.find((k) => k.id === kidId) ?? { active: true, sort: 0, max: {} };
    const currencies = this._admin.currencies.filter((c) => c.active);
    this._openForm({
      title: kidId ? kid.name : `${t(L, "new")}: ${t(L, "kids")}`,
      name: kid.name,
      fields: [
        { key: "name", type: "text", label: t(L, "f_name") },
        ...currencies.map((c) => ({
          key: `max_${c.id}`,
          type: "number",
          label: t(L, "f_max", { name: `${c.name} (${c.unit})` }),
        })),
        { key: "sort", type: "number", label: t(L, "f_sort") },
        { key: "active", type: "bool", label: t(L, "f_active") },
      ],
      values: {
        ...kid,
        ...Object.fromEntries(currencies.map((c) => [`max_${c.id}`, kid.max?.[String(c.id)]])),
      },
      onSave: (v) =>
        this._pws("admin/kid/save", {
          ...(kidId ? { kid_id: kidId } : {}),
          name: v.name,
          sort: v.sort ?? 0,
          active: v.active,
          max: Object.fromEntries(currencies.map((c) => [String(c.id), v[`max_${c.id}`]])),
        }),
      onDelete: kidId ? () => this._pws("admin/kid/delete", { kid_id: kidId }) : null,
    });
  }

  _openChoreForm(choreId) {
    const L = this._lang;
    const chore = this._admin.chores.find((c) => c.id === choreId) ?? {
      chore_type: "expected",
      slot: "afternoon",
      weekdays: [],
      kid_ids: [],
      values: {},
      active: true,
      sort: 0,
      icon: "",
      description: "",
    };
    const currencies = this._admin.currencies.filter((c) => c.active);
    this._openForm({
      title: choreId ? chore.name : `${t(L, "new")}: ${t(L, "chores")}`,
      name: chore.name,
      fields: [
        { key: "name", type: "text", label: t(L, "f_name") },
        {
          key: "chore_type",
          type: "select",
          label: t(L, "f_chore_type"),
          options: [
            ["expected", t(L, "expected")],
            ["bonus", t(L, "bonus")],
          ],
        },
        { key: "slot", type: "select", label: t(L, "f_slot"), options: SLOTS.map((s) => [s, t(L, s)]) },
        {
          key: "weekdays",
          type: "multi",
          label: t(L, "f_weekdays"),
          options: [0, 1, 2, 3, 4, 5, 6].map((d) => [d, weekdayName(d, L)]),
        },
        {
          key: "kid_ids",
          type: "multi",
          label: t(L, "f_kids"),
          options: this._admin.kids.filter((k) => k.active).map((k) => [k.id, k.name]),
        },
        ...currencies.map((c) => ({
          key: `value_${c.id}`,
          type: "number",
          label: t(L, "f_value", { name: `${c.name} (${c.unit})` }),
        })),
        { key: "icon", type: "text", label: t(L, "f_icon") },
        { key: "description", type: "text", label: t(L, "f_description") },
        { key: "sort", type: "number", label: t(L, "f_sort") },
        { key: "active", type: "bool", label: t(L, "f_active") },
      ],
      values: {
        ...chore,
        ...Object.fromEntries(currencies.map((c) => [`value_${c.id}`, chore.values?.[String(c.id)]])),
      },
      onSave: async (v) => {
        const result = await this._pws("admin/chore/save", {
          ...(choreId ? { chore_id: choreId } : {}),
          name: v.name,
          chore_type: v.chore_type,
          slot: v.slot,
          weekdays: v.weekdays,
          kid_ids: v.kid_ids,
          values: Object.fromEntries(currencies.map((c) => [String(c.id), Math.max(0, v[`value_${c.id}`] ?? 0)])),
          icon: v.icon,
          description: v.description,
          sort: v.sort ?? 0,
          active: v.active,
        });
        // AC-5.5: a warning only; the chore is saved.
        if (result.warnings.length) {
          const names = result.warnings
            .map((id) => this._admin.currencies.find((c) => c.id === id)?.name)
            .join(", ");
          this._showInfo(t(L, "warn_after_payout", { names }));
        }
      },
      onDelete: choreId ? () => this._pws("admin/chore/delete", { chore_id: choreId }) : null,
    });
  }

  _openCurrencyForm(currencyId) {
    const L = this._lang;
    const cur = this._admin.currencies.find((c) => c.id === currencyId) ?? {
      payout_weekday: 4,
      can_be_lost: false,
      cap_mode: "fixed",
      active: true,
      sort: 0,
      icon: "",
    };
    this._openForm({
      title: currencyId ? cur.name : `${t(L, "new")}: ${t(L, "currencies")}`,
      name: cur.name,
      fields: [
        { key: "name", type: "text", label: t(L, "f_name") },
        { key: "unit", type: "text", label: t(L, "f_unit") },
        { key: "icon", type: "text", label: t(L, "f_icon") },
        {
          key: "payout_weekday",
          type: "select",
          label: t(L, "f_payout_weekday"),
          options: [0, 1, 2, 3, 4, 5, 6].map((d) => [d, weekdayName(d, L)]),
        },
        { key: "can_be_lost", type: "bool", label: t(L, "f_can_be_lost") },
        {
          key: "cap_mode",
          type: "select",
          label: t(L, "f_cap_mode"),
          options: [
            ["fixed", t(L, "cap_fixed")],
            ["pot", t(L, "cap_pot")],
          ],
        },
        { key: "default_max", type: "number", label: t(L, "f_default_max") },
        { key: "sort", type: "number", label: t(L, "f_sort") },
        { key: "active", type: "bool", label: t(L, "f_active") },
      ],
      values: cur,
      onSave: (v) =>
        this._pws("admin/currency/save", {
          ...(currencyId ? { currency_id: currencyId } : {}),
          name: v.name,
          unit: v.unit,
          icon: v.icon,
          payout_weekday: Number(v.payout_weekday),
          can_be_lost: v.can_be_lost,
          cap_mode: v.cap_mode,
          default_max: v.default_max,
          sort: v.sort ?? 0,
          active: v.active,
        }),
      onDelete: currencyId ? () => this._pws("admin/currency/delete", { currency_id: currencyId }) : null,
    });
  }

  _openSettingsForm() {
    const L = this._lang;
    const keys = ["idle_seconds", "wake_seconds", "pin_timeout_seconds"];
    this._openForm({
      title: t(L, "settings"),
      fields: [
        { key: "clean_hands_enabled", type: "bool", label: t(L, "f_clean_hands_enabled") },
        { key: "clean_hands_text", type: "text", label: t(L, "f_clean_hands_text") },
        ...keys.map((key) => ({ key, type: "number", label: t(L, `f_${key}`) })),
      ],
      values: this._admin.settings,
      onSave: (v) =>
        this._pws("admin/settings/save", {
          settings: {
            clean_hands_enabled: v.clean_hands_enabled,
            clean_hands_text: v.clean_hands_text,
            ...Object.fromEntries(keys.filter((k) => v[k] !== null).map((k) => [k, v[k]])),
          },
        }),
    });
  }

  // --- rendering -------------------------------------------------------------------

  _syncMenuButton() {
    const button = this.shadowRoot?.querySelector("ha-menu-button");
    if (button) {
      button.hass = this._hass;
      button.narrow = this._narrow;
    }
  }

  _render({ background = false } = {}) {
    if (!this.shadowRoot) return;
    if (this._form) {
      if (background) return; // don't disturb typing; the next render picks up new data
      if (this.shadowRoot.querySelector("form.form")) Object.assign(this._form.values, this._readForm());
    }
    const L = this._lang;
    const s = this._state;
    let title = t(L, "loading");
    let body = "";
    if (s) {
      if (this._view.name === "week") {
        const kid = s.kids.find((k) => k.id === this._view.kidId);
        const week = this._week ? isoWeek(this._week.week) : isoWeek(s.today);
        title = `${escapeHtml(kid?.name ?? "")} · ${t(L, "week", { n: week })}`;
        body = this._renderWeek();
      } else if (this._parent && this._tab === "payouts") {
        title = t(L, "tab_payouts");
        body = this._renderPayouts();
      } else if (this._parent && this._tab === "admin") {
        title = t(L, "tab_admin");
        body = this._renderAdmin();
      } else if (this._parent && this._tab === "log") {
        title = t(L, "tab_log");
        body = this._renderLog();
      } else {
        title = this._dayHeader();
        body = this._renderOverview();
      }
    }
    const back =
      this._view.name === "week"
        ? `<button class="nav" data-action="back" aria-label="${t(L, "back")}">←</button>`
        : "";
    this.shadowRoot.innerHTML = `
      <style>${STYLES}</style>
      <header><ha-menu-button></ha-menu-button>${back}<span class="title">${title}</span>
        ${this._renderTabs()}
        <button class="lock ${this._parent ? "open" : ""}" data-action="lock-toggle"
          aria-label="${t(L, this._parent ? "lock" : "unlock")}"><ha-icon icon="${
            this._parent ? "mdi:lock-open-variant" : "mdi:lock"
          }"></ha-icon></button></header>
      <main>${body}</main>
      ${this._renderForm()}
      ${this._renderSheet()}
      ${this._renderDialog()}
      ${this._pin !== null ? this._renderPinPad() : ""}
      ${this._cleanHands ? this._renderCleanHands() : ""}
      ${this._toast ? `<div class="toast ${this._toast.kind}">${escapeHtml(this._toast.text)}</div>` : ""}`;
    if (this._form) this._fillForm();
    this._syncMenuButton();
  }

  _renderTabs() {
    if (!this._parent) return "";
    const L = this._lang;
    const due = (this._payouts?.items ?? []).some((i) => i.is_payout_day && !i.paid);
    const tab = (id, label) =>
      `<button class="pill ${this._tab === id && this._view.name === "overview" ? "active" : ""}"
        data-action="tab" data-tab="${id}">${label}</button>`;
    return `<nav class="tabs">${tab("today", t(L, "tab_today"))}${tab(
      "payouts",
      `${t(L, "tab_payouts")}${due ? '<span class="dot" aria-label="!"></span>' : ""}`,
    )}${tab("admin", t(L, "tab_admin"))}${tab("log", t(L, "tab_log"))}</nav>`;
  }

  _dayHeader() {
    const L = this._lang;
    const { today, day } = this._state;
    const nav = dayNav(today, day);
    const arrow = (target, label, text) =>
      `<button class="nav" data-action="day" data-day="${target ?? ""}" aria-label="${t(L, label)}"
        ${target ? "" : "disabled"}>${text}</button>`;
    const back = day !== today ? `<button class="pill" data-action="day" data-day="">${t(L, "today")}</button>` : "";
    return `${arrow(nav.prev, "prev_day", "‹")}<span class="${day === today ? "" : "other-day"}">${escapeHtml(
      formatDay(day, L),
    )}</span>${arrow(nav.next, "next_day", "›")}${back}`;
  }

  _renderOverview() {
    const s = this._state;
    const L = this._lang;
    if (!s.kids.length) return `<p class="empty">${t(L, "no_kids")}</p>`;
    const closed = s.week_status === "closed" ? `<p class="warn">${t(L, "week_closed")}</p>` : "";
    const cols = s.kids
      .map((kid) => {
        const data = s.board[String(kid.id)] ?? { chores: [], bonus: [], balances: {} };
        const groups = groupBySlot(data.chores)
          .map(
            (g) => `<div class="slot">${t(L, g.slot)}</div>${g.items.map((i) => this._choreRow(i)).join("")}`,
          )
          .join("");
        const bonus = data.bonus.length
          ? `<div class="bonus"><div class="slot">${t(L, "bonus")}</div>${data.bonus
              .map((i) => this._choreRow(i))
              .join("")}</div>`
          : "";
        const empty = !data.chores.length && !data.bonus.length;
        const adjust = this._parent
          ? `<button class="small-btn" data-action="adjust" data-kid="${kid.id}">±</button>`
          : "";
        return `<section class="kid">
          <div class="kid-head"><button class="kid-name" data-action="kid" data-kid="${kid.id}">${escapeHtml(
            kid.name,
          )}</button>${adjust}</div>
          ${this._meters(data.balances)}
          ${groups}${bonus}
          ${empty ? `<p class="empty">${t(L, "no_chores")}</p>` : ""}
        </section>`;
      })
      .join("");
    return `${closed}<div class="columns" style="grid-template-columns: repeat(${s.kids.length}, minmax(0, 1fr))">${cols}</div>`;
  }

  _choreRow(inst) {
    // Kids can tick or untick any day of the open week (D8); future days are a preview.
    // Parents also get a ⋯ menu and see ⚠ on ticks made after the chore's day.
    const open = this._state.week_status === "open";
    const tappable = open && kidTap(inst, this._state.today) !== null;
    const late =
      this._parent && inst.late ? `<span class="late" title="${t(this._lang, "late_hint")}">⚠</span>` : "";
    const more =
      this._parent && parentActions(inst, this._state.today).length
        ? `<button class="more" data-action="more" data-id="${inst.id}">⋯</button>`
        : "";
    return `<div class="row"><button class="chore ${inst.status}" data-action="toggle" data-id="${inst.id}"
      ${tappable ? "" : "disabled"}><span class="box">${inst.status === "pending" ? "" : cellSymbol(inst.status)}</span>
      <span>${escapeHtml(inst.name)}</span>${late}</button>${more}</div>`;
  }

  _meters(balances) {
    return this._state.currencies
      .map((c) => {
        const b = progress(balances?.[String(c.id)]);
        const lost =
          c.can_be_lost && b.lost ? `<span class="lost">${t(this._lang, "lost", { n: b.lost })}</span>` : "";
        const bar = b.pct === null ? "" : `<div class="bar"><div class="fill" style="width:${b.pct}%"></div></div>`;
        return `<div class="meter">
          <div class="meter-label"><ha-icon icon="${escapeHtml(c.icon || "mdi:star")}"></ha-icon>
            ${escapeHtml(c.name)} ${lost}<span class="amount">${escapeHtml(amountLabel(b, c.unit))}</span></div>
          ${bar}
        </div>`;
      })
      .join("");
  }

  _renderWeek() {
    const L = this._lang;
    const w = this._week;
    if (!w) return `<p class="empty">${t(L, "loading")}</p>`;
    const today = this._state.today;
    // Today's cells are tappable for kids (D34); match them to today's instances by chore.
    // In parent mode, past cells open the ⋯ menu instead.
    const kidBoard = this._state.board[String(this._view.kidId)] ?? { chores: [], bonus: [] };
    const todayByChore = new Map([...kidBoard.chores, ...kidBoard.bonus].map((i) => [i.chore_id, i]));
    const head = w.days
      .map((d) => `<th class="${d === today ? "today" : ""}">${weekdayLetter(d, L)}</th>`)
      .join("");
    const rows = w.rows
      .map((r) => {
        const cells = w.days
          .map((d) => {
            const status = r.cells[d];
            const cls = `cell ${status ?? ""} ${d === today ? "today" : ""}`;
            const id = r.ids?.[d];
            const open = w.week_status === "open";
            const late = this._parent && r.late?.[d] ? `<sup class="late">⚠</sup>` : "";
            const inst = d === today ? todayByChore.get(r.chore_id) : null;
            if (inst && open && kidTap(inst, today)) {
              return `<td class="${cls}"><button data-action="toggle" data-confirm="1" data-id="${inst.id}">${cellSymbol(
                inst.status,
              )}${late}</button></td>`;
            }
            if (id && d < today && open) {
              // Parents get the ⋯ menu; kids may fix a forgotten tick (D8).
              const past = { id, day: d, status, type: r.type };
              if (this._parent) {
                return `<td class="${cls}"><button data-action="more" data-id="${id}" data-day="${d}">${cellSymbol(
                  status,
                )}${late}</button></td>`;
              }
              if (kidTap(past, today)) {
                return `<td class="${cls}"><button data-action="toggle" data-id="${id}" data-day="${d}">${cellSymbol(
                  status,
                )}</button></td>`;
              }
            }
            return `<td class="${cls}">${status ? cellSymbol(status) : ""}${late}</td>`;
          })
          .join("");
        const label = r.type === "bonus" ? `${t(L, "bonus")}: ${escapeHtml(r.name)}` : escapeHtml(r.name);
        return `<tr class="${r.type === "bonus" ? "bonus-row" : ""}"><td>${label}</td>${cells}</tr>`;
      })
      .join("");
    return `<div class="week-meters">${this._meters(w.balances)}</div>
      <table class="week"><thead><tr><th></th>${head}</tr></thead><tbody>${rows}</tbody></table>`;
  }

  _renderPayouts() {
    const L = this._lang;
    const p = this._payouts;
    if (!p) return `<p class="empty">${t(L, "loading")}</p>`;
    const s = this._state;
    const kidName = (id) => escapeHtml(s.kids.find((k) => k.id === id)?.name ?? `#${id}`);
    const currentWeek = mondayOf(s.today);
    const prevWeek = addDays(p.week, -7);
    const nextWeek = p.week < currentWeek ? addDays(p.week, 7) : null;
    const weekNav = `<div class="card"><h2>
      <button class="nav" data-action="payout-week" data-week="${prevWeek}">‹</button>
      <span class="grow">${t(L, "week", { n: isoWeek(p.week) })}${
        p.week_status === "closed" ? ` · <span class="muted">${t(L, "week_closed")}</span>` : ""
      }</span>
      ${nextWeek ? `<button class="nav" data-action="payout-week" data-week="${nextWeek === currentWeek ? "" : nextWeek}">›</button>` : ""}
      ${
        p.week === currentWeek
          ? p.week_status === "closed"
            ? `<button class="small-btn" data-action="reopen-week">${t(L, "reopen_week")}</button>`
            : `<button class="small-btn" data-action="close-week">${t(L, "close_week")}</button>`
          : ""
      }</h2></div>`;
    const cards = s.currencies
      .map((c) => {
        const items = p.items.filter((i) => i.currency_id === c.id);
        if (!items.length) return "";
        const payoutDay = items[0].payout_day;
        const today = items[0].is_payout_day ? ` · <b>${t(L, "payout_today")}</b>` : "";
        const rows = items
          .map((i) => {
            const paid = i.paid
              ? `${t(L, "paid", { amount: `${i.paid.amount} ${escapeHtml(c.unit)}` })}${
                  i.after_payout
                    ? ` <span class="warn">${t(L, "after_payout", { amount: `${i.after_payout} ${escapeHtml(c.unit)}` })}</span>`
                    : ""
                }`
              : "";
            const btn = i.paid
              ? `<button class="small-btn" data-action="pay" data-kid="${i.kid_id}" data-currency="${c.id}" data-paid="0">${t(L, "undo")}</button>`
              : `<button class="primary-btn" data-action="pay" data-kid="${i.kid_id}" data-currency="${c.id}" data-paid="1">${t(L, "mark_paid")}</button>`;
            const details = `<button class="small-btn" data-action="details" data-kid="${i.kid_id}">${t(
              L,
              "details",
            )}</button>`;
            return `<tr><td>${kidName(i.kid_id)}</td><td class="num">${i.amount_due} ${escapeHtml(c.unit)}</td>
              <td>${paid}</td><td class="actions">${details} ${btn}</td></tr>`;
          })
          .join("");
        return `<div class="card"><h2><ha-icon icon="${escapeHtml(c.icon || "mdi:star")}"></ha-icon>
          <span class="grow">${escapeHtml(c.name)}</span>
          <span class="muted">${t(L, "payout_day", { day: escapeHtml(formatDay(payoutDay, L)) })}${today}</span></h2>
          <table class="list"><tr class="muted"><th></th><th class="num">${t(L, "amount_due")}</th><th></th><th></th></tr>${rows}</table></div>`;
      })
      .join("");
    const adjustments = p.adjustments.length
      ? `<div class="card"><h2>${t(L, "adjustments")}</h2><table class="list">${p.adjustments
          .map((a) => {
            const cur = s.currencies.find((c) => c.id === a.currency_id);
            const sign = a.amount > 0 ? "+" : "";
            return `<tr><td>${kidName(a.kid_id)}</td><td class="num">${sign}${a.amount} ${escapeHtml(cur?.unit ?? "")}</td>
              <td>${escapeHtml(a.note)}</td><td class="muted">${escapeHtml(formatTimestamp(a.created_at, L))}</td></tr>`;
          })
          .join("")}</table></div>`
      : "";
    return weekNav + cards + adjustments;
  }

  _renderAdmin() {
    const L = this._lang;
    const a = this._admin;
    if (!a) return `<p class="empty">${t(L, "loading")}</p>`;
    const inactive = (x) => (x.active ? "" : ` <span class="muted">(${t(L, "inactive")})</span>`);
    const section = (title, action, rows) =>
      `<div class="card"><h2><span class="grow">${title}</span>
        <button class="small-btn" data-action="${action}">+ ${t(L, "new")}</button></h2>
        <table class="list">${rows}</table></div>`;
    const editBtn = (action, id) =>
      `<td class="actions"><button class="small-btn" data-action="${action}" data-id="${id}">${t(L, "edit")}</button></td>`;
    const kidName = (id) => escapeHtml(a.kids.find((k) => k.id === id)?.name ?? "?");
    const kids = a.kids
      .map((k) => `<tr><td>${escapeHtml(k.name)}${inactive(k)}</td>${editBtn("edit-kid", k.id)}</tr>`)
      .join("");
    const chores = a.chores
      .map((c) => {
        const days = c.weekdays.length
          ? c.weekdays.map((d) => weekdayName(d, L).slice(0, 3)).join(" ")
          : t(L, "every_day");
        const values = Object.entries(c.values)
          .map(([cid, v]) => `${v} ${escapeHtml(a.currencies.find((x) => x.id === Number(cid))?.unit ?? "")}`)
          .join(", ");
        return `<tr><td>${escapeHtml(c.name)}${inactive(c)}<br><span class="muted">${t(L, c.chore_type)} · ${t(
          L,
          c.slot,
        )} · ${days} · ${c.kid_ids.map(kidName).join(", ")}</span></td><td class="num">${values}</td>${editBtn(
          "edit-chore",
          c.id,
        )}</tr>`;
      })
      .join("");
    const currencies = a.currencies
      .map(
        (c) => `<tr><td>${escapeHtml(c.name)} (${escapeHtml(c.unit)})${inactive(c)}<br><span class="muted">${t(
          L,
          `cap_${c.cap_mode}`,
        )} · ${weekdayName(c.payout_weekday, L)}</span></td>${editBtn("edit-currency", c.id)}</tr>`,
      )
      .join("");
    return `<div class="columns" style="grid-template-columns: 1fr 1fr">
      <div>${section(t(L, "kids"), "edit-kid", kids)}${section(t(L, "currencies"), "edit-currency", currencies)}
        <div class="card"><h2><span class="grow">${t(L, "settings")}</span>
          <button class="small-btn" data-action="edit-settings">${t(L, "edit")}</button></h2></div></div>
      <div>${section(t(L, "chores"), "edit-chore", chores)}</div></div>`;
  }

  _renderLog() {
    const L = this._lang;
    const s = this._state;
    const f = this._logFilter;
    const kidName = (id) => escapeHtml(s.kids.find((k) => k.id === id)?.name ?? "");
    const kidOpts = [`<option value="">${t(L, "log_all_kids")}</option>`]
      .concat(
        s.kids.map(
          (k) => `<option value="${k.id}" ${f.kidId === k.id ? "selected" : ""}>${escapeHtml(k.name)}</option>`,
        ),
      )
      .join("");
    const groupOpts = Object.keys(LOG_GROUPS)
      .map((g) => `<option value="${g}" ${f.group === g ? "selected" : ""}>${t(L, `g_${g}`)}</option>`)
      .join("");
    const weekLabel = f.week ? t(L, "week", { n: isoWeek(f.week) }) : t(L, "log_all_weeks");
    const current = mondayOf(s.today);
    const prev = addDays(f.week ?? addDays(current, 7), -7);
    const next = f.week && f.week < current ? addDays(f.week, 7) : null;
    const filters = `<div class="card filters">
      <select data-filter="kid">${kidOpts}</select>
      <select data-filter="group">${groupOpts}</select>
      <label class="check"><input type="checkbox" data-filter="late" ${f.late ? "checked" : ""}> ${t(
        L,
        "log_late_only",
      )}</label>
      <span class="grow"></span>
      <button class="nav" data-action="log-week" data-week="${prev}">‹</button>
      <span>${weekLabel}</span>
      <button class="nav" data-action="log-week" data-week="${next ?? ""}" ${f.week ? "" : "disabled"}>›</button>
    </div>`;
    if (!this._log) return `${filters}<p class="empty">${t(L, "loading")}</p>`;
    if (!this._log.length) return `${filters}<p class="empty">${t(L, "log_empty")}</p>`;
    const rows = this._log
      .map((e) => {
        let after = null;
        try {
          after = e.after ? JSON.parse(e.after) : null;
        } catch {
          after = null;
        }
        let what = "";
        if (after?.chore) what = `${after.chore} → ${t(L, `act_${after.status}`)}`;
        else if (after?.name) what = after.name;
        else if (after?.amount !== undefined && after?.amount !== null) what = String(after.amount);
        if (e.action === "check" || e.action === "uncheck") what = after?.chore ?? "";
        const day = e.day && e.entity === "instance" ? shortDay(e.day, L) : "";
        const late = e.late ? `<span class="late" title="${t(L, "late_hint")}">⚠</span>` : "";
        return `<tr class="${e.late ? "late-row" : ""}"><td class="muted">${escapeHtml(formatTimestamp(e.ts, L))}</td>
          <td>${kidName(e.kid_id)}</td><td>${escapeHtml(t(L, `a_${e.action}`))}</td>
          <td>${escapeHtml(what)}</td><td>${escapeHtml(day)} ${late}</td>
          <td class="muted">${escapeHtml(e.note ?? "")}</td></tr>`;
      })
      .join("");
    const head = `<tr class="muted"><th>${t(L, "log_when")}</th><th>${t(L, "kids")}</th><th>${t(
      L,
      "log_event",
    )}</th><th>${t(L, "log_what")}</th><th>${t(L, "log_day")}</th><th>${t(L, "note")}</th></tr>`;
    return `${filters}<div class="card"><table class="list">${head}${rows}</table></div>`;
  }

  _renderForm() {
    if (!this._form) return "";
    const L = this._lang;
    const f = this._form;
    const fields = f.fields
      .map((field) => {
        const id = `f-${field.key}`;
        if (field.type === "bool") {
          return `<div class="field check"><input type="checkbox" id="${id}" name="${field.key}">
            <label for="${id}">${escapeHtml(field.label)}</label></div>`;
        }
        if (field.type === "select") {
          const opts = field.options
            .map(([v, label]) => `<option value="${escapeHtml(v)}">${escapeHtml(label)}</option>`)
            .join("");
          return `<div class="field"><label for="${id}">${escapeHtml(field.label)}</label>
            <select id="${id}" name="${field.key}">${opts}</select></div>`;
        }
        if (field.type === "multi") {
          const chips = field.options
            .map(
              ([v, label]) =>
                `<label><input type="checkbox" name="${field.key}" value="${escapeHtml(v)}">${escapeHtml(label)}</label>`,
            )
            .join("");
          return `<div class="field"><label>${escapeHtml(field.label)}</label><div class="chips">${chips}</div></div>`;
        }
        const type = field.type === "number" ? "number" : "text";
        return `<div class="field"><label for="${id}">${escapeHtml(field.label)}</label>
          <input type="${type}" id="${id}" name="${field.key}" ${type === "number" ? 'inputmode="numeric"' : ""}></div>`;
      })
      .join("");
    return `<div class="overlay"><div class="dialog"><h3>${escapeHtml(f.title)}</h3>
      <form class="form" onsubmit="return false">${fields}</form>
      <div class="actions">
        ${f.onDelete ? `<button class="danger" data-action="form-delete">${t(L, "delete")}</button>` : ""}
        <button data-action="form-cancel">${t(L, "cancel")}</button>
        <button class="primary" data-action="form-save">${t(L, "save")}</button>
      </div></div></div>`;
  }

  /** Put current values into the freshly rendered form inputs. */
  _fillForm() {
    const root = this.shadowRoot.querySelector("form.form");
    for (const field of this._form.fields) {
      const value = this._form.values[field.key];
      if (field.type === "bool") {
        root.querySelector(`[name="${field.key}"]`).checked = Boolean(value);
      } else if (field.type === "multi") {
        const set = new Set((value ?? []).map(Number));
        for (const input of root.querySelectorAll(`[name="${field.key}"]`)) {
          input.checked = set.has(Number(input.value));
        }
      } else {
        const input = root.querySelector(`[name="${field.key}"]`);
        if (value !== undefined && value !== null) input.value = String(value);
      }
    }
  }

  _renderSheet() {
    if (!this._sheet) return "";
    const L = this._lang;
    const items = this._sheet.items
      .map((item, i) => `<button data-action="sheet-item" data-index="${i}">${escapeHtml(item.label)}</button>`)
      .join("");
    return `<div class="overlay"><div class="dialog"><h3>${escapeHtml(this._sheet.title)}</h3>
      <div class="sheet">${items}<button data-action="sheet-close">${t(L, "cancel")}</button></div></div></div>`;
  }

  _renderDialog() {
    if (!this._dialog) return "";
    const L = this._lang;
    return `<div class="overlay"><div class="dialog">
      <div>${escapeHtml(this._dialog.text)}</div>
      <div class="actions">
        <button data-action="dialog-cancel">${t(L, "cancel")}</button>
        <button class="primary" data-action="dialog-yes">${t(L, "yes")}</button>
      </div></div></div>`;
  }

  _renderPinPad() {
    const L = this._lang;
    const keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
      .map((d) => `<button data-action="pin-digit" data-digit="${d}">${d}</button>`)
      .join("");
    return `<div class="overlay"><div class="dialog pinpad"><h3>${t(L, "enter_pin")}</h3>
      <div class="pin-dots">${"●".repeat(this._pin.length) || "&nbsp;"}</div>
      <div class="keys">${keys}
        <button data-action="pin-back">⌫</button>
        <button data-action="pin-digit" data-digit="0">0</button>
        <button data-action="pin-ok">OK</button>
      </div>
      <div class="actions"><button data-action="pin-cancel">${t(L, "cancel")}</button></div>
    </div></div>`;
  }

  _renderCleanHands() {
    const L = this._lang;
    const text = this._state?.settings?.clean_hands_text || t(L, "clean_hands");
    return `<div class="overlay clean-hands" data-action="clean-hands">
      <div>🧼 ${escapeHtml(text)}<small>${t(L, "tap_to_continue")}</small></div></div>`;
  }
}

if (globalThis.customElements && !customElements.get("chores-and-rewards-panel")) {
  customElements.define("chores-and-rewards-panel", ChoresPanel);
}
