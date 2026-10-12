// Render smoke test: drives the real panel element in happy-dom against a fake HA
// connection. Run with script/smoke (installs happy-dom in a throwaway location).
import assert from "node:assert/strict";
import { after, test } from "node:test";

import { Window } from "happy-dom";

const window = new Window({ url: "http://localhost:8123/" });
for (const key of ["window", "document", "HTMLElement", "customElements", "Event", "Node"]) {
  globalThis[key] = key === "window" ? window : window[key];
}
globalThis.window.addEventListener = window.addEventListener.bind(window);

const { ChoresPanel } = await import("../../custom_components/chores_and_rewards/frontend/panel.js");

const TODAY = "2026-10-09";
const inst = (id, kid, name, slot, type = "expected", status = "pending") => ({
  id, kid_id: kid, chore_id: id, day: TODAY, type, slot, name, icon: "", values: { 1: 10 },
  status, status_at: status === "done" ? "2026-10-09T08:00:00+00:00" : null,
});
const balance = { earned: 10, lost: 0, adjustments: 0, cap: 60, total: 10 };
const STATE = {
  today: TODAY, day: TODAY, week: "2026-10-05", week_status: "open", is_preview: false,
  kids: [{ id: 1, name: "Ada", sort: 0, active: true }, { id: 2, name: "Bo", sort: 1, active: true }],
  currencies: [{ id: 1, name: "Skjermtid", unit: "min", icon: "mdi:tablet", payout_weekday: 4,
    can_be_lost: true, cap_mode: "fixed", default_max: 60, active: true, sort: 0 }],
  settings: { clean_hands_enabled: true, clean_hands_text: "", idle_seconds: 60, wake_seconds: 300,
    pin_timeout_seconds: 300 },
  board: {
    1: { chores: [inst(1, 1, "Re opp sengen", "morning", "expected", "done"), inst(2, 1, "Dekke bordet", "afternoon")],
         bonus: [inst(3, 1, "Vaske vinduer", "anytime", "bonus")], balances: { 1: balance } },
    2: { chores: [inst(4, 2, "Oppvask", "afternoon")], bonus: [], balances: { 1: balance } },
  },
};

function fakeHass(state = STATE) {
  const calls = [];
  const replies = {
    get_state: () => structuredClone(state),
    get_week: () => ({ week: "2026-10-05", week_status: "open", days: ["2026-10-05", "2026-10-06",
      "2026-10-07", "2026-10-08", TODAY, "2026-10-10", "2026-10-11"],
      rows: [{ chore_id: 2, name: "Dekke bordet", slot: "afternoon", type: "expected",
        cells: { "2026-10-08": "missed", [TODAY]: "pending" }, ids: { "2026-10-08": 20, [TODAY]: 2 } }],
      balances: { 1: balance } }),
    set_done: (m) => ({ instance: { ...inst(m.instance_id, 1, "x", "afternoon"), status: m.done ? "done" : "pending" } }),
    "pin/unlock": (m) => {
      if (m.pin !== "1234") throw { code: "wrong_pin" };
      return { token: "tok", expires_in: 300 };
    },
    "parent/payouts": () => ({ week: "2026-10-05", week_status: "open", adjustments: [],
      items: [{ kid_id: 1, currency_id: 1, amount_due: 10, paid: null, after_payout: 0,
        payout_day: TODAY, is_payout_day: true }] }),
    "admin/list": () => ({
      kids: [{ id: 1, name: "Ada", sort: 0, active: true, max: { 1: 60 } }],
      currencies: STATE.currencies,
      chores: [],
      settings: STATE.settings,
    }),
    "admin/chore/save": () => ({ id: 9, warnings: [1] }),
    "parent/audit": () => ({
      entries: [{ id: 1, ts: "2026-10-09T19:00:00+00:00", user_id: "u", action: "check", entity: "instance",
        entity_id: "20", before: '{"status": "missed"}', after: '{"status": "done", "chore": "Dekke bordet"}',
        note: null, kid_id: 1, day: "2026-10-08", late: true }],
    }),
    "parent/set_status": (m) => ({ instance: inst(m.instance_id, 1, "x", "afternoon", "expected", m.status) }),
  };
  return {
    calls,
    language: "nb",
    connection: {
      addEventListener() {},
      removeEventListener() {},
      subscribeMessage: async () => () => {},
      sendMessagePromise: async (msg) => {
        calls.push(msg);
        const type = msg.type.replace("chores_and_rewards/", "");
        const reply = replies[type];
        if (!reply) throw { code: "unknown_command" };
        return reply(msg);
      },
    },
  };
}

