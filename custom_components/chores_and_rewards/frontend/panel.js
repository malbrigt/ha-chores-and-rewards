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
    earn_title: "Hva vil du ha for «{name}»?",
    earn_pay: "{amount} {name}",
    earn_refill: "Vinn tilbake {amount} {name}",
    act_done_for: "Merk som gjort: {label}",
    error_nothing_lost: "Ingenting å vinne tilbake.",
    error_decimals_locked: "Desimaler kan ikke endres etter at valutaen er laget.",
    f_decimals: "Desimaler (kan ikke endres senere)",
    back: "Tilbake",
    more_actions: "Flere valg for {name}",
    adjust_for: "Juster saldo for {name}",
    open_week_of: "Vis uka til {name}",
    prev_week: "Forrige uke",
    next_week: "Neste uke",
    backspace: "Slett siste siffer",
    cell_label: "{name}, {day}: {status}",
    st_done: "gjort",
    st_missed: "ikke gjort",
    st_rejected: "avvist",
    st_excused: "fritatt",
    st_pending: "ikke gjort ennå",
    st_none: "ikke planlagt",
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
    a_auto_missed: "Ikke gjort (midnatt)",
    a_instance_create: "Gjøremål lagt til dagen",
    a_instance_update: "Gjøremål oppdatert",
    a_instance_delete: "Gjøremål fjernet fra dagen",
    a_week_open: "Ny uke",
    a_rollover: "Dagsskifte",
    a_db_created: "Database opprettet",
    a_pin_unlock: "Foreldremodus låst opp",
    a_pin_wrong_pin: "Feil PIN",
    a_pin_locked_out: "PIN sperret",
    a_pin_lock: "Foreldremodus låst",
    a_pin_reset: "PIN endret",
    g_system: "System og PIN",
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
    error_duplicate_name: "Navnet er allerede i bruk.",
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
    earn_title: "What do you want for “{name}”?",
    earn_pay: "{amount} {name}",
    earn_refill: "Win back {amount} {name}",
    act_done_for: "Mark done: {label}",
    error_nothing_lost: "Nothing to win back.",
    error_decimals_locked: "Decimals can't be changed once the currency exists.",
    f_decimals: "Decimals (can't be changed later)",
    back: "Back",
    more_actions: "More options for {name}",
    adjust_for: "Adjust balance for {name}",
    open_week_of: "Show {name}'s week",
    prev_week: "Previous week",
    next_week: "Next week",
    backspace: "Delete last digit",
    cell_label: "{name}, {day}: {status}",
    st_done: "done",
    st_missed: "not done",
    st_rejected: "rejected",
    st_excused: "excused",
    st_pending: "not done yet",
    st_none: "not scheduled",
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
    a_auto_missed: "Not done (midnight)",
    a_instance_create: "Chore added to the day",
    a_instance_update: "Chore updated",
    a_instance_delete: "Chore removed from the day",
    a_week_open: "New week",
    a_rollover: "Day change",
    a_db_created: "Database created",
    a_pin_unlock: "Parent mode unlocked",
    a_pin_wrong_pin: "Wrong PIN",
    a_pin_locked_out: "PIN locked out",
    a_pin_lock: "Parent mode locked",
    a_pin_reset: "PIN changed",
    g_system: "System and PIN",
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
    error_duplicate_name: "That name is already in use.",
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
  // `lost` is what is still lost: extra chores may have won some back (D49).
  const { total = 0, cap = null, lost = 0, refilled = 0 } = balance || {};
  const pct = cap ? Math.min(100, Math.round((total / cap) * 100)) : null;
  return { total, cap, lost: lost - refilled, pct };
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

/**
 * Currencies a done extra chore may earn, payment first, then refills (mirrors
 * logic.earn_options, D49). Can't-be-lost currencies always pay; a can-be-lost one is
 * only on offer while the kid still has some of it to win back this week.
 */
