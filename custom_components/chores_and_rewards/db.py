"""SQLite storage: schema, migrations and data access.

Everything here is synchronous and blocking. Call it from Home Assistant only via
`hass.async_add_executor_job` (the store does this). Each `Database.run` opens a short-lived
connection, runs one transaction and closes it, so there is no cross-thread sharing.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import closing, contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from .logic import CapMode, Chore, ChoreType, Currency, Instance, Kid, Slot, Status, week_start

# --- Schema -------------------------------------------------------------------

_V1 = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE kids (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    sort INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1,
    deleted_at TEXT
);

CREATE TABLE currencies (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    unit TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT '',
    payout_weekday INTEGER NOT NULL CHECK (payout_weekday BETWEEN 0 AND 6),
    can_be_lost INTEGER NOT NULL,
    cap_mode TEXT NOT NULL CHECK (cap_mode IN ('fixed', 'pot')),
    default_max INTEGER,
    active INTEGER NOT NULL DEFAULT 1,
    sort INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT
);

CREATE TABLE kid_currency_max (
    kid_id INTEGER NOT NULL REFERENCES kids(id),
    currency_id INTEGER NOT NULL REFERENCES currencies(id),
    weekly_max INTEGER NOT NULL,
    PRIMARY KEY (kid_id, currency_id)
);

CREATE TABLE chores (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    type TEXT NOT NULL CHECK (type IN ('expected', 'bonus')),
    slot TEXT NOT NULL CHECK (slot IN ('morning', 'afternoon', 'anytime')),
    weekdays INTEGER NOT NULL DEFAULT 0,  -- bitmask, bit 0 = Monday; 0 = every day
    active INTEGER NOT NULL DEFAULT 1,
    sort INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT
);

CREATE TABLE chore_kids (
    chore_id INTEGER NOT NULL REFERENCES chores(id),
    kid_id INTEGER NOT NULL REFERENCES kids(id),
    PRIMARY KEY (chore_id, kid_id)
);

CREATE TABLE chore_values (
    chore_id INTEGER NOT NULL REFERENCES chores(id),
    currency_id INTEGER NOT NULL REFERENCES currencies(id),
    value INTEGER NOT NULL,
    PRIMARY KEY (chore_id, currency_id)
);

CREATE TABLE weeks (
    start TEXT PRIMARY KEY,  -- Monday, ISO date
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
    closed_at TEXT,
    closed_by TEXT
);

CREATE TABLE instances (
    id INTEGER PRIMARY KEY,
    week TEXT NOT NULL REFERENCES weeks(start),
    kid_id INTEGER NOT NULL REFERENCES kids(id),
    chore_id INTEGER NOT NULL REFERENCES chores(id),
    day TEXT NOT NULL,
    type TEXT NOT NULL,
    slot TEXT NOT NULL,
    name TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT '',
    "values" TEXT NOT NULL,  -- JSON {currency_id: value}, snapshot
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'done', 'missed', 'excused', 'rejected')),
    status_at TEXT,
    status_by TEXT,
    UNIQUE (kid_id, chore_id, day)
);
CREATE INDEX instances_week_kid ON instances (week, kid_id);
CREATE INDEX instances_day ON instances (day);

CREATE TABLE adjustments (
    id INTEGER PRIMARY KEY,
    week TEXT NOT NULL REFERENCES weeks(start),
    kid_id INTEGER NOT NULL REFERENCES kids(id),
    currency_id INTEGER NOT NULL REFERENCES currencies(id),
    amount INTEGER NOT NULL,
    note TEXT NOT NULL CHECK (length(trim(note)) > 0),
    created_at TEXT NOT NULL,
    created_by TEXT
);

CREATE TABLE payouts (
    id INTEGER PRIMARY KEY,
    week TEXT NOT NULL REFERENCES weeks(start),
    kid_id INTEGER NOT NULL REFERENCES kids(id),
    currency_id INTEGER NOT NULL REFERENCES currencies(id),
    amount INTEGER NOT NULL,
    done_at TEXT NOT NULL,
    done_by TEXT,
    UNIQUE (week, kid_id, currency_id)
);

CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,
    user_id TEXT,
    action TEXT NOT NULL,
    entity TEXT,
    entity_id TEXT,
    before TEXT,
    after TEXT,
    note TEXT
);

INSERT INTO currencies (name, unit, icon, payout_weekday, can_be_lost, cap_mode, sort)
VALUES ('Skjermtid', 'min', 'mdi:tablet', 4, 1, 'fixed', 0),
       ('Ukepenger', 'kr', 'mdi:cash', 5, 0, 'pot', 1);
"""