// Panels keep an idle timer running; detach them all so Node can exit.
const mounted = [];
after(async () => {
  for (const el of mounted) el.remove();
  await window.happyDOM.close();
});

const tick = () => new Promise((r) => setTimeout(r, 200));
const click = (root, selector) => {
  const el = root.querySelector(selector);
  assert.ok(el, `missing ${selector}`);
  el.click();
};

async function mount(state = STATE) {
  // Each test starts with a fresh panel: drop earlier ones, and with them their focus
  // (happy-dom otherwise keeps pointing activeElement at a detached node).
  for (const old of mounted.splice(0)) old.remove();
  document.body.focus?.();
  const hass = fakeHass(state);
  const el = new ChoresPanel();
  el.hass = hass;
  document.body.appendChild(el);
  mounted.push(el);
  await tick();
  return { el, hass, root: el.shadowRoot };
}

test("overview renders kid columns, slots, bonus and meters", async () => {
  const { root } = await mount();
  const text = root.textContent;
  for (const s of ["Fredag 9. okt", "Ada", "Bo", "Morgen", "Ettermiddag", "Ekstra", "Vaske vinduer", "10/60 min"]) {
    assert.ok(text.includes(s), `missing "${s}"`);
  }
  assert.equal(root.querySelectorAll("section.kid").length, 2);
  assert.ok(root.querySelector(".chore.done"));
});

test("tap marks done; recent uncheck needs no confirm, old one does", async () => {
  const { root, hass } = await mount();
  click(root, '[data-action="toggle"][data-id="2"]');
  await tick();
  assert.deepEqual(hass.calls.at(-1), { type: "chores_and_rewards/set_done", instance_id: 2, done: true });
  click(root, '[data-action="toggle"][data-id="1"]'); // ticked long ago → confirm
  await tick();
  assert.ok(root.querySelector(".dialog"), "confirm dialog shown");
  click(root, '[data-action="dialog-yes"]');
  await tick();
  assert.deepEqual(hass.calls.at(-1), { type: "chores_and_rewards/set_done", instance_id: 1, done: false });
});

test("week view opens and today's cell asks to confirm", async () => {
  const { root, hass } = await mount();
  click(root, '[data-action="kid"][data-kid="1"]');
  await tick();
  assert.ok(root.textContent.includes("Uke 41"));
  assert.ok(root.querySelector("table.week"));
  click(root, 'table.week [data-action="toggle"]');
  await tick();
  assert.ok(root.querySelector(".dialog"));
  click(root, '[data-action="back"]');
  await tick();
  assert.ok(root.querySelector("section.kid"));
  assert.ok(hass.calls.some((c) => c.type.endsWith("get_week")));
});

test("PIN pad: wrong PIN shows error, right PIN unlocks tabs and ⋯ menu", async () => {
  const { root, hass } = await mount();
  click(root, '[data-action="lock-toggle"]');
  await tick();
  for (const d of "0000") click(root, `[data-action="pin-digit"][data-digit="${d}"]`);
  click(root, '[data-action="pin-ok"]');
  await tick();
  assert.ok(root.querySelector(".toast")?.textContent.includes("Feil PIN"));
  for (const d of "1234") click(root, `[data-action="pin-digit"][data-digit="${d}"]`);
  click(root, '[data-action="pin-ok"]');
  await tick();
  assert.ok(root.querySelector('[data-tab="payouts"] .dot'), "payout-due dot");
  assert.ok(root.querySelector(".lock.open"), "unlocked lock icon");
  click(root, '[data-action="more"][data-id="1"]');
  await tick();
  const labels = [...root.querySelectorAll('[data-action="sheet-item"]')].map((b) => b.textContent);
  assert.deepEqual(labels, ["Fritatt", "Avvis (teller som ikke gjort)", "Nullstill", "Juster saldo"]);
  click(root, '[data-action="sheet-item"][data-index="1"]');
  await tick();
  const last = hass.calls.find((c) => c.type.endsWith("parent/set_status"));
  assert.deepEqual(last, { type: "chores_and_rewards/parent/set_status", instance_id: 1, status: "rejected", token: "tok" });
});

