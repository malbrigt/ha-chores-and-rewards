"""SQLite storage: schema, migrations and data access.

Everything here is synchronous and blocking. Call it from Home Assistant only via
`hass.async_add_executor_job` (the store does this). Each `Database.run` opens a short-lived
connection, runs one transaction and closes it, so there is no cross-thread sharing.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import closing, contextmanager
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from .logic import CapMode, Chore, ChoreType, Currency, Instance, Kid, Slot, Status, week_start

_LOGGER = logging.getLogger(__name__)

# --- Schema -------------------------------------------------------------------
# Conventions (D45): STRICT tables; booleans INTEGER CHECK IN (0,1); dates TEXT
# 'YYYY-MM-DD' checked with date(); timestamps TEXT ISO-8601 UTC checked with datetime();
# amounts INTEGER; every FK child column indexed; soft delete via deleted_at with partial
# unique indexes on names. Schema version lives in PRAGMA user_version.

_SCHEMA = """
CREATE TABLE meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
) STRICT;

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL CHECK (json_valid(value))
) STRICT;

CREATE TABLE kids (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    sort INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    deleted_at TEXT CHECK (deleted_at IS NULL OR datetime(deleted_at) IS NOT NULL)
) STRICT;
CREATE UNIQUE INDEX kids_name ON kids (name COLLATE NOCASE) WHERE deleted_at IS NULL;

CREATE TABLE currencies (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    unit TEXT NOT NULL CHECK (length(trim(unit)) > 0),
    icon TEXT NOT NULL DEFAULT '',
    payout_weekday INTEGER NOT NULL CHECK (payout_weekday BETWEEN 0 AND 6),
    can_be_lost INTEGER NOT NULL CHECK (can_be_lost IN (0, 1)),
    cap_mode TEXT NOT NULL CHECK (cap_mode IN ('fixed', 'pot')),
    default_max INTEGER CHECK (default_max IS NULL OR default_max >= 0),
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    sort INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT CHECK (deleted_at IS NULL OR datetime(deleted_at) IS NOT NULL)
) STRICT;
CREATE UNIQUE INDEX currencies_name ON currencies (name COLLATE NOCASE)
    WHERE deleted_at IS NULL;

CREATE TABLE kid_currency_max (
    kid_id INTEGER NOT NULL REFERENCES kids (id),
    currency_id INTEGER NOT NULL REFERENCES currencies (id),
    weekly_max INTEGER NOT NULL CHECK (weekly_max >= 0),
    PRIMARY KEY (kid_id, currency_id)
) STRICT;
CREATE INDEX kid_currency_max_currency ON kid_currency_max (currency_id);

CREATE TABLE chores (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(trim(name)) > 0),
    icon TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    type TEXT NOT NULL CHECK (type IN ('expected', 'bonus')),
    slot TEXT NOT NULL CHECK (slot IN ('morning', 'afternoon', 'anytime')),
    weekdays INTEGER NOT NULL CHECK (weekdays BETWEEN 1 AND 127),  -- bit 0 = Monday
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    sort INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT CHECK (deleted_at IS NULL OR datetime(deleted_at) IS NOT NULL)
) STRICT;
CREATE UNIQUE INDEX chores_name ON chores (name COLLATE NOCASE) WHERE deleted_at IS NULL;

CREATE TABLE chore_kids (
    chore_id INTEGER NOT NULL REFERENCES chores (id),
    kid_id INTEGER NOT NULL REFERENCES kids (id),
    PRIMARY KEY (chore_id, kid_id)
) STRICT;
CREATE INDEX chore_kids_kid ON chore_kids (kid_id);

CREATE TABLE chore_values (
    chore_id INTEGER NOT NULL REFERENCES chores (id),
    currency_id INTEGER NOT NULL REFERENCES currencies (id),
    value INTEGER NOT NULL CHECK (value > 0),
    PRIMARY KEY (chore_id, currency_id)
) STRICT;
CREATE INDEX chore_values_currency ON chore_values (currency_id);

CREATE TABLE weeks (
    start TEXT PRIMARY KEY
        CHECK (start IS date(start, '+0 days') AND strftime('%u', start) = '1'),
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
    closed_at TEXT CHECK (closed_at IS NULL OR datetime(closed_at) IS NOT NULL),
    closed_by TEXT,
    CHECK ((status = 'closed') = (closed_at IS NOT NULL))
) STRICT;

