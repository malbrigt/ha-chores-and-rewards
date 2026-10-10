"""Browser E2E against a real Home Assistant (started by script/e2e).

Two "tablets" open the panel. One ticks a chore, the other must update live. Then a
parent unlocks with the PIN and marks the payout as paid; the HA sensor must follow.
Screenshots land in e2e/artifacts/ for a human (or agent) to look at.
"""

import json
import os
import re
import sys
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


def open_tablet(browser, name: str) -> Page:
    context = browser.new_context(
        viewport={"width": 1280, "height": 800}, locale="nb-NO", timezone_id="Europe/Oslo"
    )
    # Log in the way the HA frontend does: tokens + language in localStorage.
    context.add_init_script(
        f"localStorage.setItem('hassTokens', {json.dumps(json.dumps(TOKENS))});"
        "localStorage.setItem('selectedLanguage', '\"nb\"');"
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
            re.compile(r"(Mandag|Tirsdag|Onsdag|Torsdag|Fredag|Lørdag|Søndag)")
        )
        expect(kid(a, "Ada")).to_contain_text("Skjermtid")
        a.screenshot(path=ARTIFACTS / "1-overview.png")

        # Kid taps a chore on tablet A → done; tablet B updates live (AC-6.1).
        row_a = kid(a, "Ada").locator(".chore", has_text="Dekke bordet")
        row_a.click()
        expect(row_a).to_have_class(re.compile(r"\bdone\b"))
        row_b = kid(b, "Ada").locator(".chore", has_text="Dekke bordet")
        expect(row_b).to_have_class(re.compile(r"\bdone\b"), timeout=5_000)
        expect(kid(b, "Ada")).to_contain_text("20/120 min")
        assert state("sensor.ada_skjermtid") == "20", state("sensor.ada_skjermtid")
        b.screenshot(path=ARTIFACTS / "2-live-update.png")

        # Week view for Ada.
        kid(a, "Ada").locator(".kid-name").click()
        expect(a.locator("table.week")).to_be_visible()
        expect(a.locator("header")).to_contain_text("Uke")
        a.screenshot(path=ARTIFACTS / "3-week.png")
        a.locator('[data-action="back"]').click()

        # Parent: wrong PIN, then right PIN → payouts → mark Ada's screen time paid.
        a.locator('[data-action="lock-toggle"]').click()
        for digit in "0000":
            a.locator(f'[data-action="pin-digit"][data-digit="{digit}"]').click()
        a.locator('[data-action="pin-ok"]').click()
        expect(a.locator(".toast")).to_contain_text("Feil PIN")
        for digit in "1234":
            a.locator(f'[data-action="pin-digit"][data-digit="{digit}"]').click()
        a.locator('[data-action="pin-ok"]').click()
        expect(a.locator('[data-action="tab"][data-tab="payouts"]')).to_be_visible()
        a.screenshot(path=ARTIFACTS / "4-parent.png")
        a.locator('[data-action="tab"][data-tab="payouts"]').click()
        card = a.locator(".card").filter(has_text="Skjermtid")
        card.locator("tr", has_text="Ada").locator('[data-action="pay"]').click()
        expect(card.locator("tr", has_text="Ada")).to_contain_text("Utbetalt 20 min")
        a.screenshot(path=ARTIFACTS / "5-payouts.png")

        # Admin tab renders.
        a.locator('[data-action="tab"][data-tab="admin"]').click()
        expect(a.locator("main")).to_contain_text("Dekke bordet")
        a.screenshot(path=ARTIFACTS / "6-admin.png")
        browser.close()
    print("E2E passed. Screenshots:", ARTIFACTS)


if __name__ == "__main__":
    main()
