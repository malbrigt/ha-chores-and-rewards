// Pure helpers in frontend/panel.js. Run: node --test tests/js/
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import {
  ChoresPanel,
  STRINGS,
  amountLabel,
  cellSymbol,
  errorText,
  escapeHtml,
  formatDay,
  groupBySlot,
  isoWeek,
  langOf,
  needsUncheckConfirm,
  progress,
  t,
  weekdayLetter,
} from "../../custom_components/chores_and_rewards/frontend/panel.js";

test("imports without a DOM (element defined only in browsers)", () => {
  assert.equal(typeof ChoresPanel, "function");
});

test("langOf: Norwegian variants → nb, else en (AC-8.5)", () => {
  for (const l of ["nb", "nn", "no", "nb-NO"]) assert.equal(langOf(l), "nb");
  for (const l of ["en", "en-GB", "sv", "", undefined]) assert.equal(langOf(l), "en");
});

test("t: vars, fallback to English, then key", () => {
  assert.equal(t("nb", "week", { n: 41 }), "Uke 41");
  assert.equal(t("en", "lost", { n: 10 }), "−10 lost");
  assert.equal(t("xx", "yes"), "Yes");
  assert.equal(t("nb", "nope"), "nope");
});

test("nb and en have the same keys", () => {
  assert.deepEqual(Object.keys(STRINGS.nb).sort(), Object.keys(STRINGS.en).sort());
});

test("errorText maps known codes, else generic", () => {
  assert.equal(errorText("nb", "week_closed"), "Uka er avsluttet.");
  assert.equal(errorText("en", "whatever"), STRINGS.en.error_generic);
  assert.equal(errorText("en", undefined), STRINGS.en.error_generic);
});

test("escapeHtml", () => {
  assert.equal(escapeHtml(`<b a="x">'&`), "&lt;b a=&quot;x&quot;&gt;&#39;&amp;");
  assert.equal(escapeHtml(null), "");
});

test("progress: percentage of cap, null when uncapped (AC-8.2)", () => {
  assert.deepEqual(progress({ total: 40, cap: 60, lost: 10 }), { total: 40, cap: 60, lost: 10, pct: 67 });
  assert.equal(progress({ total: 90, cap: 60 }).pct, 100);
  assert.equal(progress({ total: 5, cap: null }).pct, null);
  assert.equal(progress({ total: 0, cap: 0 }).pct, null);
  assert.equal(progress(undefined).total, 0);
});

test("amountLabel (AC-3.4: decimals per currency)", () => {
  const min = { unit: "min", decimals: 0 };
  const eur = { unit: "€", decimals: 2 };
  assert.equal(amountLabel({ total: 40, cap: 60 }, min, "en"), "40/60 min");
  assert.equal(amountLabel({ total: 40, cap: null }, { unit: "kr" }, "nb"), "40 kr");
  assert.equal(amountLabel({ total: 450, cap: 700 }, eur, "nb"), "4,50/7 €");
  assert.equal(amountLabel({ total: 450, cap: 700 }, eur, "en"), "4.50/7 €");
});

test("isoWeek incl. year boundaries", () => {
  assert.equal(isoWeek("2026-10-09"), 41);
  assert.equal(isoWeek("2026-10-12"), 42);
  assert.equal(isoWeek("2026-12-31"), 53);
  assert.equal(isoWeek("2027-01-03"), 53);
  assert.equal(isoWeek("2027-01-04"), 1);
  assert.equal(isoWeek("2025-12-29"), 1);
});

test("needsUncheckConfirm: only done chores ticked > 30 s ago (D35)", () => {
  const at = "2026-10-09T10:00:00+00:00";
  const t0 = Date.parse(at);
  assert.equal(needsUncheckConfirm({ status: "done", status_at: at }, t0 + 29_000), false);
  assert.equal(needsUncheckConfirm({ status: "done", status_at: at }, t0 + 31_000), true);
  assert.equal(needsUncheckConfirm({ status: "pending", status_at: at }, t0 + 99_000), false);
  assert.equal(needsUncheckConfirm({ status: "done", status_at: null }, t0), false);
});

test("groupBySlot keeps order and drops empty slots (AC-8.1)", () => {
  const chores = [
    { name: "a", slot: "anytime" },
    { name: "m", slot: "morning" },
    { name: "m2", slot: "morning" },
  ];
  assert.deepEqual(
    groupBySlot(chores).map((g) => [g.slot, g.items.map((i) => i.name)]),
    [
      ["morning", ["m", "m2"]],
      ["anytime", ["a"]],
    ],
  );
});

test("cellSymbol", () => {
  assert.equal(cellSymbol("done"), "✓");
  assert.equal(cellSymbol("rejected"), "✗");
  assert.equal(cellSymbol("excused"), "–");
  assert.equal(cellSymbol(undefined), "");
});

