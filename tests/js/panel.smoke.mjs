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

function fakeHass() {
  const calls = [];
  const replies = {
    get_state: () => structuredClone(STATE),
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
    "parent/set_status": (m) => ({ instance: inst(m.instance_id, 1, "x", "afternoon", "expected", m.status) }),
  };
  return {
    calls,
    language: "nb",
    connection: {
      addEventListener() {},
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

async function mount() {
  const hass = fakeHass();
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
  assert.ok(root.querySelector(".toast.info")?.textContent.includes("Skjermtid"), "payout warning");
  assert.equal(root.querySelector("form.form"), null, "form closed");
});
