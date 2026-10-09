"""SQLite storage in db.py, against a temp file. No hass needed."""

import sqlite3
from contextlib import closing
from dataclasses import replace
from datetime import date

import pytest

from custom_components.chores_and_rewards import db as dbmod
from custom_components.chores_and_rewards.db import (
    SCHEMA_VERSION,
    Database,
    mask_to_weekdays,
    weekdays_to_mask,
)
from custom_components.chores_and_rewards.logic import (
    CapMode,
    Chore,
    ChoreType,
    Currency,
    Slot,
    Status,
    instances_for_day,
    week_start,
)

MON = date(2026, 10, 5)


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "chores.db")
    database.migrate()
    return database


def _chore(kids, **kw):
    base = Chore(
        id=0,
        name="Dishes",
        type=ChoreType.EXPECTED,
        kid_ids=frozenset(kids),
        weekdays=frozenset({0, 2}),
        slot=Slot.AFTERNOON,
        values={1: 30, 2: 10},
        icon="mdi:silverware",
    )
    return replace(base, **kw)


# --- migrations ---------------------------------------------------------------


def test_migrate_fresh_seeds_currencies_and_wal(db, tmp_path):
    assert db.schema_version() == SCHEMA_VERSION
    currencies = db.run(lambda r: r.list_currencies())
    assert [(c.name, c.payout_weekday, c.can_be_lost, c.cap_mode) for c in currencies] == [
        ("Skjermtid", 4, True, CapMode.FIXED),
        ("Ukepenger", 5, False, CapMode.POT),
    ]
    with closing(sqlite3.connect(tmp_path / "chores.db")) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_migrate_is_idempotent(db, tmp_path):
    assert db.migrate() == SCHEMA_VERSION
    assert len(db.run(lambda r: r.list_currencies())) == 2
    assert not list(tmp_path.glob("*.bak-*"))  # nothing to back up when up to date


def test_upgrade_backs_up_and_applies(tmp_path, monkeypatch):
    path = tmp_path / "chores.db"
    Database(path).migrate()
    db = Database(path)
    db.run(lambda r: r.add_kid("Ada"))
    monkeypatch.setattr(dbmod, "MIGRATIONS", [*dbmod.MIGRATIONS, "ALTER TABLE kids ADD x INT;"])
    monkeypatch.setattr(dbmod, "SCHEMA_VERSION", SCHEMA_VERSION + 1)
    assert db.migrate() == SCHEMA_VERSION + 1
    backup = Database(tmp_path / f"chores.db.bak-v{SCHEMA_VERSION}")
    assert backup.schema_version() == SCHEMA_VERSION
    assert [k.name for k in backup.run(lambda r: r.list_kids())] == ["Ada"]


def test_failed_migration_rolls_back(tmp_path, monkeypatch):
    path = tmp_path / "chores.db"
    Database(path).migrate()
    bad = "CREATE TABLE extra (a INT); THIS IS NOT SQL;"
    monkeypatch.setattr(dbmod, "MIGRATIONS", [*dbmod.MIGRATIONS, bad])
    monkeypatch.setattr(dbmod, "SCHEMA_VERSION", SCHEMA_VERSION + 1)
    with pytest.raises(sqlite3.Error):
        Database(path).migrate()
    db = Database(path)
    assert db.schema_version() == SCHEMA_VERSION
    with closing(sqlite3.connect(path)) as conn:
        assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='extra'").fetchone()


def test_refuses_newer_schema(db, monkeypatch):
    monkeypatch.setattr(dbmod, "SCHEMA_VERSION", 0)
    with pytest.raises(RuntimeError):
        db.migrate()


def test_transaction_rolls_back_on_error(db):
    def boom(r):
        r.add_kid("Ghost")
        raise ValueError

    with pytest.raises(ValueError):
        db.run(boom)
    assert db.run(lambda r: r.list_kids()) == []


def test_backup_and_checkpoint(db, tmp_path):
    db.run(lambda r: r.add_kid("Ada"))
    db.checkpoint()
    db.backup(tmp_path / "copy.db")
    assert [k.name for k in Database(tmp_path / "copy.db").run(lambda r: r.list_kids())] == ["Ada"]


# --- settings / meta ----------------------------------------------------------


def test_settings_defaults_and_override(db):
    s = db.run(lambda r: r.get_settings())
    assert s["clean_hands_enabled"] is True and s["idle_seconds"] == 60
    db.run(lambda r: r.set_setting("idle_seconds", 90))
    assert db.run(lambda r: r.get_settings())["idle_seconds"] == 90


