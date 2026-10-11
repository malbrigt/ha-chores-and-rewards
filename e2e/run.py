"""Browser E2E against a real Home Assistant (started by script/e2e).

Two "tablets" open the panel. One ticks a chore, the other must update live. Then a
parent unlocks with the PIN and marks the payout as paid; the HA sensor must follow.
Screenshots land in e2e/artifacts/ for a human (or agent) to look at.
"""

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("HA_URL", "http://localhost:8124")
CONFIG = ROOT / os.environ.get("HA_CONFIG_DIR", "dev/e2e-config")
ARTIFACTS = ROOT / "e2e/artifacts"
TOKENS = json.loads((CONFIG / ".dev_tokens.json").read_text())
URL = f"{BASE}/chores-and-rewards"


def state(entity_id: str) -> str:
    req = urllib.request.Request(
        f"{BASE}/api/states/{entity_id}",
        headers={"Authorization": f"Bearer {TOKENS['access_token']}"},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())["state"]


def wait_for_state(entity_id: str, expected: str, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while (value := state(entity_id)) != expected:
        if time.monotonic() > deadline:
            raise AssertionError(f"{entity_id} = {value!r}, expected {expected!r}")
        time.sleep(0.2)


def open_tablet(browser, name: str, lang: str = "en") -> Page:
    locale = {"en": "en-GB", "nb": "nb-NO"}[lang]
    context = browser.new_context(
        viewport={"width": 1280, "height": 800}, locale=locale, timezone_id="Europe/Oslo"
    )
    # Log in the way the HA frontend does: tokens + language in localStorage.
    context.add_init_script(
        f"localStorage.setItem('hassTokens', {json.dumps(json.dumps(TOKENS))});"
        f"localStorage.setItem('selectedLanguage', '\"{lang}\"');"
    )
    page = context.new_page()
    page.on("pageerror", lambda err: print(f"[{name}] page error: {err}", file=sys.stderr))
    page.goto(URL)
    expect(page.locator("section.kid").first).to_be_visible(timeout=30_000)
    return page


def kid(page: Page, name: str):
    return page.locator("section.kid").filter(has=page.locator(".kid-name", has_text=name))


def main() -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        a = open_tablet(browser, "A")
        b = open_tablet(browser, "B")
        expect(a.locator("header")).to_contain_text(
            re.compile(r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)")
        )
        expect(kid(a, "Ada")).to_contain_text("Screen time")
        a.screenshot(path=ARTIFACTS / "1-overview.png")

        # Kid taps a chore on tablet A → done; tablet B updates live (AC-6.1).
        row_a = kid(a, "Ada").locator(".chore", has_text="Make your bed")
        row_a.click()
        expect(row_a).to_have_class(re.compile(r"\bdone\b"))
        row_b = kid(b, "Ada").locator(".chore", has_text="Make your bed")
        expect(row_b).to_have_class(re.compile(r"\bdone\b"), timeout=5_000)
        expect(kid(b, "Ada")).to_contain_text("10/120 min")
        # Sensors refresh through a 1 s debouncer, so allow a moment for the value.
        wait_for_state("sensor.ada_screen_time", "10")
        b.screenshot(path=ARTIFACTS / "2-live-update.png")

        # Week view for Ada.
        kid(a, "Ada").locator(".kid-name").click()
        expect(a.locator("table.week")).to_be_visible()
        expect(a.locator("header")).to_contain_text("Week")
        a.screenshot(path=ARTIFACTS / "3-week.png")
        a.locator('[data-action="back"]').click()

        # Parent: wrong PIN, then right PIN → payouts → mark Ada's screen time paid.
        a.locator('[data-action="lock-toggle"]').click()
        for digit in "0000":
            a.locator(f'[data-action="pin-digit"][data-digit="{digit}"]').click()
        a.locator('[data-action="pin-ok"]').click()
        expect(a.locator(".toast")).to_contain_text("Wrong PIN")
        for digit in "1234":
            a.locator(f'[data-action="pin-digit"][data-digit="{digit}"]').click()
        a.locator('[data-action="pin-ok"]').click()
        expect(a.locator('[data-action="tab"][data-tab="payouts"]')).to_be_visible()
        a.screenshot(path=ARTIFACTS / "4-parent.png")
        a.locator('[data-action="tab"][data-tab="payouts"]').click()
        card = a.locator(".card").filter(has_text="Screen time")
        card.locator("tr", has_text="Ada").locator('[data-action="pay"]').click()
        expect(card.locator("tr", has_text="Ada")).to_contain_text("Paid 10 min")
        a.screenshot(path=ARTIFACTS / "5-payouts.png")

        # "Details" opens the audit log filtered on Ada + this week (D44).
        card.locator("tr", has_text="Ada").locator('[data-action="details"]').click()
        expect(a.locator("main")).to_contain_text("Ticked")
        expect(a.locator("main")).to_contain_text("Make your bed")
        a.screenshot(path=ARTIFACTS / "7-log.png")

        # Admin tab renders.
        a.locator('[data-action="tab"][data-tab="admin"]').click()
        expect(a.locator("main")).to_contain_text("Make your bed")
        a.screenshot(path=ARTIFACTS / "6-admin.png")

        # Pay or win back (D49): the parent rejects Ada's bed (−10 min), so the trash
        # offers "win back 10 min" next to "1 €"; she picks screen time.
        a.locator('[data-action="tab"][data-tab="today"]').click()
        bed = kid(a, "Ada").locator(".row", has_text="Make your bed")
        bed.locator('[data-action="more"]').click()
        a.locator('[data-action="sheet-item"]', has_text="Reject").click()
        expect(kid(a, "Ada")).to_contain_text("−10 lost")
        kid(a, "Ada").locator(".chore", has_text="Take out the trash").click()
        expect(a.locator('[data-action="sheet-item"]', has_text="0.30 € Allowance")).to_be_visible()
        a.screenshot(path=ARTIFACTS / "8-earn-picker.png")
        a.locator('[data-action="sheet-item"]', has_text="Win back 10 min").click()
        trash = kid(a, "Ada").locator(".chore", has_text="Take out the trash")
        expect(trash).to_contain_text("+10 min")
        expect(kid(a, "Ada")).not_to_contain_text("−10 lost")

        # The panel follows the HA user's language: Norwegian (AC-8.5). The profile
        # setting wins over the browser's, so switch it the way HA's profile page does.
        a.evaluate(
            """() => document.querySelector("home-assistant").hass.callWS({
                type: "frontend/set_user_data", key: "language",
                value: {language: "nb", number_format: "language", time_format: "language",
                        date_format: "language", time_zone: "local", first_weekday: "language"}})"""
        )
        n = open_tablet(browser, "NB", lang="nb")
        expect(n.locator("header")).to_contain_text(
            re.compile(r"(Mandag|Tirsdag|Onsdag|Torsdag|Fredag|Lørdag|Søndag)", re.IGNORECASE)
        )
        expect(kid(n, "Ada")).to_contain_text("Morgen", ignore_case=True)
        n.screenshot(path=ARTIFACTS / "9-norwegian.png")
        browser.close()
    print("E2E passed. Screenshots:", ARTIFACTS)


if __name__ == "__main__":
    main()
