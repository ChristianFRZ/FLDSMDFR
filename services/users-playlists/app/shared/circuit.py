"""Circuit breaker hecho a mano, uno por servicio remoto (rama 04).

- Cerrado: deja pasar y cuenta las llamadas fallidas SEGUIDAS; un éxito reinicia la cuenta.
  Al llegar a `failures` pasa a abierto.
- Abierto: no llama; quien pregunta recibe CircuitOpen al instante. Pasados `open_s` segundos
  pasa a semiabierto.
- Semiabierto: deja pasar UNA llamada de prueba (las demás se rechazan mientras sigue en curso).
  Si sale bien, cierra; si falla, vuelve a abrir otros `open_s` segundos.

El estado vive en la memoria de este proceso: cada instancia del servicio tiene el suyo.
"""

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Literal

logger = logging.getLogger(__name__)

State = Literal["closed", "open", "half_open"]
_NAMES = {"closed": "cerrado", "open": "abierto", "half_open": "semiabierto"}


class CircuitOpen(Exception):
    def __init__(self, target: str):
        super().__init__(f"circuito abierto hacia {target}")
        self.target = target


class CircuitBreaker:
    def __init__(
        self,
        source: str,
        target: str,
        failures: int,
        open_s: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.source, self.target = source, target
        self.failures, self.open_s = failures, open_s
        self._clock = clock
        self._state: State = "closed"
        self._consecutive = 0
        self._since = clock()
        self._opened_at = 0.0
        self._probe_in_flight = False

    @property
    def state(self) -> State:
        if self._state == "open" and self._clock() - self._opened_at >= self.open_s:
            self._move("half_open", f"pasaron {self.open_s:g} s")
            self._probe_in_flight = False
        return self._state

    def before_call(self) -> None:
        """Levanta CircuitOpen si no se debe llamar; en semiabierto reserva la única prueba."""
        state = self.state
        if state == "closed":
            return
        if state == "half_open" and not self._probe_in_flight:
            self._probe_in_flight = True
            return
        raise CircuitOpen(self.target)

    def record_success(self) -> None:
        self._consecutive = 0
        self._probe_in_flight = False
        if self._state != "closed":
            self._move("closed", "la prueba salió bien")

    def record_failure(self) -> None:
        self._consecutive += 1
        if self._state == "half_open":
            self._open("falló la prueba")
        elif self._state == "closed" and self._consecutive >= self.failures:
            self._open(f"{self._consecutive} fallas seguidas")

    def abandon(self) -> None:
        """La llamada terminó sin resultado (p. ej. cancelada): libera la prueba de semiabierto."""
        self._probe_in_flight = False

    def snapshot(self) -> dict:
        state = self.state
        now = self._clock()
        retry_in = None
        if state == "open":
            retry_in = round(max(0.0, self.open_s - (now - self._opened_at)), 1)
        since = datetime.now(UTC) - timedelta(seconds=now - self._since)
        return {
            "source": self.source,
            "target": self.target,
            "state": state,
            "consecutive_failures": self._consecutive,
            "since": since.isoformat(),
            "retry_in_s": retry_in,
        }

    def _open(self, reason: str) -> None:
        self._opened_at = self._clock()
        self._probe_in_flight = False
        self._move("open", reason)

    def _move(self, state: State, reason: str) -> None:
        before, self._state = self._state, state
        self._since = self._clock()
        logger.warning(
            "circuito %s→%s: %s → %s (%s)",
            self.source,
            self.target,
            _NAMES[before],
            _NAMES[state],
            reason,
        )