test("formatDay and weekdayLetter", () => {
  assert.match(formatDay("2026-10-09", "nb"), /^Fredag 9\. okt/);
  assert.match(formatDay("2026-10-09", "en"), /^Friday 9 Oct/);
  assert.equal(weekdayLetter("2026-10-12", "nb"), "M");
  assert.equal(weekdayLetter("2026-10-18", "en"), "S");
});

test("day navigation stays inside the current week (D37)", async () => {
  const { addDays, dayNav, mondayOf, sameWeek } = await import(
    "../../custom_components/chores_and_rewards/frontend/panel.js"
  );
  assert.equal(addDays("2026-12-31", 1), "2027-01-01");
  assert.equal(addDays("2026-10-25", -1), "2026-10-24"); // DST night
  assert.equal(mondayOf("2026-10-09"), "2026-10-05");
  assert.equal(mondayOf("2026-10-05"), "2026-10-05");
  assert.equal(mondayOf("2026-10-11"), "2026-10-05");
  assert.deepEqual(dayNav("2026-10-09", "2026-10-09"), { prev: "2026-10-08", next: "2026-10-10" });
  assert.deepEqual(dayNav("2026-10-09", "2026-10-05"), { prev: null, next: "2026-10-06" });
  assert.deepEqual(dayNav("2026-10-09", "2026-10-11"), { prev: "2026-10-10", next: null });
  assert.ok(sameWeek("2026-10-09", "2026-10-11"));
  assert.ok(!sameWeek("2026-10-11", "2026-10-12"));
});

test("parentActions mirrors logic.transition (D19)", async () => {
  const { parentActions } = await import("../../custom_components/chores_and_rewards/frontend/panel.js");
  const today = "2026-10-09";
  const inst = (over) => ({ id: 1, day: today, type: "expected", status: "pending", ...over });
  assert.deepEqual(parentActions(inst(), today), ["done", "excused"]);
  assert.deepEqual(parentActions(inst({ status: "done" }), today), ["excused", "rejected", "pending"]);
  assert.deepEqual(parentActions(inst({ status: "missed", day: "2026-10-08" }), today), [
    "done",
    "excused",
  ]);
  assert.deepEqual(parentActions(inst({ status: "excused", day: "2026-10-08" }), today), [
    "done",
    "missed",
  ]);
  assert.deepEqual(parentActions(inst({ type: "bonus", day: "2026-10-08" }), today), ["done", "excused"]);
  assert.deepEqual(parentActions(inst({ day: "2026-10-10" }), today), []); // future
  assert.deepEqual(parentActions(inst({ day: "2026-10-10", can_tick_ahead: true }), today), ["done"]); // D52
  assert.deepEqual(parentActions(inst({ id: null }), today), []); // preview
});

test("cooldownText says who did the chore, and when if it wasn't that day (D51)", async () => {
  const { cooldownText } = await import("../../custom_components/chores_and_rewards/frontend/panel.js");
  const friday = "2026-10-09";
  assert.equal(cooldownText({ kid_id: 1, day: friday }, friday, "Ada", "nb"), "Tatt av Ada");
  assert.equal(cooldownText({ kid_id: 1, day: friday }, friday, "Ada", "en"), "Taken by Ada");
  assert.match(cooldownText({ kid_id: 1, day: "2026-10-08" }, friday, "Ada", "nb"), /^Gjort tor\.? av Ada$/);
  assert.equal(cooldownText({ kid_id: 1, day: "2026-10-08" }, friday, "Ada", "en"), "Done Thu by Ada");
  // A late tick can be blocked by a later day; a week or more away the date is shown.
  assert.match(cooldownText({ kid_id: 1, day: "2026-10-10" }, friday, "Ada", "nb"), /^Gjort lør\.? av Ada$/);
  assert.match(cooldownText({ kid_id: 1, day: "2026-10-01" }, friday, "Ada", "nb"), /^Gjort tor\.? 1\.10\.? av Ada$/);
});

test("parseOptionalInt and weekdayName", async () => {
  const { parseOptionalInt, weekdayName } = await import(
    "../../custom_components/chores_and_rewards/frontend/panel.js"
  );
  assert.equal(parseOptionalInt(""), null);
  assert.equal(parseOptionalInt(" 12 "), 12);
  assert.equal(parseOptionalInt("-5"), -5);
  assert.equal(parseOptionalInt("1.5"), null);
  assert.equal(parseOptionalInt(undefined), null);
  assert.equal(weekdayName(0, "nb"), "mandag");
  assert.equal(weekdayName(6, "en"), "Sunday");
});

