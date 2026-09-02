import unittest

from evaluation.agent_benchmark_contract import BenchmarkTask


class BenchmarkTaskTests(unittest.TestCase):
    def test_pause_and_resume(self):
        task = BenchmarkTask("t1", {})
        task.transition("RUNNING")
        task.transition("PAUSED")
        task.transition("RUNNING")
        self.assertEqual(task.state, "RUNNING")

    def test_invalid_transition(self):
        task = BenchmarkTask("t2", {})
        with self.assertRaises(ValueError):
            task.transition("SUCCEEDED")

    def test_evidence_is_retained(self):
        task = BenchmarkTask("t3", {})
        task.record_evidence("observation", {"ok": True})
        self.assertEqual(len(task.evidence), 1)


if __name__ == "__main__":
    unittest.main()
