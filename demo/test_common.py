"""Comprueba sin el stack que la restauración de catalog-streaming no tapa el error original."""
import inspect
import sys
import unittest
from unittest import mock

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

    def test_other_statuses_fail_at_once(self):
        for status in (401, 503):
            api = FakeApi([status])
            with self.assertRaisesRegex(common.Failure, str(status)):
                common.wait_composer_role(api, seconds=40, sleep=lambda s: None, clock=lambda: 0)
            self.assertEqual(len(api.paths), 1)

    def test_new_composer_waits_for_the_role(self):
        composer, promoted = FakeApi([403, 200]), []

        class Admin:
            def ok(self, method, path, body=None):
                promoted.append((method, path, body))

        user = {"id": "u1", "email": "c@x"}
        with mock.patch.object(common, "new_user", return_value=(object(), user)), mock.patch.object(
            common, "login", return_value=composer
        ), mock.patch.object(common.time, "sleep"):
            self.assertEqual(common.new_composer("c", Admin()), (composer, user))
        self.assertEqual(promoted, [("POST", "/api/admin/users/u1/role", {"role": "composer"})])
        self.assertEqual(len(composer.paths), 2)


class WaitEdgeTest(unittest.TestCase):

    def test_needs_five_consecutive_200s(self):
        calls = []
        with mock.patch.object(common, "admin", lambda: object()), mock.patch.object(
            common, "probe_status", lambda api, path: calls.append(1) or 200
        ):
            common.wait_edge(sleep=lambda s: None, clock=lambda: 0)
        self.assertEqual(len(calls), 5)

    def test_a_non_200_resets_the_count(self):
        seq, calls = [200, 200, 200, 200, 502, 200, 200, 200, 200, 200], []

        def probe(api, path):
            calls.append(1)
            return seq.pop(0)

        with mock.patch.object(common, "admin", lambda: object()), mock.patch.object(common, "probe_status", probe):
            common.wait_edge(sleep=lambda s: None, clock=lambda: 0)
        self.assertEqual(len(calls), 10)

    def test_times_out_with_failure(self):
        now = [0.0]

        def sleep(seconds):
            now[0] += seconds

        with mock.patch.object(common, "admin", lambda: object()), mock.patch.object(
            common, "probe_status", lambda api, path: 502
        ):
            with self.assertRaisesRegex(common.Failure, "no respondió"):
                common.wait_edge(sleep=sleep, clock=lambda: now[0])
        self.assertGreaterEqual(now[0], common.START_SECONDS)

    def test_admin_login_failure_raises_at_once(self):
        def broken():
            raise common.Failure("Falta ADMIN_EMAIL en .env")

        slept = []
        with mock.patch.object(common, "admin", broken):
            with self.assertRaisesRegex(common.Failure, "administrador.*ADMIN_EMAIL"):
                common.wait_edge(sleep=slept.append, clock=lambda: 0)
        self.assertEqual(slept, [])


class ProbeTest(unittest.TestCase):
    def test_returns_the_status(self):
        api = mock.Mock()
        api.send.return_value = (503, b"")
        self.assertEqual(common.probe_status(api, "/x"), 503)

    def test_connection_error_counts_as_status_zero(self):
        api = mock.Mock()
        api.send.side_effect = OSError("reset")
        self.assertEqual(common.probe_status(api, "/x"), 0)

    def test_failed_counts_every_non_200(self):
        self.assertEqual(common.failed([200, 0, 200, 502, 404]), 3)


if __name__ == "__main__":
    unittest.main()
