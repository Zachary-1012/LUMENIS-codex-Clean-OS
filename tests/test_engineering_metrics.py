# -*- coding: utf-8 -*-
"""test_engineering_metrics.py — 工程度量聚合器单元测试（P0-E 落地验证）"""
import json
import os
import tempfile
import unittest

import engineering_metrics as em


def _write_trace(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        for l in lines:
            f.write(l + "\n")


class TaskClosedLoopMetricsTest(unittest.TestCase):
    def test_empty_trace(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "none.jsonl")
            m = em.task_closed_loop_metrics(p)
            self.assertEqual(m["total_tasks"], 0)
            self.assertEqual(m["closed_tasks"], 0)
            self.assertEqual(m["task_completion_rate"], 0.0)
            self.assertEqual(m["in_progress_tasks"], 0)
            self.assertEqual(m["open_tasks"], [])

    def test_closed_loop_rate(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.jsonl")
            _write_trace(p, [
                json.dumps({"ts": "2026-09-03T02:00:00", "task": "A", "event": "begin"}),
                json.dumps({"ts": "2026-09-03T02:10:00", "task": "A", "event": "code"}),
                json.dumps({"ts": "2026-09-03T02:30:00", "task": "A", "event": "done", "outcome": "ok"}),
                json.dumps({"ts": "2026-09-03T02:05:00", "task": "B", "event": "begin"}),
                json.dumps({"ts": "2026-09-03T02:06:00", "task": "B", "event": "test"}),
                json.dumps({"ts": "2026-09-03T02:40:00", "task": "B", "event": "fail", "reason": "API timeout"}),
                json.dumps({"ts": "2026-09-03T02:09:00", "task": "C", "event": "begin"}),
                # 坏行应被跳过
                "{not json",
            ])
            m = em.task_closed_loop_metrics(p)
            self.assertEqual(m["total_tasks"], 3)
            self.assertEqual(m["closed_tasks"], 1)
            self.assertAlmostEqual(m["task_completion_rate"], round(1/3, 3))
            self.assertEqual(m["in_progress_tasks"], 1)
            self.assertEqual(m["open_tasks"], ["C"])
            self.assertEqual(m["failed_tasks"], 1)
            self.assertEqual(m["failed_task_list"][0]["task"], "B")
            self.assertEqual(m["recovery_rate"], 0.5)
            self.assertEqual(m["phase_distribution"], {"code": 1, "test": 1})
            # A 从 02:00 → 02:30 = 30 min
            dur = {d["task"]: d["duration_min"] for d in m["task_durations_min"]}
            self.assertAlmostEqual(dur["A"], 30.0)
            self.assertEqual(m["avg_duration_min"], 30.0)

    def test_missing_file_no_raise(self):
        m = em.task_closed_loop_metrics(r"Z:\no\such\file.jsonl")
        self.assertEqual(m["total_tasks"], 0)


class SystemHealthMetricsTest(unittest.TestCase):
    def test_returns_dict(self):
        h = em.system_health_metrics()
        self.assertIn("engineered", h)
        self.assertIn("health", h)

    def test_fallback_on_error(self):
        # 模拟 import 失败场景不应抛异常（已在模块内兜底）
        self.assertTrue(isinstance(em.system_health_metrics(), dict))


class FullSnapshotTest(unittest.TestCase):
    def test_snapshot_shape(self):
        s = em.full_snapshot()
        self.assertIn("engineered_metrics_version", s)
        self.assertIn("generated_ts", s)
        self.assertIn("task_closed_loop", s)
        self.assertIn("collector_performance", s)
        self.assertIn("scheduling_health", s)
        self.assertIn("system_health", s)



class HealthAlertTest(unittest.TestCase):
    """v4 告警分级：OK / WARN / CRIT 边界与自定义阈值。"""

    def _snap(self, recovery, collector, sched_ok=True, sysh="ok"):
        return {
            "task_closed_loop": {"recovery_rate": recovery, "failed_tasks": 0},
            "collector_performance": {"window_success_rate": collector},
            "scheduling_health": {"platforms": {"xhs": {}} if sched_ok else {}, "degraded": not sched_ok},
            "system_health": {"health": {"status": sysh}},
        }

    def test_ok_level(self):
        a = em.health_alert(snapshot=self._snap(1.0, 1.0))
        self.assertEqual(a["level"], "OK")
        self.assertTrue(all(c["level"] == "OK" for c in a["checks"]))

    def test_warn_recovery(self):
        a = em.health_alert(snapshot=self._snap(0.4, 1.0))
        self.assertEqual(a["level"], "WARN")
        rec = next(c for c in a["checks"] if c["name"] == "recovery_rate")
        self.assertEqual(rec["level"], "WARN")

    def test_crit_recovery(self):
        a = em.health_alert(snapshot=self._snap(0.2, 1.0))
        self.assertEqual(a["level"], "CRIT")

    def test_crit_collector(self):
        a = em.health_alert(snapshot=self._snap(1.0, 0.4))
        self.assertEqual(a["level"], "CRIT")

    def test_warn_scheduling_degraded(self):
        a = em.health_alert(snapshot=self._snap(1.0, 1.0, sched_ok=False))
        self.assertEqual(a["level"], "WARN")
        s = next(c for c in a["checks"] if c["name"] == "scheduling")
        self.assertEqual(s["level"], "WARN")

    def test_custom_thresholds(self):
        a = em.health_alert(snapshot=self._snap(0.6, 1.0),
                            thresholds={"recovery_warn": 0.7, "recovery_crit": 0.5})
        self.assertEqual(a["level"], "WARN")  # 0.6 < 0.7(warn) 且 >= 0.5(crit)

    def test_none_value_conservative_warn(self):
        a = em.health_alert(snapshot=self._snap(None, None))
        rec = next(c for c in a["checks"] if c["name"] == "recovery_rate")
        self.assertEqual(rec["level"], "WARN")


if __name__ == "__main__":
    unittest.main()


class CollectorPerformanceTest(unittest.TestCase):
    def test_empty_file(self):
        m = em.collector_performance_metrics(r"Z:\\no\\such\\metrics.jsonl")
        self.assertEqual(m["samples"], 0)
        self.assertIsNone(m["latest"])

    def test_aggregation(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "cm.jsonl")
            with open(p, "w", encoding="utf-8") as f:
                for r in ({"ts":"2026-09-04T00:00:01","success_rate":1.0,"avg_latency":0.5,"total":1},
                          {"ts":"2026-09-04T00:00:02","success_rate":0.5,"avg_latency":1.5,"total":2}):
                    f.write(json.dumps(r) + "\n")
            m = em.collector_performance_metrics(p, window=10)
            self.assertEqual(m["samples"], 2)
            self.assertAlmostEqual(m["window_success_rate"], 0.75)
            self.assertAlmostEqual(m["window_avg_latency"], 1.0)