-- One chore for one kid on one day. type/slot/name/icon and instance_values are a
-- snapshot of the chore at that time (D6). week is derived from day; the CHECK keeps
-- it consistent and the FK ties rows to their week.
CREATE TABLE instances (
    -- AUTOINCREMENT: ids of deleted rows are never reused, so audit entity_ids stay
    -- unambiguous and the log can be replayed (D46). Only this table hard-deletes rows
    -- that the audit log refers to by id.
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week TEXT NOT NULL REFERENCES weeks (start)
        CHECK (week = date(day, '-6 days', 'weekday 1')),
    kid_id INTEGER NOT NULL REFERENCES kids (id),
    chore_id INTEGER NOT NULL REFERENCES chores (id),
    day TEXT NOT NULL CHECK (day IS date(day, '+0 days')),
    type TEXT NOT NULL CHECK (type IN ('expected', 'bonus')),
    slot TEXT NOT NULL CHECK (slot IN ('morning', 'afternoon', 'anytime')),
    name TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'done', 'missed', 'excused', 'rejected')),
    status_at TEXT CHECK (status_at IS NULL OR datetime(status_at) IS NOT NULL),
    status_by TEXT,
    UNIQUE (kid_id, chore_id, day),
    CHECK (status = 'pending' OR status_at IS NOT NULL)
) STRICT;
CREATE INDEX instances_week_kid ON instances (week, kid_id);
CREATE INDEX instances_day ON instances (day);
CREATE INDEX instances_chore ON instances (chore_id);

CREATE TABLE instance_values (
    instance_id INTEGER NOT NULL REFERENCES instances (id) ON DELETE CASCADE,
    currency_id INTEGER NOT NULL REFERENCES currencies (id),
    value INTEGER NOT NULL CHECK (value > 0),
    PRIMARY KEY (instance_id, currency_id)
) STRICT;
CREATE INDEX instance_values_currency ON instance_values (currency_id);

CREATE TABLE adjustments (
    id INTEGER PRIMARY KEY,
    week TEXT NOT NULL REFERENCES weeks (start),
    kid_id INTEGER NOT NULL REFERENCES kids (id),
    currency_id INTEGER NOT NULL REFERENCES currencies (id),
    amount INTEGER NOT NULL CHECK (amount <> 0),
    note TEXT NOT NULL CHECK (length(trim(note)) > 0),
    created_at TEXT NOT NULL CHECK (datetime(created_at) IS NOT NULL),
    created_by TEXT
) STRICT;
CREATE INDEX adjustments_week_kid ON adjustments (week, kid_id);
CREATE INDEX adjustments_kid ON adjustments (kid_id);
CREATE INDEX adjustments_currency ON adjustments (currency_id);

CREATE TABLE payouts (
    id INTEGER PRIMARY KEY,
    week TEXT NOT NULL REFERENCES weeks (start),
    kid_id INTEGER NOT NULL REFERENCES kids (id),
    currency_id INTEGER NOT NULL REFERENCES currencies (id),
    amount INTEGER NOT NULL CHECK (amount >= 0),
    done_at TEXT NOT NULL CHECK (datetime(done_at) IS NOT NULL),
    done_by TEXT,
    UNIQUE (week, kid_id, currency_id)
) STRICT;
CREATE INDEX payouts_kid ON payouts (kid_id);
CREATE INDEX payouts_currency ON payouts (currency_id);

-- Append-only history (polymorphic: entity + entity_id, no FK to the entity itself).
-- kid_id/day/late make the log filterable (D43, D44); day is the chore's day, or the
-- week's Monday for week and payout actions.
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL CHECK (datetime(ts) IS NOT NULL),
    user_id TEXT,
    action TEXT NOT NULL,
    entity TEXT,
    entity_id INTEGER,
    before TEXT CHECK (before IS NULL OR json_valid(before)),
    after TEXT CHECK (after IS NULL OR json_valid(after)),
    note TEXT,
    kid_id INTEGER REFERENCES kids (id),
    day TEXT CHECK (day IS NULL OR day IS date(day, '+0 days')),
    late INTEGER NOT NULL DEFAULT 0 CHECK (late IN (0, 1))
) STRICT;
CREATE INDEX audit_kid_day ON audit_log (kid_id, day);
CREATE INDEX audit_day ON audit_log (day);
CREATE INDEX audit_ts ON audit_log (ts);

INSERT INTO currencies (name, unit, icon, payout_weekday, can_be_lost, cap_mode, sort)
VALUES ('Skjermtid', 'min', 'mdi:tablet', 4, 1, 'fixed', 0),
       ('Ukepenger', 'kr', 'mdi:cash', 5, 0, 'pot', 1);