# Index i holds the script that upgrades schema version i to i + 1.
MIGRATIONS: list[str] = [_V1]
SCHEMA_VERSION = len(MIGRATIONS)

DEFAULT_SETTINGS: dict[str, Any] = {
    "clean_hands_enabled": True,
    "clean_hands_text": "",  # empty = translated default
    "idle_seconds": 60,
    "wake_seconds": 300,
    "pin_timeout_seconds": 300,
}

META_LAST_FINALIZED = "last_finalized"


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def weekdays_to_mask(days: Iterable[int]) -> int:
    return sum(1 << d for d in set(days))


def mask_to_weekdays(mask: int) -> frozenset[int]:
    return frozenset(d for d in range(7) if mask & (1 << d))


# --- Database -----------------------------------------------------------------


class Database:
    """Owns the SQLite file. Thread-safe by using one connection per call."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    @contextmanager
    def transaction(self) -> Iterator[Repo]:
        """One connection, one transaction: commit on success, roll back on error."""
        with closing(self._connect()) as conn, conn:
            yield Repo(conn)

    def run[T](self, fn: Callable[[Repo], T]) -> T:
        """Run `fn(repo)` in one transaction. Use with async_add_executor_job."""
        with self.transaction() as repo:
            return fn(repo)

    def schema_version(self) -> int:
        with closing(self._connect()) as conn:
            return _read_version(conn)

    def migrate(self) -> int:
        """Bring the schema up to date. Backs up the file before upgrading existing data."""
        with closing(self._connect()) as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            current = _read_version(conn)
            if current > SCHEMA_VERSION:
                raise RuntimeError(f"Database schema v{current} is newer than this code")
            if 0 < current < SCHEMA_VERSION:
                self.backup(self.path.with_name(f"{self.path.name}.bak-v{current}"))
            for version in range(current, SCHEMA_VERSION):
                # executescript commits first; wrap explicitly so a failed step rolls back.
                conn.executescript(
                    f"BEGIN; {MIGRATIONS[version]}\n"
                    f"INSERT OR REPLACE INTO meta (key, value) "
                    f"VALUES ('schema_version', '{version + 1}'); COMMIT;"
                )
            return SCHEMA_VERSION

    def backup(self, target: Path) -> None:
        """Consistent copy of the live database (safe with WAL)."""
        with closing(self._connect()) as src, closing(sqlite3.connect(target)) as dst:
            src.backup(dst)

    def checkpoint(self) -> None:
        """Flush the WAL into the main file, e.g. before an HA backup."""
        with closing(self._connect()) as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def _read_version(conn: sqlite3.Connection) -> int:
    has_meta = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'meta'"
    ).fetchone()
    if not has_meta:
        return 0
    row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    return int(row[0]) if row else 0


# --- Repository ---------------------------------------------------------------


class Repo:
    """Queries over one open connection/transaction."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def _x(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, tuple(params))

    # meta / settings

    def get_meta(self, key: str) -> str | None:
        row = self._x("SELECT value FROM meta WHERE key = ?", [key]).fetchone()
        return row[0] if row else None

    def set_meta(self, key: str, value: str) -> None:
        self._x("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", [key, value])

    def last_finalized(self) -> date | None:
        value = self.get_meta(META_LAST_FINALIZED)
        return date.fromisoformat(value) if value else None

    def set_last_finalized(self, day: date) -> None:
        self.set_meta(META_LAST_FINALIZED, day.isoformat())

    def get_settings(self) -> dict[str, Any]:
        stored = {r[0]: json.loads(r[1]) for r in self._x("SELECT key, value FROM settings")}
        return {**DEFAULT_SETTINGS, **stored}

    def set_setting(self, key: str, value: Any) -> None:
        self._x(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", [key, json.dumps(value)]
        )

    # kids

    def list_kids(self, include_inactive: bool = False) -> list[Kid]:
        sql = "SELECT * FROM kids WHERE deleted_at IS NULL"
        if not include_inactive:
            sql += " AND active = 1"
        return [_kid(r) for r in self._x(sql + " ORDER BY sort, id")]

    def get_kid(self, kid_id: int) -> Kid | None:
        row = self._x("SELECT * FROM kids WHERE id = ? AND deleted_at IS NULL", [kid_id]).fetchone()
        return _kid(row) if row else None

    def add_kid(self, name: str, sort: int = 0, active: bool = True) -> int:
        cur = self._x(
            "INSERT INTO kids (name, sort, active) VALUES (?, ?, ?)", [name, sort, active]
        )
        return _id(cur)

    def update_kid(self, kid_id: int, **fields: Any) -> None:
        self._update("kids", kid_id, fields, {"name", "sort", "active"})

    def delete_kid(self, kid_id: int) -> None:
        self._soft_delete("kids", kid_id)

    def kid_max(self, kid_id: int) -> dict[int, int]:
        rows = self._x(
            "SELECT currency_id, weekly_max FROM kid_currency_max WHERE kid_id = ?", [kid_id]
        )
        return {r[0]: r[1] for r in rows}

    def set_kid_max(self, kid_id: int, currency_id: int, weekly_max: int | None) -> None:
        if weekly_max is None:
            self._x(
                "DELETE FROM kid_currency_max WHERE kid_id = ? AND currency_id = ?",
                [kid_id, currency_id],
            )
        else:
            self._x(
                "INSERT OR REPLACE INTO kid_currency_max VALUES (?, ?, ?)",
                [kid_id, currency_id, weekly_max],
            )

    # currencies

    def list_currencies(self, include_inactive: bool = False) -> list[Currency]:
        sql = "SELECT * FROM currencies WHERE deleted_at IS NULL"
        if not include_inactive:
            sql += " AND active = 1"
        return [_currency(r) for r in self._x(sql + " ORDER BY sort, id")]

    def add_currency(self, c: Currency) -> int:
        cur = self._x(
            "INSERT INTO currencies (name, unit, icon, payout_weekday, can_be_lost, cap_mode,"
            " default_max, active, sort) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                c.name,
                c.unit,
                c.icon,
                c.payout_weekday,
                c.can_be_lost,
                c.cap_mode.value,
                c.default_max,
                c.active,
                c.sort,
            ],
        )
        return _id(cur)

    def update_currency(self, currency_id: int, **fields: Any) -> None:
        if "cap_mode" in fields:
            fields["cap_mode"] = CapMode(fields["cap_mode"]).value
        allowed = {"name", "unit", "icon", "payout_weekday", "can_be_lost", "cap_mode"}
        self._update("currencies", currency_id, fields, allowed | {"default_max", "active", "sort"})

    def delete_currency(self, currency_id: int) -> None:
        self._soft_delete("currencies", currency_id)

    # chores

    def list_chores(self, include_inactive: bool = False) -> list[Chore]:
        sql = "SELECT * FROM chores WHERE deleted_at IS NULL"
        if not include_inactive:
            sql += " AND active = 1"
        rows = self._x(sql + " ORDER BY sort, id").fetchall()
        kids: dict[int, set[int]] = {}
        for r in self._x("SELECT chore_id, kid_id FROM chore_kids"):
            kids.setdefault(r[0], set()).add(r[1])
        values: dict[int, dict[int, int]] = {}
        for r in self._x("SELECT chore_id, currency_id, value FROM chore_values"):
            values.setdefault(r[0], {})[r[1]] = r[2]
        return [_chore(r, kids.get(r["id"], set()), values.get(r["id"], {})) for r in rows]

    def get_chore(self, chore_id: int) -> Chore | None:
        return next((c for c in self.list_chores(True) if c.id == chore_id), None)

    def add_chore(self, c: Chore) -> int:
        cur = self._x(
            "INSERT INTO chores (name, icon, description, type, slot, weekdays, active, sort)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                c.name,
                c.icon,
                c.description,
                c.type.value,
                c.slot.value,
                weekdays_to_mask(c.weekdays),
                c.active,
                c.sort,
            ],
        )
        chore_id = _id(cur)
        self._set_chore_links(chore_id, c.kid_ids, c.values)
        return chore_id

    def update_chore(self, c: Chore) -> None:
        """Replace a chore's definition (by id). History keeps its snapshots."""
        self._x(
            "UPDATE chores SET name = ?, icon = ?, description = ?, type = ?, slot = ?,"
            " weekdays = ?, active = ?, sort = ? WHERE id = ?",
            [
                c.name,
                c.icon,
                c.description,
                c.type.value,
                c.slot.value,
                weekdays_to_mask(c.weekdays),
                c.active,
                c.sort,
                c.id,
            ],
        )
        self._x("DELETE FROM chore_kids WHERE chore_id = ?", [c.id])
        self._x("DELETE FROM chore_values WHERE chore_id = ?", [c.id])
        self._set_chore_links(c.id, c.kid_ids, c.values)

    def delete_chore(self, chore_id: int) -> None:
        self._soft_delete("chores", chore_id)

    def _set_chore_links(
        self, chore_id: int, kid_ids: Iterable[int], values: Mapping[int, int]
    ) -> None:
        self.conn.executemany(
            "INSERT INTO chore_kids (chore_id, kid_id) VALUES (?, ?)",
            [(chore_id, k) for k in kid_ids],
        )
        self.conn.executemany(
            "INSERT INTO chore_values (chore_id, currency_id, value) VALUES (?, ?, ?)",
            [(chore_id, cid, v) for cid, v in values.items() if v],
        )

    # weeks

    def ensure_week(self, start: date) -> None:
        self._x("INSERT OR IGNORE INTO weeks (start) VALUES (?)", [start.isoformat()])

    def week_status(self, start: date) -> str | None:
        row = self._x("SELECT status FROM weeks WHERE start = ?", [start.isoformat()]).fetchone()
        return row[0] if row else None

    def open_weeks(self) -> list[date]:
        rows = self._x("SELECT start FROM weeks WHERE status = 'open' ORDER BY start")
        return [date.fromisoformat(r[0]) for r in rows]

    def list_weeks(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self._x("SELECT * FROM weeks ORDER BY start DESC")]

    def close_week(self, start: date, by: str | None, at: str | None = None) -> None:
        self._x(
            "UPDATE weeks SET status = 'closed', closed_at = ?, closed_by = ?"
            " WHERE start = ? AND status = 'open'",
            [at or now_iso(), by, start.isoformat()],
        )

    # instances

    def insert_instances(self, instances: Iterable[Instance]) -> int:
        """Insert new instances; existing (kid, chore, day) rows are left alone.

        The week is derived from each instance's day, so callers can't mismatch them.
        """
        rows = list(instances)
        for week in {week_start(i.day) for i in rows}:
            self.ensure_week(week)
        cur = self.conn.executemany(
            "INSERT OR IGNORE INTO instances (week, kid_id, chore_id, day, type, slot, name, icon,"
            ' "values", status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            [
                (
                    week_start(i.day).isoformat(),
                    i.kid_id,
                    i.chore_id,
                    i.day.isoformat(),
                    i.type.value,
                    i.slot.value,
                    i.name,
                    i.icon,
                    _dump_values(i.values),
                    i.status.value,
                )
                for i in rows
            ],
        )
        return cur.rowcount

    def list_instances(
        self, *, week: date | None = None, day: date | None = None, kid_id: int | None = None
    ) -> list[Instance]:
        where: list[str] = []
        params: list[Any] = []
        if week is not None:
            where.append("week = ?")
            params.append(week.isoformat())
        if day is not None:
            where.append("day = ?")
            params.append(day.isoformat())
        if kid_id is not None:
            where.append("kid_id = ?")
            params.append(kid_id)
        sql = "SELECT * FROM instances"
        if where:
            sql += " WHERE " + " AND ".join(where)
        return [_instance(r) for r in self._x(sql + " ORDER BY day, id", params)]

    def get_instance(self, instance_id: int) -> Instance | None:
        row = self._x("SELECT * FROM instances WHERE id = ?", [instance_id]).fetchone()
        return _instance(row) if row else None

    def set_status(
        self, instance_id: int, status: Status, by: str | None, at: str | None = None
    ) -> None:
        self._x(
            "UPDATE instances SET status = ?, status_at = ?, status_by = ? WHERE id = ?",
            [Status(status).value, at or now_iso(), by, instance_id],
        )

    def resync_pending(self, chore: Chore, day: date) -> None:
        """Refresh pending snapshots of `chore` on `day` after an edit (D7)."""
        self._x(
            'UPDATE instances SET type = ?, slot = ?, name = ?, icon = ?, "values" = ?'
            " WHERE chore_id = ? AND day = ? AND status = 'pending'",
            [
                chore.type.value,
                chore.slot.value,
                chore.name,
                chore.icon,
                _dump_values(chore.values),
                chore.id,
                day.isoformat(),
            ],
        )

    def delete_pending(self, chore_id: int, day: date, keep_kids: Iterable[int] = ()) -> None:
        """Drop pending rows for a chore on a day, e.g. when it is unassigned or deactivated."""
        keep = list(keep_kids)
        sql = "DELETE FROM instances WHERE chore_id = ? AND day = ? AND status = 'pending'"
        if keep:
            sql += f" AND kid_id NOT IN ({','.join('?' * len(keep))})"
        self._x(sql, [chore_id, day.isoformat(), *keep])

    # adjustments

    def add_adjustment(
        self,
        week: date,
        kid_id: int,
        currency_id: int,
        amount: int,
        note: str,
        by: str | None,
        at: str | None = None,
    ) -> int:
        self.ensure_week(week)
        cur = self._x(
            "INSERT INTO adjustments (week, kid_id, currency_id, amount, note, created_at,"
            " created_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [week.isoformat(), kid_id, currency_id, amount, note, at or now_iso(), by],
        )
        return _id(cur)

    def adjustment_total(self, week: date, kid_id: int, currency_id: int) -> int:
        row = self._x(
            "SELECT COALESCE(SUM(amount), 0) FROM adjustments"
            " WHERE week = ? AND kid_id = ? AND currency_id = ?",
            [week.isoformat(), kid_id, currency_id],
        ).fetchone()
        return int(row[0])

    def list_adjustments(self, week: date) -> list[dict[str, Any]]:
        rows = self._x("SELECT * FROM adjustments WHERE week = ? ORDER BY id", [week.isoformat()])
        return [dict(r) for r in rows]

    # payouts

    def record_payout(
        self,
        week: date,
        kid_id: int,
        currency_id: int,
        amount: int,
        by: str | None,
        at: str | None = None,
    ) -> None:
        self.ensure_week(week)
        self._x(
            "INSERT OR REPLACE INTO payouts (week, kid_id, currency_id, amount, done_at, done_by)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [week.isoformat(), kid_id, currency_id, amount, at or now_iso(), by],
        )

    def undo_payout(self, week: date, kid_id: int, currency_id: int) -> None:
        self._x(
            "DELETE FROM payouts WHERE week = ? AND kid_id = ? AND currency_id = ?",
            [week.isoformat(), kid_id, currency_id],
        )

    def list_payouts(self, week: date) -> list[dict[str, Any]]:
        rows = self._x("SELECT * FROM payouts WHERE week = ? ORDER BY id", [week.isoformat()])
        return [dict(r) for r in rows]

    # audit

    def audit(
        self,
        action: str,
        *,
        user_id: str | None,
        entity: str | None = None,
        entity_id: Any = None,
        before: Any = None,
        after: Any = None,
        note: str | None = None,
        at: str | None = None,
    ) -> None:
        self._x(
            "INSERT INTO audit_log (ts, user_id, action, entity, entity_id, before, after, note)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                at or now_iso(),
                user_id,
                action,
                entity,
                None if entity_id is None else str(entity_id),
                _json_or_none(before),
                _json_or_none(after),
                note,
            ],
        )

    def list_audit(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._x("SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", [limit])
        return [dict(r) for r in rows]

    # helpers

    def _update(self, table: str, row_id: int, fields: dict[str, Any], allowed: set[str]) -> None:
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"Unknown fields for {table}: {sorted(unknown)}")
        if not fields:
            return
        cols = ", ".join(f"{k} = ?" for k in fields)
        self._x(f"UPDATE {table} SET {cols} WHERE id = ?", [*fields.values(), row_id])

    def _soft_delete(self, table: str, row_id: int) -> None:
        self._x(f"UPDATE {table} SET deleted_at = ? WHERE id = ?", [now_iso(), row_id])


