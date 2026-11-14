"""Comprueba sin el stack que la restauración de catalog-streaming no tapa el error original."""
import inspect
import sys
import unittest

import common


class RestoreTest(unittest.TestCase):
    def test_runs_up_with_default_replicas_and_waits(self):
        calls, waited = [], []
        common.restore_catalog(lambda *a: calls.append(a), lambda: waited.append(1))
        self.assertIn("--scale", calls[0])
        self.assertEqual(common.REPLICAS, 2)
        self.assertIn(f"catalog-streaming={common.REPLICAS}", calls[0])
        self.assertEqual(waited, [1])

    def test_demo_stack_defaults_to_replicas(self):
        self.assertEqual(inspect.signature(common.demo_stack).parameters["replicas"].default, common.REPLICAS)

    def test_failure_without_prior_error_propagates(self):
        def boom(*a):
            raise RuntimeError("x")
        with self.assertRaises(RuntimeError):
            common.restore_catalog(boom, lambda: None)

    def test_failure_during_error_keeps_original(self):
        def boom(*a):
            raise RuntimeError("cleanup")
        with self.assertRaises(ValueError):
            try:
                raise ValueError("original")
            finally:
                common.restore_catalog(boom, lambda: None)


class FakeApi:
    def __init__(self, statuses):
        self.statuses, self.paths = list(statuses), []

    def call(self, method, path, body=None):
        self.paths.append((method, path))
        return self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0], {}


class WaitComposerTest(unittest.TestCase):
    def test_returns_once_the_gateway_stops_answering_403(self):
        api, slept = FakeApi([403, 403, 200]), []
        common.wait_composer_role(api, seconds=40, sleep=slept.append, clock=lambda: 0)
        self.assertEqual(len(api.paths), 3)
        self.assertTrue(all(m == "GET" and p.startswith("/api/composer/") for m, p in api.paths))
        self.assertEqual(slept, [1, 1])

    def test_raises_failure_after_the_deadline(self):
        api, now = FakeApi([403]), [0.0]

        def sleep(seconds):
            now[0] += seconds

        with self.assertRaises(common.Failure):
            common.wait_composer_role(api, seconds=40, sleep=sleep, clock=lambda: now[0])
        self.assertGreaterEqual(now[0], 40)

    def test_new_composer_waits_for_the_role(self):
        self.assertIn("wait_composer_role", inspect.getsource(common.new_composer))


if __name__ == "__main__":
    unittest.main()
