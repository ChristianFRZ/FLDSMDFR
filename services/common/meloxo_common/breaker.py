"""Circuit breaker: tras varios fallos seguidos deja de llamar un rato y prueba con una sola llamada."""
import time
from collections.abc import Callable
from typing import Literal

State = Literal["closed", "open", "half_open"]


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        window_seconds: float = 30,
        open_seconds: float = 15,
        clock: Callable[[], float] = time.monotonic,
    ):
        self._threshold = failure_threshold
        self._window = window_seconds
        self._open_seconds = open_seconds
        self._clock = clock
        self._failures: list[float] = []
        self._opened_at: float | None = None
        self._probing = False

    @property
    def state(self) -> State:
        if self._opened_at is None:
            return "closed"
        return "half_open" if self._probing else "open"

    def allow(self) -> bool:
        if self._opened_at is None:
            return True
        if self._probing or self._clock() - self._opened_at < self._open_seconds:
            return False
        self._probing = True
        return True

    def record_success(self) -> None:
        if self._opened_at is not None:
            self._opened_at = None
            self._probing = False
            self._failures.clear()

    def record_failure(self) -> None:
        now = self._clock()
        if self._opened_at is not None:
            self._opened_at = now
            self._probing = False
            return
        self._failures = [t for t in self._failures if now - t < self._window]
        self._failures.append(now)
        if len(self._failures) >= self._threshold:
            self._opened_at = now
            self._probing = False
