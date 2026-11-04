"""Circuit breaker hecho a mano: cerrado → abierto → semiabierto → cerrado (o abierto otra vez)."""

import logging

import pytest

from app.config import get_settings
from app.shared.circuit import CircuitBreaker, CircuitOpen

SOURCE = get_settings().service_name


@pytest.fixture
def clock():
    return [1000.0]


@pytest.fixture
def breaker(clock):
    return CircuitBreaker(
        SOURCE, "catalog-streaming", failures=5, open_s=10, clock=lambda: clock[0]
    )


def _fail(breaker, n):
    for _ in range(n):
        breaker.before_call()
        breaker.record_failure()


def test_starts_closed(breaker):
    assert breaker.state == "closed"
    breaker.before_call()


def test_opens_after_threshold(breaker):
    _fail(breaker, 5)
    assert breaker.state == "open"


def test_success_resets_count(breaker):
    _fail(breaker, 4)
    breaker.before_call()
    breaker.record_success()
    _fail(breaker, 4)
    assert breaker.state == "closed"


def test_open_rejects(breaker):
    _fail(breaker, 5)
    with pytest.raises(CircuitOpen):
        breaker.before_call()


def test_half_open_after_open_s(breaker, clock):
    _fail(breaker, 5)
    clock[0] += 9.9
    assert breaker.state == "open"
    clock[0] += 0.1
    assert breaker.state == "half_open"


def test_half_open_allows_single_probe(breaker, clock):
    _fail(breaker, 5)
    clock[0] += 10
    breaker.before_call()  # la prueba
    with pytest.raises(CircuitOpen):
        breaker.before_call()  # concurrente: rechazada mientras la prueba sigue en curso


def test_probe_success_closes(breaker, clock):
    _fail(breaker, 5)
    clock[0] += 10
    breaker.before_call()
    breaker.record_success()
    assert breaker.state == "closed"
    assert breaker.snapshot()["consecutive_failures"] == 0


def test_probe_failure_reopens(breaker, clock):
    _fail(breaker, 5)
    clock[0] += 10
    breaker.before_call()
    breaker.record_failure()
    assert breaker.state == "open"
    assert breaker.snapshot()["retry_in_s"] == 10


def test_abandoned_probe_frees_the_slot(breaker, clock):
    _fail(breaker, 5)
    clock[0] += 10
    breaker.before_call()
    breaker.abandon()  # la llamada se canceló sin resultado
    breaker.before_call()  # otra prueba puede pasar


def test_snapshot_fields(breaker, clock):
    snap = breaker.snapshot()
    assert snap["source"] == SOURCE
    assert snap["target"] == "catalog-streaming"
    assert snap["state"] == "closed"
    assert snap["consecutive_failures"] == 0
    assert snap["retry_in_s"] is None
    assert snap["since"].endswith("+00:00")
    _fail(breaker, 5)
    clock[0] += 3
    snap = breaker.snapshot()
    assert snap["state"] == "open"
    assert snap["consecutive_failures"] == 5
    assert snap["retry_in_s"] == 7


def test_transition_logged(breaker, caplog):
    caplog.set_level(logging.WARNING, logger="app.shared.circuit")
    _fail(breaker, 5)
    expected = f"circuito {SOURCE}→catalog-streaming: cerrado → abierto (5 fallas seguidas)"
    assert expected in caplog.text
