"""Onboard the local Docker HA (user dev/dev) and add Chores and Rewards (PIN 1234).

Idempotent enough for dev use. Stdlib only. HA_URL (default http://localhost:8123) and
HA_CONFIG_DIR (default dev/config) select the instance. Writes .dev_token (access token)
and .dev_tokens.json (full token set for a browser's localStorage) into the config dir.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("HA_URL", "http://localhost:8123")
CLIENT_ID = f"{BASE}/"
CONFIG_DIR = ROOT / os.environ.get("HA_CONFIG_DIR", "dev/config")
TOKEN_FILE = CONFIG_DIR / ".dev_token"
TOKENS_FILE = CONFIG_DIR / ".dev_tokens.json"


def call(method, path, body=None, token=None, form=False):
    data = None
    headers = {}
    if body is not None:
        if form:
            data = urllib.parse.urlencode(body).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read() or b"null")


def token_from_code(code):
    tok = call(
        "POST",
        "/auth/token",
        {"grant_type": "authorization_code", "code": code, "client_id": CLIENT_ID},
        form=True,
    )
    # Same shape the HA frontend keeps in localStorage["hassTokens"].
    tok.update(
        hassUrl=BASE, clientId=CLIENT_ID, expires=int(time.time() * 1000) + tok["expires_in"] * 1000
    )
    TOKENS_FILE.write_text(json.dumps(tok))
    return tok["access_token"]


def login():
    flow = call(
        "POST",
        "/auth/login_flow",
        {"client_id": CLIENT_ID, "handler": ["homeassistant", None], "redirect_uri": CLIENT_ID},
    )
    res = call(
        "POST",
        f"/auth/login_flow/{flow['flow_id']}",
        {"username": "dev", "password": "dev", "client_id": CLIENT_ID},
    )
    return token_from_code(res["result"])


def main():
    try:
        steps = {s["step"]: s["done"] for s in call("GET", "/api/onboarding")}
    except urllib.error.HTTPError as err:  # 404 once onboarding is finished
        if err.code != 404:
            raise
        steps = {"user": True}
    if not steps.get("user"):
        res = call(
            "POST",
            "/api/onboarding/users",
            {
                "client_id": CLIENT_ID,
                "name": "Dev",
                "username": "dev",
                "password": "dev",
                "language": "en",
            },
        )
        token = token_from_code(res["auth_code"])
        call("POST", "/api/onboarding/core_config", {}, token)
        call("POST", "/api/onboarding/analytics", {}, token)
        call(
            "POST",
            "/api/onboarding/integration",
            {"client_id": CLIENT_ID, "redirect_uri": CLIENT_ID},
            token,
        )
    else:
        token = login()
    TOKEN_FILE.write_text(token)

    entries = call("GET", "/api/config/config_entries/entry", token=token)
    if not any(e["domain"] == "chores_and_rewards" for e in entries):
        flow = call(
            "POST",
            "/api/config/config_entries/flow",
            {"handler": "chores_and_rewards", "show_advanced_options": False},
            token,
        )
        res = call(
            "POST",
            f"/api/config/config_entries/flow/{flow['flow_id']}",
            {"pin": "1234", "pin_confirm": "1234"},
            token,
        )
        assert res["type"] == "create_entry", res
    entries = call("GET", "/api/config/config_entries/entry", token=token)
    entry = next(e for e in entries if e["domain"] == "chores_and_rewards")
    print(f"chores_and_rewards: {entry['state']}")
    sys.exit(0 if entry["state"] == "loaded" else 1)


if __name__ == "__main__":
    main()