-- The log starts with the database itself, so all state can be replayed from it (D46).
INSERT INTO audit_log (ts, user_id, action) VALUES
    (strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now'), 'system', 'db_created');
INSERT INTO audit_log (ts, user_id, action, entity, entity_id, after)
SELECT strftime('%Y-%m-%dT%H:%M:%S+00:00', 'now'), 'system', 'currency_save', 'currency', id,
       json_object('id', id, 'name', name, 'unit', unit, 'icon', icon,
                   'payout_weekday', payout_weekday,
                   'can_be_lost', json(iif(can_be_lost, 'true', 'false')),
                   'cap_mode', cap_mode, 'default_max', default_max,
                   'active', json(iif(active, 'true', 'false')), 'sort', sort)
FROM currencies;
"""

# Index i holds the script that upgrades schema version i to i + 1 (PRAGMA user_version).
# One clean schema for now (step 12); add scripts here for future changes.
MIGRATIONS: list[str] = [_SCHEMA]
SCHEMA_VERSION = len(MIGRATIONS)

DEFAULT_SETTINGS: dict[str, Any] = {
    "clean_hands_enabled": True,
    "clean_hands_text": "",  # empty = translated default
    "idle_seconds": 60,
    "wake_seconds": 300,
    "pin_timeout_seconds": 300,
}

META_LAST_FINALIZED = "last_finalized"
SYSTEM = "system"  # audit user for automatic changes (same value as const.SYSTEM_USER)


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


ALL_DAYS = 0b1111111


def weekdays_to_mask(days: Iterable[int]) -> int:
    """Bitmask, bit 0 = Monday. An empty set ("every day", D17) is stored as all days."""
    return sum(1 << d for d in set(days)) or ALL_DAYS


def mask_to_weekdays(mask: int) -> frozenset[int]:
    """All days come back as the empty set, so "every day" has one representation (D17)."""
    if mask == ALL_DAYS:
        return frozenset()
    return frozenset(d for d in range(7) if mask & (1 << d))


# --- Database -----------------------------------------------------------------


class SchemaTooNewError(RuntimeError):
    """The file was written by a newer version of this integration."""


class Database:
    """Owns the SQLite file. Thread-safe by using one connection per call."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _connect(self) -> sqlite3.Connection:
        # timeout=5 installs SQLite's busy handler (same as PRAGMA busy_timeout = 5000).
        conn = sqlite3.connect(self.path, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")  # per connection, off by default
        conn.execute("PRAGMA synchronous = NORMAL")  # safe with WAL, fewer fsyncs
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
        self._reset_legacy()
        with closing(self._connect()) as conn:
            conn.execute("PRAGMA journal_mode = WAL")  # persistent once set
            current = _read_version(conn)
            if current > SCHEMA_VERSION:
                raise SchemaTooNewError(f"Database schema v{current} is newer than this code")
            if 0 < current < SCHEMA_VERSION:
                self.backup(self.path.with_name(f"{self.path.name}.bak-v{current}"))
            for version in range(current, SCHEMA_VERSION):
                # executescript commits first; wrap explicitly so a failed step rolls back.
                # user_version is transactional, so it only moves if the script succeeds.
                conn.executescript(
                    f"BEGIN; {MIGRATIONS[version]}\nPRAGMA user_version = {version + 1}; COMMIT;"
                )
            conn.execute("PRAGMA optimize")
            return SCHEMA_VERSION

    def _reset_legacy(self) -> None:
        """Pre-0.2 files (schema version kept in a meta table) are set aside, not migrated.

        There was no production data before 0.2 (D45). The old file is kept as a backup.
        """
        if not self.path.exists():
            return
        with closing(sqlite3.connect(self.path)) as conn:
            legacy = (
                conn.execute("PRAGMA user_version").fetchone()[0] == 0
                and conn.execute(
                    "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'meta'"
                ).fetchone()
            )
        if not legacy:
            return
        stamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        target = self.path.with_name(f"{self.path.name}.legacy-{stamp}.bak")
        self.backup(target)
        for suffix in ("", "-wal", "-shm"):
            self.path.with_name(self.path.name + suffix).unlink(missing_ok=True)
        _LOGGER.warning("Old pre-0.2 database moved to %s; starting with a fresh one", target)

    def backup(self, target: Path) -> None:
        """Consistent copy of the live database (safe with WAL)."""
        with closing(self._connect()) as src, closing(sqlite3.connect(target)) as dst:
            src.backup(dst)

    def checkpoint(self) -> None:
        """Flush the WAL into the main file, e.g. before an HA backup."""
        with closing(self._connect()) as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")


def _read_version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])


# --- Repository ---------------------------------------------------------------


