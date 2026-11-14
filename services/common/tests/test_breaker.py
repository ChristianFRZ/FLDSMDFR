from meloxo_common.breaker import CircuitBreaker


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make():
    clock = Clock()
    return CircuitBreaker(clock=clock), clock


def fail(breaker, times):
    for _ in range(times):
        assert breaker.allow()
        breaker.record_failure()


def test_opens_after_five_failures_in_window():
    breaker, _ = make()
    fail(breaker, 4)
    assert breaker.state == "closed" and breaker.allow()
    breaker.record_failure()
    assert breaker.state == "open"
    assert not breaker.allow()


def test_failures_outside_window_do_not_count():
    breaker, clock = make()
    for _ in range(10):
        breaker.record_failure()
        clock.now += 31
    assert breaker.state == "closed"


def test_half_open_allows_a_single_probe_after_15s():
    breaker, clock = make()
    fail(breaker, 5)
    clock.now += 14
    assert not breaker.allow()
    clock.now += 1
    assert breaker.allow()
    assert breaker.state == "half_open"
    assert not breaker.allow()


def test_probe_success_closes_and_clears_failures():
    breaker, clock = make()
    fail(breaker, 5)
    clock.now += 15
    assert breaker.allow()
    breaker.record_success()
    assert breaker.state == "closed"
    fail(breaker, 4)
    assert breaker.state == "closed"


def test_probe_failure_reopens_for_another_15s():
    breaker, clock = make()
    fail(breaker, 5)
    clock.now += 15
    assert breaker.allow()
    breaker.record_failure()
    assert breaker.state == "open"
    clock.now += 14
    assert not breaker.allow()
    clock.now += 1
    assert breaker.allow()


def test_success_in_closed_state_does_not_hide_failures():
    breaker, _ = make()
    fail(breaker, 2)
    breaker.record_success()
    fail(breaker, 3)
    assert breaker.state == "open"
