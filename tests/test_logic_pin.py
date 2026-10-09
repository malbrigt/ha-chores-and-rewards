"""PIN helpers in logic.py."""

import pytest

from custom_components.chores_and_rewards.logic import hash_pin, is_valid_pin, verify_pin


@pytest.mark.parametrize(
    ("pin", "ok"),
    [("1234", True), ("12345678", True), ("123", False), ("123456789", False), ("12a4", False)],
)
def test_is_valid_pin(pin, ok):
    assert is_valid_pin(pin) is ok


def test_hash_and_verify():
    stored = hash_pin("2468")
    assert stored.startswith("scrypt$")
    assert verify_pin("2468", stored)
    assert not verify_pin("1357", stored)
    assert hash_pin("2468") != stored  # salted


@pytest.mark.parametrize("bad", ["", "nope", "md5$aa$bb", "scrypt$zz$00"])
def test_verify_rejects_malformed(bad):
    try:
        assert not verify_pin("2468", bad)
    except ValueError:
        pytest.fail("malformed hash must not raise")