export function earnOptions(inst, currencies, balances) {
  const payment = [];
  const refill = [];
  for (const c of currencies) {
    if (!((inst.values?.[String(c.id)] ?? 0) > 0)) continue;
    const b = balances?.[String(c.id)];
    if (!c.can_be_lost) payment.push(c.id);
    else if (b && b.lost > b.refilled) refill.push(c.id);
  }
  return [...payment, ...refill];
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
  week: ["close_week", "reopen_week", "week_open"],
  system: [
    "auto_missed",
    "instance_create",
    "instance_update",
    "instance_delete",
    "rollover",
    "db_created",
    "pin_unlock",
    "pin_wrong_pin",
    "pin_locked_out",
    "pin_lock",
    "pin_reset",
  ],
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

// Amounts arrive as integers in the currency's minor unit: with decimals = 2, 50 is
// 0.50 € (D50). These helpers are the only place that converts.

/** A minor-unit amount as a number in the user's locale: 50 → "0,50" (nb), 200 → "2". */
export function formatNumber(minor, decimals, lang) {
  const scale = 10 ** decimals;
  return new Intl.NumberFormat(LOCALE[lang] ?? LOCALE.en, {
    minimumFractionDigits: minor % scale === 0 ? 0 : decimals,
    maximumFractionDigits: decimals,
    useGrouping: false,
  }).format(minor / scale);
}

/** A minor-unit amount with its unit: "0,50 €", "10 min". */
export function formatAmount(minor, currency, lang) {
  return `${formatNumber(minor, currency?.decimals ?? 0, lang)} ${currency?.unit ?? ""}`.trim();
}

/** Typed text to a minor-unit integer: "0,5" or "0.5" → 50 (decimals 2); "" or junk → null. */
export function parseAmount(text, decimals) {
  const s = String(text ?? "").trim().replace(",", ".");
  if (!/^-?(\d+\.?\d*|\.\d+)$/.test(s)) return null;
  return Math.round(Number(s) * 10 ** decimals);
}

/** Balance with unit, e.g. "40/60 min", "4,50/7 €", or "40 kr" when uncapped. */
export function amountLabel({ total, cap }, currency, lang) {
  const n = (v) => formatNumber(v, currency?.decimals ?? 0, lang);
  return `${cap ? `${n(total)}/${n(cap)}` : n(total)} ${currency?.unit ?? ""}`.trim();
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

// --- template utils -----------------------------------------------------------
// html`` escapes every interpolated value unless it is wrapped in raw() or is itself the
// result of html``. Arrays are joined. null/undefined/false render as nothing.

class Raw {
  constructor(text) {
    this.text = text;
  }

  toString() {
    return this.text;
  }
}

export function raw(text) {
  return new Raw(String(text));
}

function renderValue(value) {
  if (value === null || value === undefined || value === false) return "";
  if (value instanceof Raw) return value.text;
  if (Array.isArray(value)) return value.map(renderValue).join("");
  return escapeHtml(value);
}

export function html(strings, ...values) {
  let out = strings[0];
  values.forEach((value, i) => {
    out += renderValue(value) + strings[i + 1];
  });
  return new Raw(out);
}

const icon = (name) => html`<ha-icon icon="${name}"></ha-icon>`;

// --- styles (HA 2026 theme tokens; dark mode comes from the variables) ----------

const STYLES = `
  :host {
    display: block;
    min-height: 100vh;
    background: var(--primary-background-color);
    color: var(--primary-text-color);
    font-family: var(--ha-font-family-body, Roboto, system-ui, sans-serif);
    -webkit-tap-highlight-color: transparent;
    --cr-radius: var(--ha-card-border-radius, var(--ha-border-radius-lg, 12px));
    --cr-radius-sm: var(--ha-border-radius-md, 8px);
    --cr-touch: 44px;
  }
  header {
    display: flex;
    align-items: center;
    gap: 8px;
    box-sizing: border-box;
    min-height: var(--header-height, 56px);
    padding: var(--safe-area-inset-top, 0) 12px 0 4px;
    background: var(--app-header-background-color, var(--primary-background-color));
    color: var(--app-header-text-color, var(--primary-text-color));
    border-bottom: var(--app-header-border-bottom, 1px solid var(--divider-color));
    font-size: 1.25rem;
  }
  .title { flex: 1; display: flex; align-items: center; gap: 4px; min-width: 0; }
  .title .text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .title .other-day { font-style: italic; }
  .tabs { display: flex; gap: 6px; flex-wrap: wrap; }
  button {
    font: inherit;
    color: inherit;
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
    text-align: left;
  }
  button:focus-visible, select:focus-visible, input:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
  }
  .icon-btn {
    width: var(--cr-touch);
    height: var(--cr-touch);
    display: inline-grid;
    place-items: center;
    border-radius: 50%;
    flex: none;
  }
  .icon-btn[disabled] { opacity: 0.3; cursor: default; }
  .lock.open { background: var(--warning-color, #ffa600); color: var(--text-primary-color, #fff); }
  .pill {
    min-height: var(--cr-touch);
    padding: 0 16px;
    border: 1px solid var(--divider-color);
    border-radius: calc(var(--cr-touch) / 2);
    font-size: 1rem;
  }
  .pill.active { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: transparent; }
  .dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--warning-color, #ffa600);
    margin-left: 6px;
    vertical-align: middle;
  }
  main { padding: 12px; }
  .columns { display: grid; gap: 12px; grid-template-columns: repeat(var(--cols, 1), minmax(0, 1fr)); }
  :host([narrow]) .columns { grid-template-columns: minmax(0, 1fr); }
  @media (max-width: 700px) { .columns { grid-template-columns: minmax(0, 1fr); } }
  .card, .kid {
    background: var(--card-background-color);
    border-radius: var(--cr-radius);
    padding: 12px 14px 16px;
    box-shadow: var(--ha-card-box-shadow, none);
    border: 1px solid var(--divider-color);
  }
  .card { margin-bottom: 12px; }
  .card h2 { margin: 4px 0 10px; font-size: 1.2rem; display: flex; align-items: center; gap: 8px; }
  .grow { flex: 1; }
  .kid-head { display: flex; align-items: center; gap: 4px; }
  .kid-name {
    flex: 1;
    min-height: var(--cr-touch);
    font-size: 1.5rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 2px;
  }
  .kid-name ha-icon { color: var(--secondary-text-color); }
  .small-btn {
    min-height: var(--cr-touch);
    padding: 0 14px;
    border-radius: calc(var(--cr-touch) / 2);
    border: 1px solid var(--divider-color);
    font-size: 0.95rem;
  }
  .primary-btn {
    min-height: var(--cr-touch);
    padding: 0 16px;
    border-radius: var(--cr-radius-sm);
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
  .chore .earned { margin-left: auto; color: var(--secondary-text-color); font-size: 0.85rem; }
  ha-icon { --mdc-icon-size: 20px; }
  .bar { height: 10px; border-radius: 5px; background: var(--divider-color); overflow: hidden; margin-top: 3px; }
  .fill { height: 100%; background: var(--primary-color); border-radius: 5px; }
  .slot {
    margin: 14px 0 4px;
    font-size: 0.8rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--secondary-text-color);
  }
  .row { display: flex; align-items: center; border-bottom: 1px solid var(--divider-color); }
  .chore { display: flex; align-items: center; gap: 12px; flex: 1; min-height: 56px; font-size: 1.15rem; }
  .box {
    flex: none;
    display: grid;
    place-items: center;
    width: 34px;
    height: 34px;
    border-radius: var(--cr-radius-sm);
    border: 2px solid var(--secondary-text-color);
    font-size: 1.3rem;
  }
  .chore.done .box {
    background: var(--success-color, #43a047);
    border-color: var(--success-color, #43a047);
    color: var(--text-primary-color, #fff);
  }
  .chore.missed .box, .chore.rejected .box { border-color: var(--error-color); color: var(--error-color); }
  .chore.excused .box { color: var(--secondary-text-color); }
  .chore[disabled] { cursor: default; opacity: 0.75; }
  .bonus { margin-top: 18px; padding-top: 6px; border-top: 2px dashed var(--divider-color); opacity: 0.6; }
  .bonus .chore { min-height: 48px; font-size: 1rem; }
  .bonus .box { border-radius: 50%; width: 28px; height: 28px; }
  .late { color: var(--warning-color, #ffa600); --mdc-icon-size: 16px; margin-left: 4px; }
  .empty, .muted { color: var(--secondary-text-color); }
  .empty { padding: 12px 0; }
  .warn { color: var(--warning-color, #ffa600); }
  .week-meters { display: flex; flex-wrap: wrap; gap: 8px 32px; margin-bottom: 12px; }
  .week-meters .meter { flex: 1 1 260px; }
  table { width: 100%; border-collapse: collapse; }
  table.week {
    background: var(--card-background-color);
    border-radius: var(--cr-radius);
    overflow: hidden;
    font-size: 1.1rem;
  }
  th, td {
    border-bottom: 1px solid var(--divider-color);
    padding: 10px 6px;
    text-align: center;
    vertical-align: middle;
  }
  table.week th:first-child, table.week td:first-child { text-align: left; padding-left: 14px; }
  table.list td, table.list th { text-align: left; }
  table.list .num { text-align: right; white-space: nowrap; }
  table.list .actions { text-align: right; white-space: nowrap; }
  table.list { user-select: text; }
  table.week .today { background: rgba(var(--rgb-primary-color, 3, 169, 244), 0.12); }
  table.week tr.bonus-row { opacity: 0.6; }
  table.week td.cell { font-size: 1.4rem; width: 9%; }
  table.week td.cell.done { color: var(--success-color, #43a047); }
  table.week td.cell.missed, table.week td.cell.rejected { color: var(--error-color); }
  table.week td button { width: 100%; min-height: var(--cr-touch); text-align: center; font-size: 1.4rem; }
  .filters { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  select, input[type="text"], input[type="number"] {
    font: inherit;
    font-size: 1.05rem;
    min-height: var(--cr-touch);
    box-sizing: border-box;
    padding: 0 10px;
    border-radius: var(--cr-radius-sm);
    border: 1px solid var(--divider-color);
    background: var(--primary-background-color);
    color: var(--primary-text-color);
  }
  .check { display: flex; align-items: center; gap: 8px; min-height: var(--cr-touch); }
  input[type="checkbox"] { width: 24px; height: 24px; accent-color: var(--primary-color); }
  dialog {
    border: none;
    padding: 24px;
    border-radius: var(--ha-dialog-border-radius, 24px);
    background: var(--card-background-color);
    color: var(--primary-text-color);
    min-width: min(320px, 90vw);
    max-width: 90vw;
    max-height: 90vh;
    overflow: auto;
    font-size: 1.15rem;
  }
  dialog::backdrop { background: rgba(0, 0, 0, 0.5); }
  dialog h3 { margin: 0 0 16px; }
  .actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px; flex-wrap: wrap; }
  .actions button, .sheet button {
    min-height: var(--cr-touch);
    padding: 0 20px;
    border-radius: var(--cr-radius-sm);
    border: 1px solid var(--divider-color);
  }
  .actions .primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border: none; }
  .actions .danger { color: var(--error-color); margin-right: auto; }
  .sheet { display: flex; flex-direction: column; gap: 10px; }
  .field { display: flex; flex-direction: column; gap: 4px; margin-bottom: 12px; }
  .field label, fieldset legend { font-size: 0.9rem; color: var(--secondary-text-color); }
  fieldset { border: none; padding: 0; margin: 0 0 12px; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; }
  .chips label {
    display: flex;
    align-items: center;
    gap: 6px;
    min-height: var(--cr-touch);
    padding: 0 12px;
    border: 1px solid var(--divider-color);
    border-radius: calc(var(--cr-touch) / 2);
  }
  .pinpad { text-align: center; }
  .pin-dots { font-size: 2rem; letter-spacing: 0.4em; min-height: 2.6rem; margin-bottom: 12px; }
  .keys { display: grid; grid-template-columns: repeat(3, 80px); gap: 12px; justify-content: center; }
  .keys button {
    height: 64px;
    border-radius: var(--cr-radius-sm);
    border: 1px solid var(--divider-color);
    font-size: 1.6rem;
    text-align: center;
  }
  dialog.clean-hands { padding: 0; }
  .clean-hands button {
    display: grid;
    place-items: center;
    gap: 16px;
    width: min(600px, 90vw);
    padding: 48px 24px;
    font-size: 2.5rem;
    text-align: center;
  }
  .clean-hands ha-icon { --mdc-icon-size: 72px; color: var(--primary-color); }
  .clean-hands small { font-size: 1.1rem; color: var(--secondary-text-color); }
  .toast {
    position: fixed;
    left: 50%;
    bottom: 24px;
    transform: translateX(-50%);
    background: var(--error-color);
    color: var(--text-primary-color, #fff);
    padding: 12px 20px;
    border-radius: var(--cr-radius-sm);
    font-size: 1.1rem;
    z-index: 20;
  }
  .toast[hidden] { display: none; }
  .toast.info { background: var(--primary-color); color: var(--text-primary-color, #fff); }
`;

const SHELL = `
  <header>
    <ha-menu-button></ha-menu-button>
    <div class="title" id="title"></div>
    <nav class="tabs" id="tabs"></nav>
    <button class="icon-btn lock" id="lock" data-action="lock-toggle"></button>
  </header>
  <main id="main"></main>
  <div id="dialogs"></div>
  <div class="toast" id="toast" role="status" aria-live="polite" hidden></div>`;

// Order matters: later dialogs open on top of earlier ones.
const DIALOG_KINDS = ["form", "sheet", "confirm", "pin", "clean"];

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
    this._dialog = null; // confirm: {text, onYes}
    this._sheet = null; // {title, items: [{label, run}]}
    this._form = null; // {title, fields, values, onSave, onDelete, name}
    this._toast = null;
    this._cleanHands = false;
    this._dialogEls = {};
    this._reloadSeq = 0;
    this._lastActivity = Date.now();
    this._onActivity = () => {
      this._lastActivity = Date.now();
    };
    this._onReady = () => this._scheduleReload();
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
    this.toggleAttribute?.("narrow", Boolean(narrow));
    this._syncMenuButton();
  }

  set panel(panel) {
    this._panelConfig = panel;
  }

  set route(route) {
    this._route = route;
  }

  connectedCallback() {
    if (!this.shadowRoot) this._buildShell();
    for (const type of ["pointerdown", "keydown"]) {
      this.addEventListener(type, this._onActivity, { capture: true });
    }
    this._idleTimer = setInterval(() => this._checkIdle(), 2000);
    this._render();
    if (this._hass) this._connect();
  }

  disconnectedCallback() {
    for (const type of ["pointerdown", "keydown"]) {
      this.removeEventListener(type, this._onActivity, { capture: true });
    }
    clearInterval(this._idleTimer);
    clearTimeout(this._toastTimer);
    clearTimeout(this._reloadTimer);
    clearTimeout(this._retryTimer);
    this._hass?.connection.removeEventListener("ready", this._onReady);
    this._unsubscribe?.then((unsub) => unsub()).catch(() => {});
    this._unsubscribe = null;
  }

  _buildShell() {
    const root = this.attachShadow({ mode: "open" });
    root.innerHTML = SHELL;
    // Styles are parsed once (constructable stylesheet), with a <style> fallback.
    try {
      const sheet = new CSSStyleSheet();
      sheet.replaceSync(STYLES);
      root.adoptedStyleSheets = [sheet];
    } catch {
      const style = document.createElement("style");
      style.textContent = STYLES;
      root.prepend(style);
    }
    this._els = {
      title: root.getElementById("title"),
      tabs: root.getElementById("tabs"),
      lock: root.getElementById("lock"),
      main: root.getElementById("main"),
      dialogs: root.getElementById("dialogs"),
      toast: root.getElementById("toast"),
    };
    root.addEventListener("click", (ev) => this._onClick(ev));
    root.addEventListener("change", (ev) => this._onChange(ev));
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
    // HA's websocket library re-subscribes by itself after a reconnect; `ready` refreshes.
    this._hass.connection.removeEventListener("ready", this._onReady);
    this._hass.connection.addEventListener("ready", this._onReady);
    this._unsubscribe = this._hass.connection.subscribeMessage(() => this._scheduleReload(), {
      type: `${P}subscribe`,
    });
    try {
      await this._unsubscribe;
    } catch (err) {
      this._unsubscribe = null; // retry, e.g. if the integration was still loading
      this._retryTimer = setTimeout(() => this._connect(), 5000);
      this._showError(err);
    }
    await this._reload();
  }

  _scheduleReload() {
    clearTimeout(this._reloadTimer);
    this._reloadTimer = setTimeout(() => this._reload(), 150);
  }

  async _reload() {
    const seq = ++this._reloadSeq; // only the newest reload may update the screen
    try {
      let state = await this._ws("get_state", this._day ? { day: this._day } : {});
      // A new week (midnight Sunday) or a stale day snaps back to today.
      if (this._day && !sameWeek(state.today, this._day)) {
        this._day = null;
        state = await this._ws("get_state");
      }
      const week =
        this._view.name === "week" ? await this._ws("get_week", { kid_id: this._view.kidId }) : null;
      if (seq !== this._reloadSeq) return;
      this._state = state;
      this._week = week;
      if (this._parent) await this._reloadParent();
    } catch (err) {
      this._showError(err);
    }
    if (seq === this._reloadSeq) this._render({ background: true });
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

  /** A minimal instance for a past week-grid cell (not in the day's board). */
  _weekInstance(id, day) {
    const row = this._week?.rows.find((r) => r.ids?.[day] === id);
    if (!row) return null;
    const values = row.values?.[day] ?? {};
    return { id, day, type: row.type, status: row.cells[day], name: row.name, kid_id: this._view.kidId, values };
  }

  async _setDone(inst, done, currencyId = null) {
    try {
      const payload = { instance_id: inst.id, done };
      if (currencyId !== null) payload.currency_id = currencyId;
      const { instance } = await this._ws("set_done", payload);
      this._replaceInstance(instance); // instant feedback; the update event reloads the rest
      this._render();
    } catch (err) {
      this._showError(err);
    }
  }

  _replaceInstance(instance) {
    for (const kid of Object.values(this._state?.board ?? {})) {
      for (const list of [kid.chores, kid.bonus]) {
        const i = list.findIndex((x) => x.id === instance.id);
        if (i >= 0) list[i] = instance;
      }
    }
  }

  async _run(fn, { info = null } = {}) {
    try {
      await fn();
      if (info) this._showInfo(info);
      await this._reload();
    } catch (err) {
      this._showError(err);
    }
  }

  // --- parent session -----------------------------------------------------------

  async _submitPin() {
    const pin = this._pin;
    this._pin = "";
    this._render();
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
    if (/^\d$/.test(ev.key)) this._pinDigit(ev.key);
    else if (ev.key === "Backspace") this._pin = this._pin.slice(0, -1);
    else if (ev.key === "Enter") {
      ev.preventDefault();
      this._submitPin();
      return;
    } else return;
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
    const options = done ? this._earnOptions(inst) : [];
    if (options.length > 1) {
      // Pay or win back (D49): picking is the confirmation, also for a past day.
      const title = t(this._lang, "earn_title", { name: inst.name });
      const day = inst.day === this._state.today ? "" : ` · ${shortDay(inst.day, this._lang)}`;
      const items = options.map((cid) => ({
        label: this._earnLabel(inst, cid),
        run: () => this._setDone(inst, true, cid),
      }));
      this._sheet = { title: title + day, items };
      return;
    }
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

  /** A currency by id, including inactive ones when the admin list is loaded. */
  _currency(id) {
    return (this._admin?.currencies ?? []).find((c) => c.id === id) ?? this._state?.currencies.find((c) => c.id === id);
  }

  /** What a done extra chore may earn for this kid this week (D49). Expected: none. */
  _earnOptions(inst) {
    if (inst.type !== "bonus") return [];
    const balances =
      this._view.name === "week" ? this._week?.balances : this._state.board?.[String(inst.kid_id)]?.balances;
    return earnOptions(inst, this._state.currencies, balances);
  }

  _earnLabel(inst, currencyId) {
    const c = this._state.currencies.find((x) => x.id === currencyId);
    const amount = formatAmount(inst.values?.[String(currencyId)] ?? 0, c, this._lang);
    return t(this._lang, c?.can_be_lost ? "earn_refill" : "earn_pay", { amount, name: c?.name ?? "" });
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
    const setStatus = (status, extra = {}) =>
      this._run(() => this._pws("parent/set_status", { instance_id: inst.id, status, ...extra }));
    const options = this._earnOptions(inst);
    const items = parentActions(inst, this._state.today).flatMap((status) =>
      status === "done" && options.length > 1
        ? options.map((cid) => ({
            label: t(L, "act_done_for", { label: this._earnLabel(inst, cid) }),
            run: () => setStatus(status, { currency_id: cid }),
          }))
        : [{ label: t(L, `act_${status}`), run: () => setStatus(status) }],
    );
    items.push({ label: t(L, "adjust"), run: () => this._openAdjust(inst.kid_id) });
    this._sheet = { title: inst.name, items };
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
    const busy = this._form || this._pin !== null; // never interrupt typing
    const away = this._view.name !== "overview" || this._day;
    if (away && !busy && idle > settings.idle_seconds * 1000) {
      this._view = { name: "overview" };
      this._day = null;
      this._dialog = this._sheet = null;
      this._scheduleReload();
      changed = true;
    }
    if (settings.clean_hands_enabled && !busy && !this._cleanHands && idle > settings.wake_seconds * 1000) {
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
    this._renderToast();
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => {
      this._toast = null;
      this._renderToast();
    }, 4000);
  }

  // --- forms ----------------------------------------------------------------------
  // A form's inputs are rendered once when it opens and read from the DOM on save,
  // so background updates never touch what is being typed.

  _openForm(form) {
    this._form = form;
    this._render();
  }

  _formEl() {
    return this._dialogEls.form?.querySelector("form.form") ?? null;
  }

  _readForm() {
    const root = this._formEl();
    const values = {};
    for (const f of this._form.fields) {
      if (f.type === "bool") values[f.key] = root.querySelector(`[name="${f.key}"]`).checked;
      else if (f.type === "multi") {
        values[f.key] = [...root.querySelectorAll(`[name="${f.key}"]:checked`)].map((i) => Number(i.value));
      } else if (f.type === "number") {
        values[f.key] = parseOptionalInt(root.querySelector(`[name="${f.key}"]`).value);
      } else if (f.type === "amount") {
        // Fields are read in order, so a currency select above can set the decimals (D50).
        const text = root.querySelector(`[name="${f.key}"]`).value;
        values[f.key] = parseAmount(text, this._fieldDecimals(f, values));
      } else values[f.key] = root.querySelector(`[name="${f.key}"]`).value;
    }
    return values;
  }

  _fieldDecimals(field, values) {
    return (typeof field.decimals === "function" ? field.decimals(values) : field.decimals) ?? 0;
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
        {
          key: "amount",
          type: "amount",
          label: t(L, "amount"),
          decimals: (v) => this._currency(Number(v.currency_id ?? this._state.currencies[0]?.id))?.decimals,
        },
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
          type: "amount",
          decimals: c.decimals,
          label: t(L, "f_max", { name: `${c.name} (${c.unit})` }),
        })),
        { key: "sort", type: "number", label: t(L, "f_sort") },
        { key: "active", type: "bool", label: t(L, "f_active") },
      ],
      values: { ...kid, ...Object.fromEntries(currencies.map((c) => [`max_${c.id}`, kid.max?.[String(c.id)]])) },
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
          type: "amount",
          decimals: c.decimals,
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
          const names = result.warnings.map((id) => this._admin.currencies.find((c) => c.id === id)?.name).join(", ");
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
      decimals: 0,
      active: true,
      sort: 0,
      icon: "",
    };
    // Decimals are chosen once, on create: they define how every amount is stored (D50).
    const decimalsField = currencyId
      ? []
      : [{ key: "decimals", type: "select", label: t(L, "f_decimals"), options: [0, 1, 2].map((d) => [d, formatNumber(1, d, L)]) }]; // 1, 0.1, 0.01
    this._openForm({
      title: currencyId ? cur.name : `${t(L, "new")}: ${t(L, "currencies")}`,
      name: cur.name,
      fields: [
        { key: "name", type: "text", label: t(L, "f_name") },
        { key: "unit", type: "text", label: t(L, "f_unit") },
        ...decimalsField,
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
        {
          key: "default_max",
          type: "amount",
          label: t(L, "f_default_max"),
          decimals: (v) => (currencyId ? cur.decimals : Number(v.decimals ?? 0)),
        },
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
          decimals: currencyId ? cur.decimals : Number(v.decimals),
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
  // The shell (header, main, dialog host, toast) is built once. Each render updates the
  // header parts and <main>, and opens/closes native <dialog>s to match the state.

  _syncMenuButton() {
    const button = this.shadowRoot?.querySelector("ha-menu-button");
    if (button) {
      button.hass = this._hass;
      button.narrow = this._narrow;
    }
  }

  _render({ background = false } = {}) {
    if (!this._els) return;
    const L = this._lang;
    const s = this._state;
    let title = html`<span class="text">${t(L, "loading")}</span>`;
    let body = html``;
    if (s) {
      if (this._view.name === "week") {
        const kid = s.kids.find((k) => k.id === this._view.kidId);
        const week = this._week ? isoWeek(this._week.week) : isoWeek(s.today);
        title = html`<button class="icon-btn" data-action="back" aria-label="${t(L, "back")}">
            ${icon("mdi:arrow-left")}</button
          ><span class="text">${kid?.name ?? ""} · ${t(L, "week", { n: week })}</span>`;
        body = this._renderWeek();
      } else if (this._parent && this._tab !== "today") {
        title = html`<span class="text">${t(L, `tab_${this._tab}`)}</span>`;
        body = { payouts: () => this._renderPayouts(), admin: () => this._renderAdmin(), log: () => this._renderLog() }[
          this._tab
        ]();
      } else {
        title = this._dayHeader();
        body = this._renderOverview();
      }
    }
    this._els.title.innerHTML = String(title);
    this._els.tabs.innerHTML = String(this._renderTabs());
    this._els.lock.classList.toggle("open", this._parent);
    this._els.lock.setAttribute("aria-label", t(L, this._parent ? "lock" : "unlock"));
    this._els.lock.innerHTML = String(icon(this._parent ? "mdi:lock-open-variant" : "mdi:lock"));
    this._renderMain(String(body), background);
    this._syncDialogs();
    this._renderToast();
    this._syncMenuButton();
  }

  /** Replace <main>, keeping keyboard focus (and never yanking an open select/input). */
  _renderMain(markup, background) {
    const main = this._els.main;
    const active = this.shadowRoot.activeElement;
    const inMain = active && main.contains(active);
    if (background && inMain && ["SELECT", "INPUT"].includes(active.tagName)) return;
    const key = inMain ? focusKey(active) : null;
    main.innerHTML = markup;
    if (key) main.querySelector(key)?.focus();
  }

  _renderToast() {
    const el = this._els?.toast;
    if (!el) return;
    el.hidden = !this._toast;
    el.className = `toast ${this._toast?.kind ?? ""}`;
    el.textContent = this._toast?.text ?? "";
  }

  _renderTabs() {
    if (!this._parent) return html``;
    const L = this._lang;
    const due = (this._payouts?.items ?? []).some((i) => i.is_payout_day && !i.paid);
    const tab = (id, label, extra = "") => {
      const active = this._tab === id && this._view.name === "overview";
      return html`<button class="pill ${active ? "active" : ""}" data-action="tab" data-tab="${id}"
        aria-current="${active ? "page" : "false"}">${label}${extra}</button>`;
    };
    return html`${tab("today", t(L, "tab_today"))}${tab(
      "payouts",
      t(L, "tab_payouts"),
      due ? html`<span class="dot" role="img" aria-label="!"></span>` : "",
    )}${tab("admin", t(L, "tab_admin"))}${tab("log", t(L, "tab_log"))}`;
  }

  _dayHeader() {
    const L = this._lang;
    const { today, day } = this._state;
    const nav = dayNav(today, day);
    const arrow = (target, label, name) =>
      html`<button class="icon-btn" data-action="day" data-day="${target ?? ""}" aria-label="${t(L, label)}"
        ${target ? "" : raw("disabled")}>${icon(name)}</button>`;
    const back = day !== today ? html`<button class="pill" data-action="day" data-day="">${t(L, "today")}</button>` : "";
    return html`${arrow(nav.prev, "prev_day", "mdi:chevron-left")}<span class="text ${day === today ? "" : "other-day"}"
        >${formatDay(day, L)}</span
      >${arrow(nav.next, "next_day", "mdi:chevron-right")}${back}`;
  }

  _kidName(id) {
    return this._state.kids.find((k) => k.id === id)?.name ?? (this._admin?.kids.find((k) => k.id === id)?.name ?? "");
  }

  _loading() {
    return html`<p class="empty">${t(this._lang, "loading")}</p>`;
  }

  _renderOverview() {
    const s = this._state;
    const L = this._lang;
    if (!s.kids.length) return html`<p class="empty">${t(L, "no_kids")}</p>`;
    const closed = s.week_status === "closed" ? html`<p class="warn">${t(L, "week_closed")}</p>` : "";
    const cols = s.kids.map((kid) => {
      const data = s.board[String(kid.id)] ?? { chores: [], bonus: [], balances: {} };
      const groups = groupBySlot(data.chores).map(
        (g) => html`<div class="slot">${t(L, g.slot)}</div>${g.items.map((i) => this._choreRow(i))}`,
      );
      const bonus = data.bonus.length
        ? html`<div class="bonus"><div class="slot">${t(L, "bonus")}</div>${data.bonus.map((i) => this._choreRow(i))}</div>`
        : "";
      const empty = !data.chores.length && !data.bonus.length;
      const adjust = this._parent
        ? html`<button class="icon-btn" data-action="adjust" data-kid="${kid.id}"
            aria-label="${t(L, "adjust_for", { name: kid.name })}">${icon("mdi:plus-minus-variant")}</button>`
        : "";
      return html`<section class="kid">
        <div class="kid-head">
          <button class="kid-name" data-action="kid" data-kid="${kid.id}" aria-label="${t(L, "open_week_of", { name: kid.name })}"
            >${kid.name}${icon("mdi:chevron-right")}</button
          >${adjust}
        </div>
        ${this._meters(data.balances)} ${groups}${bonus} ${empty ? html`<p class="empty">${t(L, "no_chores")}</p>` : ""}
      </section>`;
    });
    return html`${closed}<div class="columns" style="--cols: ${s.kids.length}">${cols}</div>`;
  }

  _choreRow(inst) {
    // Kids can tick or untick any day of the open week (D8); future days are a preview.
    // Parents also get a ⋯ menu and see a warning icon on ticks made after the chore's day.
    const L = this._lang;
    const open = this._state.week_status === "open";
    const tappable = open && kidTap(inst, this._state.today) !== null;
    const late =
      this._parent && inst.late
        ? html`<span class="late" title="${t(L, "late_hint")}" role="img" aria-label="${t(L, "late_hint")}"
            >${icon("mdi:alert")}</span
          >`
        : "";
    const more =
      this._parent && parentActions(inst, this._state.today).length
        ? html`<button class="icon-btn" data-action="more" data-id="${inst.id}"
            aria-label="${t(L, "more_actions", { name: inst.name })}">${icon("mdi:dots-vertical")}</button>`
        : "";
    const box = inst.status === "pending" ? "" : cellSymbol(inst.status);
    const earned = this._earnedTag(inst);
    return html`<div class="row">
      <button class="chore ${inst.status}" data-action="toggle" data-id="${inst.id}" role="checkbox"
        aria-checked="${inst.status === "done" ? "true" : "false"}" ${tappable ? "" : raw("disabled")}>
        <span class="box" aria-hidden="true">${box}</span><span>${inst.name}</span>${earned}${late}
      </button>${more}
    </div>`;
  }

  /** "+10 min" on a done extra chore: the currency the kid picked (D49). */
  _earnedTag(inst) {
    if (inst.type !== "bonus" || inst.status !== "done" || inst.currency_id == null) return "";
    const c = this._state.currencies.find((x) => x.id === inst.currency_id);
    const value = inst.values?.[String(inst.currency_id)];
    return c && value ? html`<span class="earned">+${formatAmount(value, c, this._lang)}</span>` : "";
  }

  _meters(balances) {
    return this._state.currencies.map((c) => {
      const b = progress(balances?.[String(c.id)]);
      const lost =
        c.can_be_lost && b.lost
          ? html`<span class="lost">${t(this._lang, "lost", { n: formatNumber(b.lost, c.decimals ?? 0, this._lang) })}</span>`
          : "";
      const bar =
        b.pct === null
          ? ""
          : html`<div class="bar" role="progressbar" aria-valuemin="0" aria-valuemax="${b.cap}" aria-valuenow="${b.total}"
              aria-label="${c.name}"><div class="fill" style="width:${b.pct}%"></div></div>`;
      return html`<div class="meter">
        <div class="meter-label">${icon(c.icon || "mdi:star")} ${c.name} ${lost}<span class="amount"
            >${amountLabel(b, c, this._lang)}</span
          ></div>
        ${bar}
      </div>`;
    });
  }

  _renderWeek() {
    const L = this._lang;
    const w = this._week;
    if (!w) return this._loading();
    const today = this._state.today;
    // Today's cells come from the day's board; past cells from the grid (D34, D8).
    const kidBoard = this._state.board[String(this._view.kidId)] ?? { chores: [], bonus: [] };
    const todayByChore = new Map([...kidBoard.chores, ...kidBoard.bonus].map((i) => [i.chore_id, i]));
    const open = w.week_status === "open";
    const head = w.days.map(
      (d) => html`<th class="${d === today ? "today" : ""}" scope="col" aria-label="${shortDay(d, L)}">${weekdayLetter(d, L)}</th>`,
    );
    const rows = w.rows.map((r) => {
      const cells = w.days.map((d) => {
        const status = r.cells[d];
        const cls = `cell ${status ?? ""} ${d === today ? "today" : ""}`;
        const label = t(L, "cell_label", { name: r.name, day: shortDay(d, L), status: t(L, `st_${status ?? "none"}`) });
        const late = this._parent && r.late?.[d] ? html`<span class="late">${icon("mdi:alert")}</span>` : "";
        const todays = d === today ? todayByChore.get(r.chore_id) : null;
        const id = todays?.id ?? r.ids?.[d];
        const inst = todays ?? (id ? { id, day: d, status, type: r.type } : null);
        let action = null;
        if (inst && open && d === today && kidTap(inst, today)) action = html`data-action="toggle" data-confirm="1"`;
        else if (inst && open && d < today && this._parent) action = html`data-action="more"`;
        else if (inst && open && d < today && kidTap(inst, today)) action = html`data-action="toggle"`;
        const symbol = cellSymbol(inst?.status ?? status);
        if (action) {
          return html`<td class="${cls}"><button ${action} data-id="${id}" data-day="${d}" aria-label="${label}">
              ${symbol}${late}</button></td>`;
        }
        return html`<td class="${cls}" aria-label="${label}">${status ? symbol : ""}${late}</td>`;
      });
      const name = r.type === "bonus" ? `${t(L, "bonus")}: ${r.name}` : r.name;
      return html`<tr class="${r.type === "bonus" ? "bonus-row" : ""}"><th scope="row">${name}</th>${cells}</tr>`;
    });
    return html`<div class="week-meters">${this._meters(w.balances)}</div>
      <table class="week"><thead><tr><td></td>${head}</tr></thead><tbody>${rows}</tbody></table>`;
  }

  _renderPayouts() {
    const L = this._lang;
    const p = this._payouts;
    if (!p) return this._loading();
    const s = this._state;
    const currentWeek = mondayOf(s.today);
    const prevWeek = addDays(p.week, -7);
    const nextWeek = p.week < currentWeek ? addDays(p.week, 7) : null;
    const weekButton =
      p.week !== currentWeek
        ? ""
        : p.week_status === "closed"
          ? html`<button class="small-btn" data-action="reopen-week">${t(L, "reopen_week")}</button>`
          : html`<button class="small-btn" data-action="close-week">${t(L, "close_week")}</button>`;
    const weekNav = html`<div class="card"><h2>
      <button class="icon-btn" data-action="payout-week" data-week="${prevWeek}" aria-label="${t(L, "prev_week")}"
        >${icon("mdi:chevron-left")}</button>
      <span class="grow">${t(L, "week", { n: isoWeek(p.week) })}${
        p.week_status === "closed" ? html` · <span class="muted">${t(L, "week_closed")}</span>` : ""
      }</span>
      ${
        nextWeek
          ? html`<button class="icon-btn" data-action="payout-week" data-week="${nextWeek === currentWeek ? "" : nextWeek}"
              aria-label="${t(L, "next_week")}">${icon("mdi:chevron-right")}</button>`
          : ""
      }
      ${weekButton}</h2></div>`;
    const cards = s.currencies.map((c) => {
      const items = p.items.filter((i) => i.currency_id === c.id);
      if (!items.length) return "";
      const amount = (n) => formatAmount(n, c, L);
      const rows = items.map((i) => {
        const paid = i.paid
          ? html`${t(L, "paid", { amount: amount(i.paid.amount) })}${
              i.after_payout ? html` <span class="warn">${t(L, "after_payout", { amount: amount(i.after_payout) })}</span>` : ""
            }`
          : "";
        const pay = html`<button class="${i.paid ? "small-btn" : "primary-btn"}" data-action="pay" data-kid="${i.kid_id}"
          data-currency="${c.id}" data-paid="${i.paid ? "0" : "1"}">${t(L, i.paid ? "undo" : "mark_paid")}</button>`;
        return html`<tr><td>${this._kidName(i.kid_id)}</td><td class="num">${amount(i.amount_due)}</td><td>${paid}</td>
          <td class="actions"><button class="small-btn" data-action="details" data-kid="${i.kid_id}">${t(L, "details")}</button>
          ${pay}</td></tr>`;
      });
      const today = items[0].is_payout_day ? html` · <b>${t(L, "payout_today")}</b>` : "";
      return html`<div class="card"><h2>${icon(c.icon || "mdi:star")}<span class="grow">${c.name}</span>
        <span class="muted">${t(L, "payout_day", { day: formatDay(items[0].payout_day, L) })}${today}</span></h2>
        <table class="list"><tr class="muted"><th></th><th class="num">${t(L, "amount_due")}</th><th></th><th></th></tr>${rows}</table></div>`;
    });
    const adjustments = p.adjustments.length
      ? html`<div class="card"><h2>${t(L, "adjustments")}</h2><table class="list">${p.adjustments.map((a) => {
          const cur = s.currencies.find((c) => c.id === a.currency_id);
          return html`<tr><td>${this._kidName(a.kid_id)}</td><td class="num">${a.amount > 0 ? "+" : ""}${formatAmount(
            a.amount,
            cur,
            L,
          )}</td><td>${a.note}</td><td class="muted">${formatTimestamp(a.created_at, L)}</td></tr>`;
        })}</table></div>`
      : "";
    return html`${weekNav}${cards}${adjustments}`;
  }

  _renderAdmin() {
    const L = this._lang;
    const a = this._admin;
    if (!a) return this._loading();
    const inactive = (x) => (x.active ? "" : html` <span class="muted">(${t(L, "inactive")})</span>`);
    const section = (title, action, rows) => html`<div class="card"><h2><span class="grow">${title}</span>
        <button class="small-btn" data-action="${action}">+ ${t(L, "new")}</button></h2>
        <table class="list">${rows}</table></div>`;
    const editBtn = (action, id) =>
      html`<td class="actions"><button class="small-btn" data-action="${action}" data-id="${id}">${t(L, "edit")}</button></td>`;
    const kids = a.kids.map((k) => html`<tr><td>${k.name}${inactive(k)}</td>${editBtn("edit-kid", k.id)}</tr>`);
    const chores = a.chores.map((c) => {
      const days = c.weekdays.length ? c.weekdays.map((d) => weekdayName(d, L).slice(0, 3)).join(" ") : t(L, "every_day");
      const values = Object.entries(c.values)
        .map(([cid, v]) => formatAmount(v, a.currencies.find((x) => x.id === Number(cid)), L))
        .join(", ");
      const who = c.kid_ids.map((id) => this._kidName(id)).join(", ");
      return html`<tr><td>${c.name}${inactive(c)}<br /><span class="muted"
          >${t(L, c.chore_type)} · ${t(L, c.slot)} · ${days} · ${who}</span
        ></td><td class="num">${values}</td>${editBtn("edit-chore", c.id)}</tr>`;
    });
    const currencies = a.currencies.map(
      (c) => html`<tr><td>${c.name} (${c.unit})${inactive(c)}<br /><span class="muted"
          >${t(L, `cap_${c.cap_mode}`)} · ${weekdayName(c.payout_weekday, L)}</span
        ></td>${editBtn("edit-currency", c.id)}</tr>`,
    );
    return html`<div class="columns" style="--cols: 2">
      <div>${section(t(L, "kids"), "edit-kid", kids)}${section(t(L, "currencies"), "edit-currency", currencies)}
        <div class="card"><h2><span class="grow">${t(L, "settings")}</span>
          <button class="small-btn" data-action="edit-settings">${t(L, "edit")}</button></h2></div></div>
      <div>${section(t(L, "chores"), "edit-chore", chores)}</div></div>`;
  }

  _renderLog() {
    const L = this._lang;
    const s = this._state;
    const f = this._logFilter;
    const kidOpts = [html`<option value="">${t(L, "log_all_kids")}</option>`].concat(
      s.kids.map((k) => html`<option value="${k.id}" ${f.kidId === k.id ? raw("selected") : ""}>${k.name}</option>`),
    );
    const groupOpts = Object.keys(LOG_GROUPS).map(
      (g) => html`<option value="${g}" ${f.group === g ? raw("selected") : ""}>${t(L, `g_${g}`)}</option>`,
    );
    const current = mondayOf(s.today);
    const prev = addDays(f.week ?? addDays(current, 7), -7);
    const next = f.week && f.week < current ? addDays(f.week, 7) : null;
    const filters = html`<div class="card filters">
      <select data-filter="kid" aria-label="${t(L, "kids")}">${kidOpts}</select>
      <select data-filter="group" aria-label="${t(L, "log_event")}">${groupOpts}</select>
      <label class="check"><input type="checkbox" data-filter="late" ${f.late ? raw("checked") : ""} /> ${t(
        L,
        "log_late_only",
      )}</label>
      <span class="grow"></span>
      <button class="icon-btn" data-action="log-week" data-week="${prev}" aria-label="${t(L, "prev_week")}">
        ${icon("mdi:chevron-left")}</button>
      <span>${f.week ? t(L, "week", { n: isoWeek(f.week) }) : t(L, "log_all_weeks")}</span>
      <button class="icon-btn" data-action="log-week" data-week="${next ?? ""}" aria-label="${t(L, "next_week")}"
        ${f.week ? "" : raw("disabled")}>${icon("mdi:chevron-right")}</button>
    </div>`;
    if (!this._log) return html`${filters}${this._loading()}`;
    if (!this._log.length) return html`${filters}<p class="empty">${t(L, "log_empty")}</p>`;
    const rows = this._log.map((e) => {
      let after = null;
      try {
        after = e.after ? JSON.parse(e.after) : null;
      } catch {
        after = null;
      }
      let what = "";
      if (e.action === "check" || e.action === "uncheck") what = after?.chore ?? "";
      else if (after?.chore) what = `${after.chore} → ${t(L, `act_${after.status}`)}`;
      else if (after?.name) what = after.name;
      else if (after?.amount !== undefined && after?.amount !== null) {
        what = formatAmount(after.amount, this._currency(after.currency_id), L);
      }
      const day = e.day && e.entity === "instance" ? shortDay(e.day, L) : "";
      const late = e.late
        ? html`<span class="late" role="img" aria-label="${t(L, "late_hint")}">${icon("mdi:alert")}</span>`
        : "";
      return html`<tr class="${e.late ? "late-row" : ""}"><td class="muted">${formatTimestamp(e.ts, L)}</td>
        <td>${this._kidName(e.kid_id)}</td><td>${t(L, `a_${e.action}`)}</td><td>${what}</td><td>${day} ${late}</td>
        <td class="muted">${e.note ?? ""}</td></tr>`;
    });
    const head = html`<tr class="muted"><th>${t(L, "log_when")}</th><th>${t(L, "kids")}</th><th>${t(L, "log_event")}</th>
      <th>${t(L, "log_what")}</th><th>${t(L, "log_day")}</th><th>${t(L, "note")}</th></tr>`;
    return html`${filters}<div class="card"><table class="list">${head}${rows}</table></div>`;
  }

  // --- dialogs (native <dialog>: focus trap, Escape, inert background) -------------

  _dialogState(kind) {
    return {
      form: this._form,
      sheet: this._sheet,
      confirm: this._dialog,
      pin: this._pin !== null ? this._pin : null,
      clean: this._cleanHands && !this._form && this._pin === null ? true : null,
    }[kind];
  }

  _syncDialogs() {
    for (const kind of DIALOG_KINDS) {
      const state = this._dialogState(kind);
      let el = this._dialogEls[kind];
      if (state === null || state === undefined || state === false) {
        if (el) {
          el.close?.();
          el.remove();
          delete this._dialogEls[kind];
        }
        continue;
      }
      const fresh = !el;
      if (fresh) {
        el = document.createElement("dialog");
        el.className = `dialog ${kind === "clean" ? "clean-hands" : ""}`;
        el.setAttribute("aria-labelledby", `dlg-${kind}-title`);
        el.addEventListener("cancel", (ev) => {
          ev.preventDefault(); // Escape: close through our own state
          this._dismiss(kind);
        });
        if (kind === "pin") el.addEventListener("keydown", (ev) => this._pinKey(ev));
        if (kind === "form") {
          el.addEventListener("submit", (ev) => ev.preventDefault());
          el.addEventListener("keydown", (ev) => {
            if (ev.key === "Enter" && ev.target.tagName === "INPUT" && ev.target.type !== "checkbox") {
              ev.preventDefault();
              this._saveForm();
            }
          });
        }
        this._els.dialogs.append(el);
        this._dialogEls[kind] = el;
      }
      // Forms are rendered once (typed input must survive); the others are cheap to redraw.
      if (fresh || kind !== "form") el.innerHTML = String(this._renderDialog(kind));
      if (fresh && kind === "form") this._fillForm();
      if (!el.open) {
        if (typeof el.showModal === "function") el.showModal();
        else el.setAttribute("open", "");
      }
    }
  }

  _dismiss(kind) {
    if (kind === "form") this._form = null;
    if (kind === "sheet") this._sheet = null;
    if (kind === "confirm") this._dialog = null;
    if (kind === "pin") this._pin = null;
    if (kind === "clean") this._cleanHands = false;
    this._render();
  }

  _renderDialog(kind) {
    const L = this._lang;
    const title = (text) => html`<h3 id="dlg-${kind}-title">${text}</h3>`;
    if (kind === "confirm") {
      return html`${title(this._dialog.text)}
        <div class="actions">
          <button data-action="dialog-cancel">${t(L, "cancel")}</button>
          <button class="primary" data-action="dialog-yes" autofocus>${t(L, "yes")}</button>
        </div>`;
    }
    if (kind === "sheet") {
      return html`${title(this._sheet.title)}
        <div class="sheet">
          ${this._sheet.items.map((item, i) => html`<button data-action="sheet-item" data-index="${i}">${item.label}</button>`)}
          <button data-action="sheet-close">${t(L, "cancel")}</button>
        </div>`;
    }
    if (kind === "pin") {
      const keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9"].map(
        (d) => html`<button data-action="pin-digit" data-digit="${d}">${d}</button>`,
      );
      return html`<div class="pinpad">${title(t(L, "enter_pin"))}
        <div class="pin-dots" aria-live="polite">${"●".repeat(this._pin.length) || raw("&nbsp;")}</div>
        <div class="keys">${keys}
          <button data-action="pin-back" aria-label="${t(L, "backspace")}">${icon("mdi:backspace-outline")}</button>
          <button data-action="pin-digit" data-digit="0">0</button>
          <button data-action="pin-ok" autofocus>OK</button>
        </div>
        <div class="actions"><button data-action="pin-cancel">${t(L, "cancel")}</button></div></div>`;
    }
    if (kind === "clean") {
      const text = this._state?.settings?.clean_hands_text || t(L, "clean_hands");
      return html`<button data-action="clean-hands" autofocus>
        ${icon("mdi:hand-wash")}<span id="dlg-clean-title">${text}</span><small>${t(L, "tap_to_continue")}</small>
      </button>`;
    }
    return this._renderForm();
  }

  _renderForm() {
    const L = this._lang;
    const f = this._form;
    const fields = f.fields.map((field) => {
      const id = `f-${field.key}`;
      if (field.type === "bool") {
        return html`<div class="field"><label class="check"><input type="checkbox" id="${id}" name="${field.key}" />
          ${field.label}</label></div>`;
      }
      if (field.type === "select") {
        const opts = field.options.map(([v, label]) => html`<option value="${v}">${label}</option>`);
        return html`<div class="field"><label for="${id}">${field.label}</label>
          <select id="${id}" name="${field.key}">${opts}</select></div>`;
      }
      if (field.type === "multi") {
        const chips = field.options.map(
          ([v, label]) => html`<label><input type="checkbox" name="${field.key}" value="${v}" />${label}</label>`,
        );
        return html`<fieldset><legend>${field.label}</legend><div class="chips">${chips}</div></fieldset>`;
      }
      const type = field.type === "number" ? "number" : "text";
      const mode = { number: "numeric", amount: "decimal" }[field.type];
      return html`<div class="field"><label for="${id}">${field.label}</label>
        <input type="${type}" id="${id}" name="${field.key}" ${mode ? raw(`inputmode="${mode}"`) : ""} /></div>`;
    });
    return html`<h3 id="dlg-form-title">${f.title}</h3>
      <form class="form" novalidate>${fields}
        <div class="actions">
          ${f.onDelete ? html`<button type="button" class="danger" data-action="form-delete">${t(L, "delete")}</button>` : ""}
          <button type="button" data-action="form-cancel">${t(L, "cancel")}</button>
          <button type="button" class="primary" data-action="form-save">${t(L, "save")}</button>
        </div>
      </form>`;
  }

  /** Put the form's current values into its freshly rendered inputs. */
  _fillForm() {
    const root = this._formEl();
    for (const field of this._form.fields) {
      const value = this._form.values[field.key];
      if (field.type === "bool") {
        root.querySelector(`[name="${field.key}"]`).checked = Boolean(value);
      } else if (field.type === "multi") {
        const set = new Set((value ?? []).map(Number));
        for (const input of root.querySelectorAll(`[name="${field.key}"]`)) input.checked = set.has(Number(input.value));
      } else if (field.type === "amount" && value !== undefined && value !== null) {
        const decimals = this._fieldDecimals(field, this._form.values);
        root.querySelector(`[name="${field.key}"]`).value = formatNumber(value, decimals, this._lang);
      } else if (value !== undefined && value !== null) {
        root.querySelector(`[name="${field.key}"]`).value = String(value);
      }
    }
  }
}

/** A selector that finds "the same" control after a re-render (for focus restore). */
function focusKey(el) {
  const attrs = ["action", "id", "day", "kid", "tab", "filter", "currency", "week"]
    .filter((a) => el.dataset?.[a] !== undefined)
    .map((a) => `[data-${a}="${globalThis.CSS?.escape?.(el.dataset[a]) ?? el.dataset[a]}"]`);
  return attrs.length ? attrs.join("") : null;
}

if (globalThis.customElements && !customElements.get("chores-and-rewards-panel")) {
  customElements.define("chores-and-rewards-panel", ChoresPanel);
}
