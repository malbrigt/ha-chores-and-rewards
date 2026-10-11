"""Send WebSocket commands to the local Docker HA. Uses the token from dev_onboard.py.

Usage:
  .venv/bin/python script/dev_ws.py \
    '{"type": "chores_and_rewards/pin/unlock", "pin": "1234"}' ...
Each argument is one message; "$token" in a later message is replaced by the last token seen.
Stops at the first failed command (exit code 1). HA_URL and HA_TOKEN_FILE (default
dev/config/.dev_token) point it at another instance, e.g. a real install.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import aiohttp

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("HA_URL", "http://localhost:8123")
TOKEN_FILE = Path(
    os.environ.get("HA_TOKEN_FILE")
    or ROOT / os.environ.get("HA_CONFIG_DIR", "dev/config") / ".dev_token"
)


async def main(messages: list[str], access_token: str) -> None:
    async with (
        aiohttp.ClientSession() as session,
        session.ws_connect(f"{BASE}/api/websocket") as ws,
    ):
        await ws.receive_json()
        await ws.send_json({"type": "auth", "access_token": access_token})
        assert (await ws.receive_json())["type"] == "auth_ok"
        token = ""
        for i, raw in enumerate(messages, start=1):
            msg = json.loads(raw.replace("$token", token))
            await ws.send_json({"id": i, **msg})
            reply = await ws.receive_json()
            print(json.dumps(reply, ensure_ascii=False))
            if not reply.get("success", True):
                sys.exit(1)
            result = reply.get("result")
            if isinstance(result, dict) and "token" in result:
                token = result["token"]


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:], TOKEN_FILE.read_text().strip()))