test("payouts tab lists amount and pay button", async () => {
  const { root, hass } = await mount();
  click(root, '[data-action="lock-toggle"]');
  for (const d of "1234") click(root, `[data-action="pin-digit"][data-digit="${d}"]`);
  click(root, '[data-action="pin-ok"]');
  await tick();
  click(root, '[data-action="tab"][data-tab="payouts"]');
  await tick();
  assert.ok(root.textContent.includes("Skjermtid"));
  assert.ok(root.querySelector('[data-action="pay"][data-paid="1"]'));
  assert.ok(hass.calls.some((c) => c.type.endsWith("parent/payouts") && c.token === "tok"));
});

test("admin: new chore form saves the typed values and shows the payout warning", async () => {
  const { root, hass } = await mount();
  click(root, '[data-action="lock-toggle"]');
  for (const d of "1234") click(root, `[data-action="pin-digit"][data-digit="${d}"]`);
  click(root, '[data-action="pin-ok"]');
  await tick();
  click(root, '[data-action="tab"][data-tab="admin"]');
  await tick();
  click(root, '[data-action="edit-chore"]:not([data-id])');
  await tick();
  const form = root.querySelector("form.form");
  form.querySelector('[name="name"]').value = "Støvsuge";
  form.querySelector('[name="slot"]').value = "morning";
  form.querySelector('[name="weekdays"][value="6"]').checked = true;
  form.querySelector('[name="kid_ids"][value="1"]').checked = true;
  form.querySelector('[name="value_1"]').value = "15";
  // A background reload must not wipe what was typed.
  await root.host._reload();
  assert.equal(root.querySelector('form.form [name="name"]').value, "Støvsuge");
  click(root, '[data-action="form-save"]');
  await tick();
  const save = hass.calls.find((c) => c.type.endsWith("admin/chore/save"));
  assert.equal(save.name, "Støvsuge");
  assert.equal(save.slot, "morning");
  assert.deepEqual(save.weekdays, [6]);
  assert.deepEqual(save.kid_ids, [1]);
  assert.deepEqual(save.values, { 1: 15 });
  assert.equal(save.chore_type, "expected");
  assert.equal(save.once_a_day, false, "once a day is for extras only (D51)");
  assert.ok(root.querySelector(".toast.info")?.textContent.includes("Skjermtid"), "payout warning");
  assert.equal(root.querySelector("form.form"), null, "form closed");
});

test("kid fixes yesterday from the week grid, with a dated confirmation (D8)", async () => {
  const { root, hass } = await mount();
  click(root, '[data-action="kid"][data-kid="1"]');
  await tick();
  click(root, '[data-action="toggle"][data-day="2026-10-08"]');
  await tick();
  assert.match(root.querySelector(".dialog").textContent, /Dekke bordet.*tor/s);
  click(root, '[data-action="dialog-yes"]');
  await tick();
  assert.deepEqual(hass.calls.find((c) => c.type.endsWith("set_done")), {
    type: "chores_and_rewards/set_done",
    instance_id: 20,
    done: true,
  });
});

test("payout Detaljer opens the log filtered on kid, week and review actions (D44)", async () => {
  const { root, hass } = await mount();
  click(root, '[data-action="lock-toggle"]');
  for (const d of "1234") click(root, `[data-action="pin-digit"][data-digit="${d}"]`);
  click(root, '[data-action="pin-ok"]');
  await tick();
  click(root, '[data-action="tab"][data-tab="payouts"]');
  await tick();
  click(root, '[data-action="details"][data-kid="1"]');
  await tick();
  const query = hass.calls.findLast((c) => c.type.endsWith("parent/audit"));
  assert.equal(query.kid_id, 1);
  assert.equal(query.week, "2026-10-05");
  assert.deepEqual(query.actions, ["check", "uncheck", "set_status", "adjust", "payout", "payout_undo"]);
  assert.ok(root.querySelector(".late-row .late"), "late tick flagged");
  assert.equal(root.querySelector('[data-filter="kid"]').value, "1");
  assert.equal(root.querySelector('[data-filter="group"]').value, "review");
});

