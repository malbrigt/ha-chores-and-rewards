"""Audit actions: the one list of everything the audit log records (D46).

The log can be replayed into the full state (tests/replay.py). The panel labels every
action, and tests check both against this enum.
"""

from enum import StrEnum


class AuditAction(StrEnum):
    # Admin
    KID_SAVE = "kid_save"
    KID_DELETE = "kid_delete"
    CURRENCY_SAVE = "currency_save"
    CURRENCY_DELETE = "currency_delete"
    CHORE_SAVE = "chore_save"
    CHORE_DELETE = "chore_delete"
    SETTINGS_SAVE = "settings_save"
    # Weeks
    WEEK_OPEN = "week_open"
    CLOSE_WEEK = "close_week"
    REOPEN_WEEK = "reopen_week"
    # Chores per day (instances)
    INSTANCE_CREATE = "instance_create"
    INSTANCE_UPDATE = "instance_update"
    INSTANCE_DELETE = "instance_delete"
    CHECK = "check"
    UNCHECK = "uncheck"
    SET_STATUS = "set_status"
    AUTO_MISSED = "auto_missed"
    # Money
    ADJUST = "adjust"
    PAYOUT = "payout"
    PAYOUT_UNDO = "payout_undo"
    # System
    ROLLOVER = "rollover"
    DB_CREATED = "db_created"
    # PIN usage
    PIN_UNLOCK = "pin_unlock"
    PIN_WRONG = "pin_wrong_pin"
    PIN_LOCKED_OUT = "pin_locked_out"
    PIN_LOCK = "pin_lock"
    PIN_RESET = "pin_reset"


# Recorded for usage/review only; they change no stored state.
USAGE_ONLY = frozenset(
    {
        AuditAction.DB_CREATED,
        AuditAction.PIN_UNLOCK,
        AuditAction.PIN_WRONG,
        AuditAction.PIN_LOCKED_OUT,
        AuditAction.PIN_LOCK,
        AuditAction.PIN_RESET,
    }
)

# Actions that only change an instance's status.
STATUS_ACTIONS = frozenset(
    {AuditAction.CHECK, AuditAction.UNCHECK, AuditAction.SET_STATUS, AuditAction.AUTO_MISSED}
)
