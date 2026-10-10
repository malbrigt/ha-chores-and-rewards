"""Parent PIN sessions. No HA imports; the clock is injectable for tests.

One shared PIN and (typically) one kitchen screen, so failures are counted globally.
Tokens live in memory only: an HA restart locks everything, which is the safe default.
"""

from __future__ import annotations

import secrets
import time
from collections.abc import Callable

from .logic import RuleError

MAX_FAILURES = 5
# Each lockout in a row lasts longer; a correct PIN or a PIN change resets the ladder.
LOCKOUT_SECONDS = (60, 300, 1800)


class PinSessions:
    def __init__(
        self,
        timeout: float = 300,
        clock: Callable[[], float] = time.monotonic,
        max_failures: int = MAX_FAILURES,
        lockouts: tuple[float, ...] = LOCKOUT_SECONDS,
    ) -> None:
        self.timeout = timeout
        self._clock = clock
        self._max_failures = max_failures
        self._lockouts = lockouts
        self._sessions: dict[str, float] = {}  # token -> expires at
        self._failures = 0
        self._lockout_level = 0  # lockouts since the last correct PIN
        self._locked_until = 0.0

    def locked_out_for(self) -> float:
        """Seconds left of a lockout, 0 if none."""
        return max(0.0, self._locked_until - self._clock())

    def check_allowed(self) -> None:
        """Raise locked_out before spending time verifying a PIN."""
        if self.locked_out_for() > 0:
            raise RuleError("locked_out")

    def unlock(self, pin_ok: bool) -> str:
        """Record an attempt. Returns a new token, or raises wrong_pin / locked_out."""
        self.check_allowed()
        if not pin_ok:
            self._failures += 1
            if self._failures >= self._max_failures:
                self._failures = 0
                step = self._lockouts[min(self._lockout_level, len(self._lockouts) - 1)]
                self._lockout_level += 1
                self._locked_until = self._clock() + step
                raise RuleError("locked_out")
            raise RuleError("wrong_pin")
        self._failures = 0
        self._lockout_level = 0
        self._purge()
        token = secrets.token_urlsafe(32)
        self._sessions[token] = self._clock() + self.timeout
        return token

    def touch(self, token: str | None) -> bool:
        """True if the token is valid; extends it (sliding expiry)."""
        if not token:
            return False
        expires = self._sessions.get(token)
        now = self._clock()
        if expires is None or expires <= now:
            self._sessions.pop(token, None)
            return False
        self._sessions[token] = now + self.timeout
        return True

    def expires_in(self, token: str) -> int:
        return max(0, round(self._sessions.get(token, 0.0) - self._clock()))

    def lock(self, token: str) -> None:
        self._sessions.pop(token, None)

    def _purge(self) -> None:
        now = self._clock()
        for token in [t for t, exp in self._sessions.items() if exp <= now]:
            del self._sessions[token]
