"""Interruptor por dependencia y proceso. Una sola solicitud sondea la recuperación."""
import time
from collections import deque
from contextlib import contextmanager

from app.core.errors import AppError


class CircuitBreaker:
    def __init__(self):
        self.failures = deque(maxlen=5)
        self.retry_at = None
        self.probing = False
        self.generation = 0

    @contextmanager
    def request(self, unavailable):
        now = time.monotonic()
        probe = self.retry_at is not None
        if probe and (self.probing or now < self.retry_at):
            raise unavailable()
        if probe:
            self.probing = True
        generation = self.generation
        try:
            yield
        except AppError as exc:
            if exc.status >= 500 and generation == self.generation:
                now = time.monotonic()
                self.failures.append(now)
                if probe or (len(self.failures) == 5 and now - self.failures[0] <= 30):
                    self.retry_at = now + 15
                    self.generation += 1
                raise
            if probe:
                self.retry_at = None
                self.failures.clear()
            raise
        else:
            if probe:
                self.retry_at = None
                self.failures.clear()
        finally:
            if probe:
                self.probing = False