test("parentActions matches the shared fixture used by the Python tests", async () => {
  const { parentActions, addDays } = await import(
    "../../custom_components/chores_and_rewards/frontend/panel.js"
  );
  const fixture = JSON.parse(readFileSync(new URL("../fixtures/parent_actions.json", import.meta.url)));
  const today = "2026-10-09";
  for (const c of fixture.cases) {
    const inst = { id: 1, type: c.type, status: c.status, day: addDays(today, c.day), can_tick_ahead: c.ahead };
    assert.deepEqual(parentActions(inst, today), c.actions, JSON.stringify(c));
  }
});

test("kidTap matches the shared fixture used by the Python tests (D8)", async () => {
  const { kidTap, addDays } = await import("../../custom_components/chores_and_rewards/frontend/panel.js");
  const fixture = JSON.parse(readFileSync(new URL("../fixtures/kid_actions.json", import.meta.url)));
  const today = "2026-10-09";
  for (const c of fixture.cases) {
    const inst = { id: 1, type: c.type, status: c.status, day: addDays(today, c.day), can_tick_ahead: c.ahead };
    assert.equal(kidTap(inst, today), c.tap, JSON.stringify(c));
  }
  assert.equal(kidTap({ id: null, status: "pending", day: today }, today), null); // preview
  // A future preview of a chore that can be ticked ahead is tapped through tick_ahead (D52).
  const ahead = { id: null, status: "pending", day: addDays(today, 3), can_tick_ahead: true };
  assert.equal(kidTap(ahead, today), "tick");
});

test("LOG_GROUPS covers every audited action with a label", async () => {
  const { LOG_GROUPS, STRINGS, shortDay } = await import(
    "../../custom_components/chores_and_rewards/frontend/panel.js"
  );
  for (const [group, actions] of Object.entries(LOG_GROUPS)) {
    assert.ok(`g_${group}` in STRINGS.nb, group);
    for (const a of actions ?? []) assert.ok(`a_${a}` in STRINGS.nb, a);
  }
  assert.match(shortDay("2026-10-12", "nb"), /^man\.? 12\.10\.?$/);
});

test("html`` escapes values unless raw(); arrays and nested templates compose", async () => {
  const { html, raw } = await import("../../custom_components/chores_and_rewards/frontend/panel.js");
  const name = `<img src=x onerror=alert(1)>`;
  assert.equal(String(html`<b>${name}</b>`), "<b>&lt;img src=x onerror=alert(1)&gt;</b>");
  assert.equal(String(html`<i>${raw("<br>")}</i>`), "<i><br></i>");
  assert.equal(String(html`${[html`<p>${"a&b"}</p>`, "<x>"]}`), "<p>a&amp;b</p>&lt;x&gt;");
  assert.equal(String(html`${null}${undefined}${false}${0}`), "0");
});

test("earnOptions matches the shared fixture used by the Python tests (AC-6.6, D49)", async () => {
  const { earnOptions } = await import("../../custom_components/chores_and_rewards/frontend/panel.js");
  const fixture = JSON.parse(readFileSync(new URL("../fixtures/earn_options.json", import.meta.url)));
  for (const c of fixture.cases) {
    const balances = Object.fromEntries(
      Object.entries(c.balances).map(([cid, [lost, refilled]]) => [cid, { lost, refilled }]),
    );
    assert.deepEqual(earnOptions({ values: c.values }, fixture.currencies, balances), c.options, JSON.stringify(c));
  }
});

test("formatAmount and parseAmount: minor units in and out (AC-3.4, D50)", async () => {
  const { formatAmount, parseAmount } = await import("../../custom_components/chores_and_rewards/frontend/panel.js");
  const eur = { unit: "€", decimals: 2 };
  assert.equal(formatAmount(50, eur, "nb"), "0,50 €");
  assert.equal(formatAmount(50, eur, "en"), "0.50 €");
  assert.equal(formatAmount(200, eur, "en"), "2 €"); // whole amounts without decimals
  assert.equal(formatAmount(-125, eur, "en"), "-1.25 €");
  assert.equal(formatAmount(10, { unit: "min", decimals: 0 }, "nb"), "10 min");
  assert.equal(formatAmount(1500, { unit: "kr" }, "nb"), "1500 kr");
  assert.equal(parseAmount("0,5", 2), 50);
  assert.equal(parseAmount("1.25", 2), 125);
  assert.equal(parseAmount("-2", 2), -200);
  assert.equal(parseAmount(".5", 1), 5);
  assert.equal(parseAmount("10", 0), 10);
  assert.equal(parseAmount("0.29", 2), 29); // no float drift (0.29 * 100 = 28.999…)
  assert.equal(parseAmount("", 2), null);
  assert.equal(parseAmount("abc", 2), null);
  assert.equal(parseAmount("1,2,3", 2), null);
});
