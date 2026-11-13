"""Comprueba sin el stack que la restauración de catalog-streaming no tapa el error original."""
import sys
import unittest

import common


class RestoreTest(unittest.TestCase):
    def test_runs_up_with_single_replica_and_waits(self):
        calls, waited = [], []
        common.restore_catalog(lambda *a: calls.append(a), lambda: waited.append(1))
        self.assertIn("--scale", calls[0])
        self.assertIn("catalog-streaming=1", calls[0])
        self.assertEqual(waited, [1])

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


if __name__ == "__main__":
    unittest.main()
