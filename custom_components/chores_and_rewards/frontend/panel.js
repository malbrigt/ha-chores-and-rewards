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
    yes: "Ja",
    cancel: "Avbryt",
    error_not_today: "Det kan bare endres samme dag.",
    error_week_closed: "Uka er avsluttet.",
    error_not_allowed: "Det er ikke lov.",
    error_not_found: "Fant ikke gjøremålet.",
    error_generic: "Noe gikk galt. Prøv igjen.",
  },
  en: {
    morning: "Morning",
    afternoon: "Afternoon",
    anytime: "Anytime",
    bonus: "Extra",
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
    yes: "Yes",
    cancel: "Cancel",
    error_not_today: "This can only be changed on the same day.",
    error_week_closed: "The week is closed.",
    error_not_allowed: "That is not allowed.",
    error_not_found: "Chore not found.",
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

const LOCALE = { nb: "nb-NO", en: "en-GB" };

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

/** One-letter weekday for the week grid header. */
export function weekdayLetter(dateStr, lang) {
  const d = new Date(`${dateStr}T12:00:00Z`);
  return new Intl.DateTimeFormat(LOCALE[lang], { weekday: "narrow", timeZone: "UTC" })
    .format(d)
    .toUpperCase();
}

/** Value with unit, e.g. "40/60 min" or "40 kr" when uncapped. */
export function amountLabel({ total, cap }, unit) {
  return cap ? `${total}/${cap} ${unit}` : `${total} ${unit}`;
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
    height: 56px;
    padding: 0 16px;
    background: var(--app-header-background-color, var(--primary-color));
    color: var(--app-header-text-color, var(--text-primary-color, #fff));
    font-size: 1.3rem;
  }
  header .title { flex: 1; display: flex; align-items: center; gap: 8px; }
  header .nav { font-size: 1.8rem; width: 44px; height: 44px; text-align: center; }
  header .nav[disabled] { opacity: 0.3; }
  header .today-btn {
    margin-left: 12px;
    padding: 4px 12px;
    border: 1px solid currentColor;
    border-radius: 16px;
    font-size: 1rem;
  }
  header .other-day { font-style: italic; }
  header button { color: inherit; }
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
  .kid {
    background: var(--card-background-color);
    border-radius: var(--ha-card-border-radius, 12px);
    padding: 12px 14px 16px;
    box-shadow: var(--ha-card-box-shadow, none);
    border: 1px solid var(--divider-color);
  }
  .kid-name {
    width: 100%;
    font-size: 1.5rem;
    font-weight: 600;
    padding: 4px 0 8px;
  }
  .kid-name::after { content: " ›"; color: var(--secondary-text-color); }
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
  .chore {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    min-height: 56px;
    font-size: 1.15rem;
    border-bottom: 1px solid var(--divider-color);
  }
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
  .week-meters { display: flex; flex-wrap: wrap; gap: 8px 32px; margin-bottom: 12px; }
  .week-meters .meter { flex: 1 1 260px; }
  table.week {
    width: 100%;
    border-collapse: collapse;
    background: var(--card-background-color);
    border-radius: var(--ha-card-border-radius, 12px);
    overflow: hidden;
    font-size: 1.1rem;
  }
  table.week th, table.week td {
    border-bottom: 1px solid var(--divider-color);
    padding: 10px 6px;
    text-align: center;
  }
  table.week th:first-child, table.week td:first-child { text-align: left; padding-left: 14px; }
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
    max-width: 80vw;
    font-size: 1.3rem;
  }
  .dialog .actions { display: flex; justify-content: flex-end; gap: 12px; margin-top: 24px; }
  .dialog .actions button {
    padding: 12px 24px;
    border-radius: 10px;
    font-size: 1.1rem;
    border: 1px solid var(--divider-color);
  }
  .dialog .actions .primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border: none; }
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
    this._dialog = null; // {text, onYes}
    this._toast = null;
    this._cleanHands = false;
    this._lastActivity = Date.now();
    this._onActivity = () => {
      this._lastActivity = Date.now();
    };
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
    }
    for (const type of ["pointerdown", "keydown"]) {
      window.addEventListener(type, this._onActivity, { capture: true });
    }
    this._idleTimer = setInterval(() => this._checkIdle(), 2000);
    this._render();
    if (this._hass) this._connect();
  }

  disconnectedCallback() {
    for (const type of ["pointerdown", "keydown"]) {
      window.removeEventListener(type, this._onActivity, { capture: true });
    }
    clearInterval(this._idleTimer);
    this._unsubscribe?.then((unsub) => unsub()).catch(() => {});
    this._unsubscribe = null;
  }

  // --- data ---------------------------------------------------------------------

  _ws(type, data = {}) {
    return this._hass.connection.sendMessagePromise({ type: P + type, ...data });
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
    } catch (err) {
      this._showError(err);
    }
    this._render();
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

  _todayInstance(id) {
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

  // --- interaction ----------------------------------------------------------------

  _onClick(ev) {
    const el = ev.composedPath().find((n) => n.dataset?.action);
    if (!el) return;
    const { action } = el.dataset;
    if (action === "clean-hands") {
      this._cleanHands = false;
    } else if (action === "kid") {
      this._openWeek(Number(el.dataset.kid));
      return;
    } else if (action === "day") {
      this._goDay(el.dataset.day || null);
      return;
    } else if (action === "back") {
      this._view = { name: "overview" };
      this._week = null;
    } else if (action === "toggle") {
      this._toggle(Number(el.dataset.id), el.dataset.confirm === "1");
      return;
    } else if (action === "dialog-yes") {
      const { onYes } = this._dialog;
      this._dialog = null;
      onYes();
    } else if (action === "dialog-cancel") {
      this._dialog = null;
    }
    this._render();
  }

  _toggle(id, alwaysConfirm) {
    const inst = this._todayInstance(id);
    if (!inst) return;
    const done = inst.status !== "done";
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
    this._render();
  }

  _checkIdle() {
    const settings = this._state?.settings;
    if (!settings) return;
    const idle = Date.now() - this._lastActivity;
    let changed = false;
    if ((this._view.name !== "overview" || this._day) && idle > settings.idle_seconds * 1000) {
      this._view = { name: "overview" };
      this._day = null;
      this._scheduleReload();
      this._week = null;
      this._dialog = null;
      changed = true;
    }
    if (settings.clean_hands_enabled && !this._cleanHands && idle > settings.wake_seconds * 1000) {
      this._cleanHands = true;
      changed = true;
    }
    if (changed) this._render();
  }

  _showError(err) {
    this._toast = errorText(this._lang, err?.code);
    this._render();
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => {
      this._toast = null;
      this._render();
    }, 4000);
  }

  // --- rendering -------------------------------------------------------------------

  _syncMenuButton() {
    const button = this.shadowRoot?.querySelector("ha-menu-button");
    if (button) {
      button.hass = this._hass;
      button.narrow = this._narrow;
    }
  }

  _render() {
    if (!this.shadowRoot) return;
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
      } else {
        title = this._dayHeader();
        body = this._renderOverview();
      }
    }
    const back =
      this._view.name === "week"
        ? `<button data-action="back" aria-label="${t(L, "back")}">←</button>`
        : "";
    this.shadowRoot.innerHTML = `
      <style>${STYLES}</style>
      <header><ha-menu-button></ha-menu-button>${back}<span class="title">${title}</span></header>
      <main>${body}</main>
      ${this._renderDialog()}
      ${this._cleanHands ? this._renderCleanHands() : ""}
      ${this._toast ? `<div class="toast">${escapeHtml(this._toast)}</div>` : ""}`;
    this._syncMenuButton();
  }

  _dayHeader() {
    const L = this._lang;
    const { today, day } = this._state;
    const nav = dayNav(today, day);
    const arrow = (target, label, text) =>
      `<button class="nav" data-action="day" data-day="${target ?? ""}" aria-label="${t(L, label)}"
        ${target ? "" : "disabled"}>${text}</button>`;
    const back = day !== today ? `<button class="today-btn" data-action="day" data-day="">${t(L, "today")}</button>` : "";
    return `${arrow(nav.prev, "prev_day", "‹")}<span class="${day === today ? "" : "other-day"}">${escapeHtml(
      formatDay(day, L),
    )}</span>${arrow(nav.next, "next_day", "›")}${back}`;
  }

  _renderOverview() {
    const s = this._state;
    const L = this._lang;
    if (!s.kids.length) return `<p class="empty">${t(L, "no_kids")}</p>`;
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
        return `<section class="kid">
          <button class="kid-name" data-action="kid" data-kid="${kid.id}">${escapeHtml(kid.name)}</button>
          ${this._meters(data.balances)}
          ${groups}${bonus}
          ${empty ? `<p class="empty">${t(L, "no_chores")}</p>` : ""}
        </section>`;
      })
      .join("");
    return `<div class="columns" style="grid-template-columns: repeat(${s.kids.length}, minmax(0, 1fr))">${cols}</div>`;
  }

  _choreRow(inst) {
    // Kids can only change today (D8); other days are read-only (parents: step 9).
    const isToday = this._state.day === this._state.today;
    const tappable = isToday && inst.id && (inst.status === "done" || inst.status === "pending");
    return `<button class="chore ${inst.status}" data-action="toggle" data-id="${inst.id}"
      ${tappable ? "" : "disabled"}><span class="box">${inst.status === "pending" ? "" : cellSymbol(inst.status)}</span>
      <span>${escapeHtml(inst.name)}</span></button>`;
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
            const inst = d === today ? todayByChore.get(r.chore_id) : null;
            if (inst && (inst.status === "pending" || inst.status === "done")) {
              return `<td class="${cls}"><button data-action="toggle" data-confirm="1" data-id="${inst.id}">${cellSymbol(
                inst.status,
              )}</button></td>`;
            }
            return `<td class="${cls}">${status ? cellSymbol(status) : ""}</td>`;
          })
          .join("");
        const label = r.type === "bonus" ? `${t(L, "bonus")}: ${escapeHtml(r.name)}` : escapeHtml(r.name);
        return `<tr class="${r.type === "bonus" ? "bonus-row" : ""}"><td>${label}</td>${cells}</tr>`;
      })
      .join("");
    return `<div class="week-meters">${this._meters(w.balances)}</div>
      <table class="week"><thead><tr><th></th>${head}</tr></thead><tbody>${rows}</tbody></table>`;
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
