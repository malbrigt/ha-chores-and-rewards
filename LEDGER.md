# Ledger

Each step records its status, what was built, how it was solved, any deviations, tests, and the commit. The plan is in `CLAUDE.md` and `docs/`.

| Step | Title | Status |
|---|---|---|
| 1 | Scaffold and baseline | ✅ |
| 2 | Domain logic (`logic.py`) | ⏳ |
| 3 | Persistence (`db.py`) | ⏳ |
| 4 | Store and scheduler | ⏳ |
| 5 | WS contract, PIN, admin CRUD | ⏳ |
| 6 | Kid and read API | ⏳ |
| 7 | Parent actions | ⏳ |
| 8 | Panel part 1 | ⏳ |
| 9 | Panel part 2 | ⏳ |
| 10 | Sensors and release | ⏳ |

---

## Step 1: Scaffold and baseline ✅
**Built**
- Integration skeleton: `manifest.json`, `const.py`, `__init__.py`, `config_flow.py`, nb/en translations, and a generated `brand/icon.png`.
- `hacs.json`, LICENSE, `pyproject.toml` (ruff and pytest).
- Scripts: `script/{setup,test,lint,develop}`. CI covers ruff, pytest, node, hassfest and HACS.
- `docker-compose.yml` with HA 2026.10.
- `CLAUDE.md`, `docs/decisions.md`, `docs/acceptance.md`.

**How**
- **Config flow:** asks for the PIN twice, validates 4–8 digits, and stores only a salted scrypt hash, computed in the executor because scrypt is deliberately slow. Single instance comes from `single_config_entry` in the manifest. The options flow resets the PIN by updating `entry.data`.
- **Test environment:** `pytest-homeassistant-custom-component==0.13.371` pins HA 2026.10.0. The tests also need `home-assistant-frontend==20260930.2`, because our manifest depends on `frontend` and `panel_custom`.
- **Toolchain:** this machine has no `uv` or `node`, so we use a plain `python3.14 -m venv`. JS tests fall back to `node:22-alpine` in Docker.

**Deviations**
- The PIN hash helpers live in `logic.py`, since they are pure and testable.
- The repo was renamed to `malbrigt/ha-chores-and-rewards` (D15).

**Tests:** 15 passing (PIN helpers, user flow, errors, single instance, options reset, setup/unload).

**Docker check:** `script/dev_onboard.py` onboards the Docker HA headlessly (user `dev`/`dev`) and adds the integration with PIN `1234`. Result: entry `loaded` in HA 2026.10.

**CI:** pushed to the public GitHub repo. lint-test, hassfest and HACS all pass. HACS needed a repo description and topics, set with `gh repo edit`.

**Commit:** (see git log)
