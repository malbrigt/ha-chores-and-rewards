"""PIN sessions with a fake clock."""

import pytest

from custom_components.chores_and_rewards.logic import RuleError
from custom_components.chores_and_rewards.sessions import PinSessions


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


@pytest.fixture
def clock():
    return Clock()


@pytest.fixture
def sessions(clock):
    return PinSessions(timeout=300, clock=clock)


def test_unlock_and_sliding_expiry(sessions, clock):
    """AC-7.1: expires after 5 min idle; activity extends it."""
    token = sessions.unlock(True)
    assert sessions.expires_in(token) == 300
    clock.t += 200
    assert sessions.touch(token)
    clock.t += 299
    assert sessions.touch(token)  # extended by the previous touch
    clock.t += 301
    assert not sessions.touch(token)
    assert not sessions.touch(token)  # removed


def test_lock_and_bad_tokens(sessions):
    token = sessions.unlock(True)
    sessions.lock(token)
    assert not sessions.touch(token)
    assert not sessions.touch(None)
    assert not sessions.touch("nope")
    a, b = sessions.unlock(True), sessions.unlock(True)
    assert a != b and sessions.touch(a) and sessions.touch(b)


def test_lockout_after_five_failures(sessions, clock):
    """AC-7.2."""
    for _ in range(4):
        with pytest.raises(RuleError, match="wrong_pin"):
            sessions.unlock(False)
    with pytest.raises(RuleError, match="locked_out"):
        sessions.unlock(False)
    with pytest.raises(RuleError, match="locked_out"):
        sessions.unlock(True)  # even the right PIN waits
    assert sessions.locked_out_for() == 60
    clock.t += 60
    assert sessions.touch(sessions.unlock(True))


def _fail_until_locked(sessions):
    for _ in range(4):
        with pytest.raises(RuleError, match="wrong_pin"):
            sessions.unlock(False)
    with pytest.raises(RuleError, match="locked_out"):
        sessions.unlock(False)


def test_lockout_escalates_and_correct_pin_resets(sessions, clock):
    for expected in (60, 300, 1800, 1800):
        _fail_until_locked(sessions)
        assert sessions.locked_out_for() == expected
        clock.t += expected
    sessions.unlock(True)
    _fail_until_locked(sessions)
    assert sessions.locked_out_for() == 60


def test_success_resets_failures(sessions):
    for _ in range(4):
        with pytest.raises(RuleError):
            sessions.unlock(False)
    sessions.unlock(True)
    _fail_until_locked(sessions)  # the count started again: five more to lock


def test_expired_sessions_purged_on_unlock(sessions, clock):
    old = sessions.unlock(True)
    clock.t += 301
    sessions.unlock(True)
    assert sessions.expires_in(old) == 0