class Repo:
    """Queries over one open connection/transaction."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def _x(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, tuple(params))

    def optimize(self) -> None:
        """Refresh query-planner stats. May write, so only call it under the store's write
        lock (the daily rollover does); never from unlocked reads, or concurrent
        connections can hit "database is locked"."""
        self._x("PRAGMA optimize")

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

    def all_kid_max(self) -> dict[tuple[int, int], int]:
        """{(kid_id, currency_id): weekly_max} for every kid."""
        rows = self._x("SELECT kid_id, currency_id, weekly_max FROM kid_currency_max")
        return {(r[0], r[1]): r[2] for r in rows}

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

    def ensure_week(self, start: date, by: str | None = SYSTEM) -> None:
        row = self._x(
            "INSERT OR IGNORE INTO weeks (start) VALUES (?) RETURNING start", [start.isoformat()]
        ).fetchone()
        if row is not None:
            self.audit("week_open", user_id=by, entity="week", day=start)

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

    def reopen_week(self, start: date) -> None:
        self._x(
            "UPDATE weeks SET status = 'open', closed_at = NULL, closed_by = NULL WHERE start = ?",
            [start.isoformat()],
        )

    # instances

    def insert_instances(self, instances: Iterable[Instance], by: str | None = SYSTEM) -> int:
        """Insert new instances; existing (kid, chore, day) rows are left alone.

        The week is derived from each instance's day, so callers can't mismatch them.
        """
        rows = list(instances)
        for week in {week_start(i.day) for i in rows}:
            self.ensure_week(week)
        inserted = 0
        for i in rows:
            row = self._x(
                "INSERT OR IGNORE INTO instances (week, kid_id, chore_id, day, type, slot, name,"
                " icon, status, status_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) RETURNING id",
                [
                    week_start(i.day).isoformat(),
                    i.kid_id,
                    i.chore_id,
                    i.day.isoformat(),
                    i.type.value,
                    i.slot.value,
                    i.name,
                    i.icon,
                    i.status.value,
                    i.status_at,
                ],
            ).fetchone()
            if row is not None:  # None: the (kid, chore, day) row already existed
                self._set_instance_values(row[0], i.values)
                self._audit_instance("instance_create", by, replace(i, id=row[0]))
                inserted += 1
        return inserted

    def _audit_instance(
        self, action: str, by: str | None, inst: Instance, before: Any = None
    ) -> None:
        """Full snapshot, so the row can be rebuilt from the log alone (D46)."""
        self.audit(
            action,
            user_id=by,
            entity="instance",
            entity_id=inst.id,
            before=before,
            after=instance_snapshot(inst),
            kid_id=inst.kid_id,
            day=inst.day,
        )

    def _set_instance_values(self, instance_id: int, values: Mapping[int, int]) -> None:
        self._x("DELETE FROM instance_values WHERE instance_id = ?", [instance_id])
        self.conn.executemany(
            "INSERT INTO instance_values (instance_id, currency_id, value) VALUES (?, ?, ?)",
            [(instance_id, cid, v) for cid, v in values.items() if v],
        )

    def _load_instances(self, where: str, params: list[Any]) -> list[Instance]:
        rows = self._x(f"SELECT * FROM instances {where} ORDER BY day, id", params).fetchall()
        values: dict[int, dict[int, int]] = {}
        for r in self._x(
            "SELECT instance_id, currency_id, value FROM instance_values"
            f" WHERE instance_id IN (SELECT id FROM instances {where})",
            params,
        ):
            values.setdefault(r[0], {})[r[1]] = r[2]
        return [_instance(r, values.get(r["id"], {})) for r in rows]

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
        return self._load_instances("WHERE " + " AND ".join(where) if where else "", params)

    def get_instance(self, instance_id: int) -> Instance | None:
        found = self._load_instances("WHERE id = ?", [instance_id])
        return found[0] if found else None

    def set_status(
        self, instance_id: int, status: Status, by: str | None, at: str | None = None
    ) -> None:
        self._x(
            "UPDATE instances SET status = ?, status_at = ?, status_by = ? WHERE id = ?",
            [Status(status).value, at or now_iso(), by, instance_id],
        )

    def resync_pending(self, chore: Chore, day: date, by: str | None = SYSTEM) -> None:
        """Refresh pending snapshots of `chore` on `day` after an edit (D7)."""
        ids = self._x(
            "UPDATE instances SET type = ?, slot = ?, name = ?, icon = ?"
            " WHERE chore_id = ? AND day = ? AND status = 'pending' RETURNING id",
            [chore.type.value, chore.slot.value, chore.name, chore.icon, chore.id, day.isoformat()],
        ).fetchall()
        for (instance_id,) in ids:
            self._set_instance_values(instance_id, chore.values)
            inst = self.get_instance(instance_id)
            assert inst is not None
            self._audit_instance("instance_update", by, inst)

    def delete_pending(
        self, chore_id: int, day: date, keep_kids: Iterable[int] = (), by: str | None = SYSTEM
    ) -> None:
        """Drop pending rows for a chore on a day, e.g. when it is unassigned or deactivated."""
        keep = list(keep_kids)
        sql = "DELETE FROM instances WHERE chore_id = ? AND day = ? AND status = 'pending'"
        if keep:
            sql += f" AND kid_id NOT IN ({','.join('?' * len(keep))})"
        self._audit_deleted(
            self._x(sql + " RETURNING id, kid_id, day", [chore_id, day.isoformat(), *keep]), by
        )

    def delete_pending_for_kid(self, kid_id: int, day: date, by: str | None = SYSTEM) -> None:
        """Drop a kid's pending rows on a day, e.g. when the kid is deactivated."""
        rows = self._x(
            "DELETE FROM instances WHERE kid_id = ? AND day = ? AND status = 'pending'"
            " RETURNING id, kid_id, day",
            [kid_id, day.isoformat()],
        )
        self._audit_deleted(rows, by)

    def _audit_deleted(self, rows: sqlite3.Cursor, by: str | None) -> None:
        for instance_id, kid_id, day in rows.fetchall():
            self.audit(
                "instance_delete",
                user_id=by,
                entity="instance",
                entity_id=instance_id,
                kid_id=kid_id,
                day=date.fromisoformat(day),
            )

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

    def adjustment_totals(self, week: date) -> dict[tuple[int, int], int]:
        """{(kid_id, currency_id): sum of adjustments} for one week."""
        rows = self._x(
            "SELECT kid_id, currency_id, SUM(amount) FROM adjustments WHERE week = ?"
            " GROUP BY kid_id, currency_id",
            [week.isoformat()],
        )
        return {(r[0], r[1]): r[2] for r in rows}

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
        entity_id: int | None = None,
        before: Any = None,
        after: Any = None,
        note: str | None = None,
        at: str | None = None,
        kid_id: int | None = None,
        day: date | None = None,
        late: bool = False,
    ) -> None:
        self._x(
            "INSERT INTO audit_log (ts, user_id, action, entity, entity_id, before, after, note,"
            " kid_id, day, late) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                at or now_iso(),
                user_id,
                action,
                entity,
                entity_id,
                _json_or_none(before),
                _json_or_none(after),
                note,
                kid_id,
                day.isoformat() if day else None,
                late,
            ],
        )

    def list_audit(
        self,
        limit: int = 100,
        *,
        actions: Iterable[str] | None = None,
        kid_id: int | None = None,
        week: date | None = None,
        late_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Newest first. `week` matches the chore's day (or the action's day if none)."""
        where: list[str] = []
        params: list[Any] = []
        if actions is not None:
            names = list(actions)
            where.append(f"action IN ({','.join('?' * len(names))})" if names else "0")
            params += names
        if kid_id is not None:
            where.append("kid_id = ?")
            params.append(kid_id)
        if week is not None:
            where.append("day BETWEEN ? AND ?")
            params += [week.isoformat(), (week + timedelta(days=6)).isoformat()]
        if late_only:
            where.append("late = 1")
        sql = "SELECT * FROM audit_log"
        if where:
            sql += " WHERE " + " AND ".join(where)
        rows = self._x(sql + " ORDER BY id DESC LIMIT ?", [*params, limit])
        return [{**dict(r), "late": bool(r["late"])} for r in rows]

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


def instance_snapshot(inst: Instance) -> dict[str, Any]:
    """Everything needed to recreate an instance row (D46)."""
    return {
        "id": inst.id,
        "kid_id": inst.kid_id,
        "chore_id": inst.chore_id,
        "day": inst.day.isoformat(),
        "type": inst.type.value,
        "slot": inst.slot.value,
        "name": inst.name,
        "icon": inst.icon,
        "values": {str(k): v for k, v in inst.values.items()},
        "status": inst.status.value,
    }


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


def _instance(r: sqlite3.Row, values: dict[int, int]) -> Instance:
    return Instance(
        id=r["id"],
        kid_id=r["kid_id"],
        chore_id=r["chore_id"],
        day=date.fromisoformat(r["day"]),
        type=ChoreType(r["type"]),
        slot=Slot(r["slot"]),
        name=r["name"],
        icon=r["icon"],
        values=values,
        status=Status(r["status"]),
        status_at=r["status_at"],
    )
