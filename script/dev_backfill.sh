#!/usr/bin/env bash
# Dev only: stop the dev HA, tick the open week up to today (one chore left open), restart.
set -euo pipefail
cd "$(dirname "$0")/.."
docker stop chores-ha >/dev/null
"${PYTHON:-.venv/bin/python}" script/dev_backfill.py
docker start chores-ha >/dev/null