test("native dialogs: Escape closes, Enter saves a form, focus survives a reload", async () => {
  const { root, hass } = await mount();
  // Escape on the confirm dialog (the browser fires "cancel") closes it via our state.
  click(root, '[data-action="toggle"][data-id="1"]');
  await tick();
  const confirm = root.querySelector("dialog.dialog");
  assert.ok(confirm, "confirm is a native <dialog>");
  confirm.dispatchEvent(new window.Event("cancel", { cancelable: true }));
  await tick();
  assert.equal(root.querySelector("dialog.dialog"), null);

  // Enter in a form input saves.
  click(root, '[data-action="lock-toggle"]');
  for (const d of "1234") click(root, `[data-action="pin-digit"][data-digit="${d}"]`);
  click(root, '[data-action="pin-ok"]');
  await tick();
  click(root, '[data-action="adjust"][data-kid="1"]');
  await tick();
  const form = root.querySelector("form.form");
  form.querySelector('[name="amount"]').value = "5";
  const note = form.querySelector('[name="note"]');
  note.value = "Bonus";
  note.dispatchEvent(new window.KeyboardEvent("keydown", { key: "Enter", bubbles: true, composed: true }));
  await tick();
  assert.ok(hass.calls.some((c) => c.type.endsWith("parent/adjust") && c.amount === 5 && c.note === "Bonus"));

  // A background reload keeps keyboard focus on the same control.
  const kidButton = root.querySelector('[data-action="kid"][data-kid="2"]');
  kidButton.focus();
  await root.host._reload();
  assert.equal(root.activeElement?.dataset.kid, "2");
});

test("extra chore: lost screen time → pick pay or win back; nothing lost → plain tick (D49)", async () => {
  const allowance = { ...STATE.currencies[0], id: 2, name: "Ukepenger", unit: "kr", can_be_lost: false, sort: 1 };
  const state = structuredClone(STATE);
  state.currencies.push(allowance);
  state.board[1].bonus[0].values = { 1: 10, 2: 1 };
  state.board[1].balances = { 1: { ...balance, lost: 10, refilled: 0 }, 2: { ...balance, cap: null } };
  const { root, hass } = await mount(state);
  click(root, '[data-action="toggle"][data-id="3"]');
  await tick();
  const items = [...root.querySelectorAll('[data-action="sheet-item"]')].map((b) => b.textContent.trim());
  assert.deepEqual(items, ["1 kr Ukepenger", "Vinn tilbake 10 min Skjermtid"]);
  click(root, '[data-action="sheet-item"][data-index="1"]');
  await tick();
  assert.deepEqual(hass.calls.at(-1), {
    type: "chores_and_rewards/set_done", instance_id: 3, done: true, currency_id: 1,
  });

  state.board[1].balances[1].refilled = 10; // all won back: only payment is left
  const second = await mount(state);
  click(second.root, '[data-action="toggle"][data-id="3"]');
  await tick();
  assert.equal(second.root.querySelector('[data-action="sheet-item"]'), null);
  assert.deepEqual(second.hass.calls.at(-1), { type: "chores_and_rewards/set_done", instance_id: 3, done: true });
});

test("a once-a-day extra another kid did is greyed out with who took it (AC-6.8, D51)", async () => {
  const state = structuredClone(STATE);
  state.board[2].bonus = [{ ...inst(5, 2, "Vaske vinduer", "anytime", "bonus"), taken_by: 1 }];
  const { root } = await mount(state);
  const row = root.querySelector('[data-action="toggle"][data-id="5"]');
  assert.ok(row.classList.contains("taken"));
  assert.ok(row.hasAttribute("disabled"), "can't be ticked");
  assert.ok(row.textContent.includes("Tatt av Ada"));
});

test("a currency with decimals shows 0,50 and the adjust form sends cents (AC-3.4, D50)", async () => {
  const euro = { ...STATE.currencies[0], id: 2, name: "Euro", unit: "€", can_be_lost: false, decimals: 2, sort: 1 };
  const state = structuredClone(STATE);
  state.currencies.push(euro);
  state.board[1].balances[2] = { earned: 50, lost: 0, refilled: 0, adjustments: 0, cap: 700, total: 50 };
  const { root, hass } = await mount(state);
  assert.ok(root.textContent.includes("0,50/7 €"), "meter in euros");

  click(root, '[data-action="lock-toggle"]');
  for (const d of "1234") click(root, `[data-action="pin-digit"][data-digit="${d}"]`);
  click(root, '[data-action="pin-ok"]');
  await tick();
  click(root, '[data-action="adjust"][data-kid="1"]');
  await tick();
  const form = root.querySelector("form.form");
  form.querySelector('[name="currency_id"]').value = "2";
  form.querySelector('[name="amount"]').value = "1,25";
  form.querySelector('[name="note"]').value = "Bonus";
  click(root, '[data-action="form-save"]');
  await tick();
  const adjust = hass.calls.find((c) => c.type.endsWith("parent/adjust"));
  assert.equal(adjust.currency_id, 2);
  assert.equal(adjust.amount, 125);
});