def test_last_finalized(db):
    assert db.run(lambda r: r.last_finalized()) is None
    db.run(lambda r: r.set_last_finalized(MON))
    assert db.run(lambda r: r.last_finalized()) == MON


def test_weekday_mask_roundtrip():
    assert weekdays_to_mask({0, 6}) == 0b1000001
    assert mask_to_weekdays(0b1000001) == frozenset({0, 6})
    assert mask_to_weekdays(0) == frozenset()


# --- kids / currencies --------------------------------------------------------


def test_kids_crud_order_and_soft_delete(db):
    a = db.run(lambda r: r.add_kid("Ada", sort=2))
    b = db.run(lambda r: r.add_kid("Bo", sort=1))
    assert [k.name for k in db.run(lambda r: r.list_kids())] == ["Bo", "Ada"]
    db.run(lambda r: r.update_kid(b, active=False))
    assert [k.id for k in db.run(lambda r: r.list_kids())] == [a]
    assert len(db.run(lambda r: r.list_kids(include_inactive=True))) == 2
    db.run(lambda r: r.delete_kid(a))
    assert db.run(lambda r: r.get_kid(a)) is None
    assert db.run(lambda r: r.get_kid(b)).name == "Bo"
    with pytest.raises(ValueError):
        db.run(lambda r: r.update_kid(b, bogus=1))


def test_kid_max(db):
    kid = db.run(lambda r: r.add_kid("Ada"))
    db.run(lambda r: r.set_kid_max(kid, 1, 90))
    assert db.run(lambda r: r.kid_max(kid)) == {1: 90}
    db.run(lambda r: r.set_kid_max(kid, 1, None))
    assert db.run(lambda r: r.kid_max(kid)) == {}


def test_currency_crud(db):
    cid = db.run(
        lambda r: r.add_currency(
            Currency(0, "Stars", "★", payout_weekday=6, can_be_lost=False, default_max=5)
        )
    )
    db.run(lambda r: r.update_currency(cid, cap_mode="pot", active=False))
    assert [c.id for c in db.run(lambda r: r.list_currencies())] == [1, 2]
    got = next(c for c in db.run(lambda r: r.list_currencies(True)) if c.id == cid)
    assert got.cap_mode is CapMode.POT and not got.active
    db.run(lambda r: r.delete_currency(cid))
    assert len(db.run(lambda r: r.list_currencies(True))) == 2


