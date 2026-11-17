import pytest

from app.core import breaker
from app.core.errors import AppError


def unavailable():
    return AppError(503, "unavailable", "Servicio no disponible")


def test_open_probe_and_recovery(monkeypatch):
    now = 0
    monkeypatch.setattr(breaker.time, "monotonic", lambda: now)
    circuit = breaker.CircuitBreaker()
    for _ in range(5):
        with pytest.raises(AppError), circuit.request(unavailable):
            raise unavailable()
    with pytest.raises(AppError), circuit.request(unavailable):
        pytest.fail("El circuito abierto llamó al servicio")
    now = 15
    with circuit.request(unavailable):
        with pytest.raises(AppError), circuit.request(unavailable):
            pytest.fail("Dos solicitudes sondearon la recuperación")
    with circuit.request(unavailable):
        pass