# --- Row mapping --------------------------------------------------------------


def _id(cur: sqlite3.Cursor) -> int:
    assert cur.lastrowid is not None
    return cur.lastrowid


def _dump_values(values: Mapping[int, int]) -> str:
    return json.dumps({str(k): v for k, v in values.items()}, sort_keys=True)


def _json_or_none(value: Any) -> str | None:
    return None if value is None else json.dumps(value, default=str, sort_keys=True)


def _kid(r: sqlite3.Row) -> Kid:
    return Kid(id=r["id"], name=r["name"], sort=r["sort"], active=bool(r["active"]))


def _currency(r: sqlite3.Row) -> Currency:
    return Currency(
        id=r["id"],
        name=r["name"],
        unit=r["unit"],
        payout_weekday=r["payout_weekday"],
        can_be_lost=bool(r["can_be_lost"]),
        cap_mode=CapMode(r["cap_mode"]),
        default_max=r["default_max"],
        icon=r["icon"],
        active=bool(r["active"]),
        sort=r["sort"],
    )


def _chore(r: sqlite3.Row, kid_ids: set[int], values: dict[int, int]) -> Chore:
    return Chore(
        id=r["id"],
        name=r["name"],
        type=ChoreType(r["type"]),
        kid_ids=frozenset(kid_ids),
        weekdays=mask_to_weekdays(r["weekdays"]),
        slot=Slot(r["slot"]),
        values=values,
        icon=r["icon"],
        description=r["description"],
        active=bool(r["active"]),
        sort=r["sort"],
    )


def _instance(r: sqlite3.Row) -> Instance:
    return Instance(
        id=r["id"],
        kid_id=r["kid_id"],
        chore_id=r["chore_id"],
        day=date.fromisoformat(r["day"]),
        type=ChoreType(r["type"]),
        slot=Slot(r["slot"]),
        name=r["name"],
        icon=r["icon"],
        values={int(k): v for k, v in json.loads(r["values"]).items()},
        status=Status(r["status"]),
    )
