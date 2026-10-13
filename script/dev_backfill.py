"""Dev only: fill the open week up to today as if the kids had done everything on time.

Every expected chore from Monday to today is ticked, except one random chore today for one
random kid. Bonus chores are ticked about half the time, like a real week. Uses the
integration's own actions, so the audit log stays complete. Run with HA stopped
(script/dev_backfill.sh does that). Never part of the integration.
"""

import os
import random
import sys
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from custom_components.chores_and_rewards.actions import Ctx, ensure_today, set_done  # noqa: E402
from custom_components.chores_and_rewards.db import Database  # noqa: E402
from custom_components.chores_and_rewards.logic import (  # noqa: E402
    ChoreType,
    RuleError,
    Status,
    instances_for_day,
    week_start,
)

DB = ROOT / os.environ.get("HA_CONFIG_DIR", "dev/config") / "chores_and_rewards.db"
TZ = ZoneInfo(os.environ.get("TZ_NAME", "Europe/Oslo"))


def on_time(day: date) -> str:
    """18:00 local on the chore's own day, so nothing is flagged as ticked late (D43)."""
    return datetime.combine(day, time(18), TZ).astimezone(UTC).isoformat(timespec="seconds")


def main() -> None:
    today = datetime.now(TZ).date()
    with Database(DB).transaction() as repo:
        ensure_today(repo, Ctx(None, today))
        kids = [k.id for k in repo.list_kids()]
        chores = repo.list_chores()
        day = week_start(today)
        while day < today:  # past days of the open week that never got rows
            if not repo.list_instances(day=day):
                repo.insert_instances(instances_for_day(chores, kids, day))
            day += timedelta(days=1)

        todays = repo.list_instances(day=today)
        skip = random.choice(todays).id if todays else None
        ticked = 0
        day = week_start(today)
        while day <= today:
            for inst in repo.list_instances(day=day):
                if inst.id == skip or inst.status is Status.DONE or inst.id is None:
                    continue
                if inst.type is ChoreType.BONUS and random.random() < 0.5:
                    continue
                try:
                    set_done(repo, Ctx(None, day), inst.id, True)
                except RuleError as err:
                    if err.code != "on_cooldown":
                        raise
                    continue  # another kid already did this extra (D51)
                repo.conn.execute(
                    "UPDATE instances SET status_at = ? WHERE id = ?", [on_time(day), inst.id]
                )
                ticked += 1
            day += timedelta(days=1)
    left = next((i for i in todays if i.id == skip), None)
    print(f"Ticked {ticked}. Left open today: {left.name if left else '-'}", end="")
    print(f" (kid {left.kid_id})" if left else "")


if __name__ == "__main__":
    main()
