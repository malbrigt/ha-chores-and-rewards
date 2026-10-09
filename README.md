# Chores and Rewards for Home Assistant

A weekly chores and rewards board for a kitchen touchscreen. It runs entirely inside Home Assistant as a custom integration.

Status: in development. See `chores-app-spec.md`.

## Install (manual)
1. Copy `custom_components/chores_and_rewards` to `/config/custom_components/`.
2. Restart Home Assistant.
3. Go to Settings → Devices & services → Add integration → *Chores and Rewards*, and set a parent PIN.

## Develop
```sh
script/setup     # venv + test deps (Python 3.14)
script/test      # pytest (+ node tests)
script/lint      # ruff
script/develop   # HA 2026.10 in Docker on :8123
```

MIT licensed.