def test_check_constraints(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.run(lambda r: r.add_currency(Currency(0, "X", "x", payout_weekday=7, can_be_lost=False)))


# --- chores -------------------------------------------------------------------


def test_chore_roundtrip_and_update(db):
    ada = db.run(lambda r: r.add_kid("Ada"))
    bo = db.run(lambda r: r.add_kid("Bo"))
    cid = db.run(lambda r: r.add_chore(_chore({ada, bo})))
    chore = db.run(lambda r: r.get_chore(cid))
    assert chore.kid_ids == {ada, bo} and chore.values == {1: 30, 2: 10}
    assert chore.weekdays == {0, 2} and chore.type is ChoreType.EXPECTED
    db.run(lambda r: r.update_chore(replace(chore, kid_ids=frozenset({bo}), values={2: 0, 1: 5})))
    chore = db.run(lambda r: r.get_chore(cid))
    assert chore.kid_ids == {bo} and chore.values == {1: 5}  # zero values are dropped
    db.run(lambda r: r.update_chore(replace(chore, active=False)))
    assert db.run(lambda r: r.list_chores()) == []
    db.run(lambda r: r.delete_chore(cid))
    assert db.run(lambda r: r.get_chore(cid)) is None


# --- instances ----------------------------------------------------------------


def _setup_instances(db):
    ada = db.run(lambda r: r.add_kid("Ada"))
    cid = db.run(lambda r: r.add_chore(_chore({ada})))
    chores = db.run(lambda r: r.list_chores())
    db.run(lambda r: r.insert_instances(instances_for_day(chores, [ada], MON), week_start(MON)))
    return ada, cid


def test_insert_instances_is_idempotent(db):
    """AC-6.3 / D6: re-creating a day never duplicates rows."""
    ada, cid = _setup_instances(db)
    chores = db.run(lambda r: r.list_chores())
    again = db.run(lambda r: r.insert_instances(instances_for_day(chores, [ada], MON), MON))
    assert again == 0
    rows = db.run(lambda r: r.list_instances(day=MON))
    assert len(rows) == 1 and rows[0].values == {1: 30, 2: 10} and rows[0].id
    assert db.run(lambda r: r.open_weeks()) == [MON]


def test_status_and_filters(db):
    ada, _ = _setup_instances(db)
    inst = db.run(lambda r: r.list_instances(week=MON, kid_id=ada))[0]
    db.run(lambda r: r.set_status(inst.id, Status.DONE, by="kid"))
    assert db.run(lambda r: r.get_instance(inst.id)).status is Status.DONE
    assert db.run(lambda r: r.get_instance(9999)) is None
    assert db.run(lambda r: r.list_instances(kid_id=ada + 1)) == []
    assert len(db.run(lambda r: r.list_instances())) == 1


def test_resync_pending_keeps_history(db):
    """AC-5.6 / D7: edits refresh pending rows only."""
    ada, cid = _setup_instances(db)
    tue = date(2026, 10, 7)
    chores = db.run(lambda r: r.list_chores())
    db.run(lambda r: r.insert_instances(instances_for_day(chores, [ada], tue), MON))
    done = db.run(lambda r: r.list_instances(day=MON))[0]
    db.run(lambda r: r.set_status(done.id, Status.DONE, by="kid"))
    edited = replace(chores[0], name="Dishes!", values={1: 99})
    for day in (MON, tue):
        db.run(lambda r, d=day: r.resync_pending(edited, d))
    assert db.run(lambda r: r.list_instances(day=MON))[0].name == "Dishes"
    pending = db.run(lambda r: r.list_instances(day=tue))[0]
    assert pending.name == "Dishes!" and pending.values == {1: 99}


def test_delete_pending(db):
    ada, cid = _setup_instances(db)
    bo = db.run(lambda r: r.add_kid("Bo"))
    chore = db.run(lambda r: r.get_chore(cid))
    db.run(
        lambda r: r.insert_instances(
            instances_for_day([replace(chore, kid_ids=frozenset({ada, bo}))], [ada, bo], MON), MON
        )
    )
    db.run(lambda r: r.delete_pending(cid, MON, keep_kids=[bo]))
    assert [i.kid_id for i in db.run(lambda r: r.list_instances(day=MON))] == [bo]
    db.run(lambda r: r.delete_pending(cid, MON))
    assert db.run(lambda r: r.list_instances(day=MON)) == []


# --- weeks / adjustments / payouts / audit -------------------------------------


def test_close_week(db):
    db.run(lambda r: r.ensure_week(MON))
    assert db.run(lambda r: r.week_status(MON)) == "open"
    db.run(lambda r: r.close_week(MON, by="auto"))
    assert db.run(lambda r: r.week_status(MON)) == "closed"
    assert db.run(lambda r: r.open_weeks()) == []
    assert db.run(lambda r: r.week_status(date(2020, 1, 6))) is None
    assert db.run(lambda r: r.list_weeks())[0]["closed_by"] == "auto"


def test_adjustments_require_note(db):
    """AC-7.6."""
    ada = db.run(lambda r: r.add_kid("Ada"))
    db.run(lambda r: r.add_adjustment(MON, ada, 1, 15, "helped grandma", by="u1"))
    db.run(lambda r: r.add_adjustment(MON, ada, 1, -5, "fight", by="u1"))
    assert db.run(lambda r: r.adjustment_total(MON, ada, 1)) == 10
    assert db.run(lambda r: r.adjustment_total(MON, ada, 2)) == 0
    assert len(db.run(lambda r: r.list_adjustments(MON))) == 2
    with pytest.raises(sqlite3.IntegrityError):
        db.run(lambda r: r.add_adjustment(MON, ada, 1, 5, "  ", by="u1"))


def test_payouts(db):
    ada = db.run(lambda r: r.add_kid("Ada"))
    db.run(lambda r: r.record_payout(MON, ada, 1, 90, by="u1"))
    db.run(lambda r: r.record_payout(MON, ada, 1, 100, by="u1"))  # re-tick replaces
    payouts = db.run(lambda r: r.list_payouts(MON))
    assert len(payouts) == 1 and payouts[0]["amount"] == 100
    db.run(lambda r: r.undo_payout(MON, ada, 1))
    assert db.run(lambda r: r.list_payouts(MON)) == []


def test_audit_log(db):
    """AC-7.7."""
    db.run(
        lambda r: r.audit(
            "reject",
            user_id="u1",
            entity="instance",
            entity_id=5,
            before={"status": "done"},
            after={"status": "rejected"},
        )
    )
    db.run(lambda r: r.audit("close_week", user_id=None))
    log = db.run(lambda r: r.list_audit())
    assert [e["action"] for e in log] == ["close_week", "reject"]
    assert log[1]["entity_id"] == "5" and '"rejected"' in log[1]["after"]
    assert log[0]["before"] is None


def test_foreign_keys_enforced(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.run(lambda r: r.set_kid_max(999, 1, 10))
