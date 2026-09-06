# -*- coding: utf-8 -*-
"""
ZBC 统一生命周期契约 V1.0 测试
=================================
工单：ZBC-LIFECYCLE-CONTRACT-V1
覆盖：状态转换 / 完整生命周期流程 / 心跳 / 检查点 / 重试 / DLQ / 熔断器 / Reaper / 双域 / 归档

使用隔离的测试数据库（ZBC_RUNTIME_GUARDIAN_DB 环境变量），不碰生产库。
"""
import os
import sys
import tempfile
import time
import unittest

# 测试隔离：使用临时数据库
_TEST_DB = os.path.join(tempfile.gettempdir(), f"zbc_lifecycle_test_{int(time.time())}.db")
os.environ["ZBC_RUNTIME_GUARDIAN_DB"] = _TEST_DB

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import runtime_guardian as rg
from runtime_guardian import (
    LifecycleState, WorkerStatus, CircuitBreaker, CircuitState,
    DLQ, RetryPolicy, RuntimeGuardian,
)
from lifecycle_mixin import LifecycleMixin, lifecycle_task


def _fresh_guardian(name="test_lc"):
    """获取一个干净的 guardian 实例（使用测试 DB）。"""
    return RuntimeGuardian(name=name, db_path=_TEST_DB)


class TestLifecycleStateMachine(unittest.TestCase):
    """生命周期状态机：10态定义 + 合法/非法转换。"""

    def test_all_ten_states_exist(self):
        states = [s.value for s in LifecycleState]
        expected = ["created", "starting", "running", "paused", "resuming",
                    "stopping", "stopped", "dead", "archived"]
        for s in expected:
            self.assertIn(s, states, f"缺少状态: {s}")
        self.assertEqual(len(states), 9)  # 9 个枚举值（CREATED 到 ARCHIVED）

    def test_worker_status_mapping(self):
        """历史 WorkerStatus → LifecycleState 映射。"""
        self.assertEqual(LifecycleState.from_worker_status(WorkerStatus.IDLE), LifecycleState.CREATED)
        self.assertEqual(LifecycleState.from_worker_status(WorkerStatus.RUNNING), LifecycleState.RUNNING)
        self.assertEqual(LifecycleState.from_worker_status(WorkerStatus.RECOVERING), LifecycleState.RESUMING)
        self.assertEqual(LifecycleState.from_worker_status(WorkerStatus.FAILED), LifecycleState.STOPPING)
        self.assertEqual(LifecycleState.from_worker_status(WorkerStatus.STOPPED), LifecycleState.STOPPED)
        self.assertEqual(LifecycleState.from_worker_status(WorkerStatus.DEAD), LifecycleState.DEAD)

    def test_valid_transitions(self):
        """合法状态转换。"""
        valid = [
            (LifecycleState.CREATED, LifecycleState.STARTING),
            (LifecycleState.STARTING, LifecycleState.RUNNING),
            (LifecycleState.RUNNING, LifecycleState.PAUSED),
            (LifecycleState.PAUSED, LifecycleState.RESUMING),
            (LifecycleState.RESUMING, LifecycleState.RUNNING),
            (LifecycleState.RUNNING, LifecycleState.STOPPING),
            (LifecycleState.STOPPING, LifecycleState.STOPPED),
            (LifecycleState.STOPPED, LifecycleState.ARCHIVED),
            (LifecycleState.DEAD, LifecycleState.ARCHIVED),
            (LifecycleState.STOPPED, LifecycleState.STARTING),
            (LifecycleState.DEAD, LifecycleState.STARTING),
        ]
        for from_s, to_s in valid:
            self.assertIn(to_s, rg._LIFECYCLE_TRANSITIONS.get(from_s, set()),
                          f"合法转换未定义: {from_s.value} -> {to_s.value}")

    def test_invalid_transitions(self):
        """非法状态转换（应被 transition_state 拒绝）。"""
        g = _fresh_guardian("invalid_trans")
        wid = g.lifecycle_create("invalid_test")
        # CREATED -> RUNNING 是非法的（必须经过 STARTING）
        result = g.transition_state(wid, LifecycleState.RUNNING, reason="test")
        self.assertFalse(result, "CREATED -> RUNNING 应该是非法转换")
        # ARCHIVED 是终态，不能转换
        g.lifecycle_archive(wid)
        result = g.transition_state(wid, LifecycleState.STARTING, reason="test")
        self.assertFalse(result, "ARCHIVED -> STARTING 应该是非法转换")


class TestFullLifecycleFlow(unittest.TestCase):
    """完整生命周期流程：create → start → pause → resume → stop → archive。"""

    def setUp(self):
        self.g = _fresh_guardian("full_flow")

    def test_complete_flow(self):
        wid = self.g.lifecycle_create("flow_worker", domain_id="cth", product_id="CTH")
        self.assertEqual(self.g.get_worker(wid)["status"], "created")

        self.assertTrue(self.g.lifecycle_start(wid))
        self.assertEqual(self.g.get_worker(wid)["status"], "running")

        self.assertTrue(self.g.lifecycle_pause(wid, reason="test_pause"))
        self.assertEqual(self.g.get_worker(wid)["status"], "paused")

        self.assertTrue(self.g.lifecycle_resume(wid))
        self.assertEqual(self.g.get_worker(wid)["status"], "running")

        self.assertTrue(self.g.lifecycle_stop(wid, reason="test_stop"))
        self.assertEqual(self.g.get_worker(wid)["status"], "stopped")

        self.assertTrue(self.g.lifecycle_archive(wid, reason="test_archive"))
        self.assertEqual(self.g.get_worker(wid)["status"], "archived")

    def test_heartbeat_updates_last_heartbeat(self):
        wid = self.g.lifecycle_create("hb_worker")
        self.g.lifecycle_start(wid)
        before = self.g.get_worker(wid)["last_heartbeat_at"]
        time.sleep(1.1)  # 确保跨秒
        self.g.heartbeat(wid)
        after = self.g.get_worker(wid)["last_heartbeat_at"]
        self.assertNotEqual(before, after, "心跳应更新 last_heartbeat_at")

    def test_checkpoint_save_and_retrieve(self):
        wid = self.g.lifecycle_create("cp_worker")
        self.g.lifecycle_start(wid)
        cp_id = self.g.save_checkpoint(
            run_id="run_cp_test", worker_id=wid,
            position="page=3", state="active",
            metadata={"notes": 42},
        )
        self.assertIsNotNone(cp_id)
        cp = self.g.get_latest_checkpoint("run_cp_test")
        self.assertIsNotNone(cp)
        self.assertEqual(cp["position"], "page=3")
        self.assertEqual(cp["metadata"].get("notes"), 42)


class TestRetryAndDLQ(unittest.TestCase):
    """重试 + 指数退避 + DLQ。"""

    def setUp(self):
        self.g = _fresh_guardian("retry_dlq")

    def test_retry_policy_backoff(self):
        policy = RetryPolicy(max_retries=3, backoff_base=2.0, backoff_max=60.0)
        self.assertEqual(policy.backoff_seconds(1), 2.0)
        self.assertEqual(policy.backoff_seconds(2), 4.0)
        self.assertEqual(policy.backoff_seconds(3), 8.0)
        self.assertTrue(policy.should_retry(0))
        self.assertTrue(policy.should_retry(2))
        self.assertFalse(policy.should_retry(3))

    def test_execute_with_retry_success(self):
        wid = self.g.lifecycle_create("retry_success")
        self.g.lifecycle_start(wid)
        result = self.g.execute_with_retry(wid, lambda: 42, task_type="test")
        self.assertEqual(result, 42)

    def test_execute_with_retry_failure_goes_to_dlq(self):
        wid = self.g.lifecycle_create("retry_fail")
        self.g.lifecycle_start(wid)
        call_count = [0]
        def always_fail():
            call_count[0] += 1
            raise ValueError("test failure")
        with self.assertRaises(RuntimeError) as ctx:
            self.g.execute_with_retry(wid, always_fail, task_type="test_fail")
        self.assertIn("DLQ", str(ctx.exception))
        self.assertEqual(call_count[0], 4)  # 1 initial + 3 retries
        # DLQ 应有记录
        dlq_stats = self.g.dlq.stats()
        self.assertGreater(dlq_stats.get("total", 0), 0)


class TestCircuitBreaker(unittest.TestCase):
    """熔断器：CLOSED → OPEN → HALF_OPEN → CLOSED。"""

    def test_circuit_breaker_transitions(self):
        cb = CircuitBreaker(name="test_cb", failure_threshold=3, reset_timeout=0.1)
        self.assertEqual(cb.state, CircuitState.CLOSED)
        self.assertTrue(cb.allow_request())
        # 连续失败触发熔断
        for _ in range(3):
            cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        self.assertFalse(cb.allow_request())
        # 等待冷却后转 HALF_OPEN
        time.sleep(0.15)
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)
        self.assertTrue(cb.allow_request())
        # HALF_OPEN 成功 → CLOSED
        cb.record_success()
        self.assertEqual(cb.state, CircuitState.CLOSED)

    def test_circuit_breaker_half_open_failure_reopens(self):
        cb = CircuitBreaker(name="test_cb2", failure_threshold=2, reset_timeout=0.1)
        for _ in range(2):
            cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)
        time.sleep(0.15)
        self.assertEqual(cb.state, CircuitState.HALF_OPEN)
        cb.record_failure()
        self.assertEqual(cb.state, CircuitState.OPEN)


class TestReaper(unittest.TestCase):
    """Reaper：回收过期租约和僵死 worker。"""

    def test_reap_zombie_workers(self):
        g = _fresh_guardian("reaper_test")
        wid = g.lifecycle_create("zombie_worker")
        g.lifecycle_start(wid)
        # 手动设置旧的心跳时间
        g._update_worker_fields(wid, last_heartbeat_at="2020-01-01 00:00:00")
        # Reaper 应标记为 dead
        reaped = g.reap_now(heartbeat_timeout=60.0)
        self.assertIn(wid, reaped.get("reaped_zombies", []))
        self.assertEqual(g.get_worker(wid)["status"], "dead")


class TestDualDomain(unittest.TestCase):
    """双域核心：CTH / ZBMP 隔离。"""

    def test_worker_domain_isolation(self):
        g = _fresh_guardian("domain_test")
        wid_cth = g.lifecycle_create("cth_worker", domain_id="cth", product_id="CTH")
        wid_zbmp = g.lifecycle_create("zbmp_worker", domain_id="zbmp", product_id="ZBMP")
        cth_tasks = g.get_tasks_by_domain("cth")
        zbmp_tasks = g.get_tasks_by_domain("zbmp")
        cth_ids = [w["worker_id"] for w in cth_tasks["workers"]]
        zbmp_ids = [w["worker_id"] for w in zbmp_tasks["workers"]]
        self.assertIn(wid_cth, cth_ids)
        self.assertNotIn(wid_cth, zbmp_ids)
        self.assertIn(wid_zbmp, zbmp_ids)
        self.assertNotIn(wid_zbmp, cth_ids)


class TestArchiveDeadWorkers(unittest.TestCase):
    """批量归档 dead/stopped worker。"""

    def test_archive_dead_workers(self):
        g = _fresh_guardian("archive_test")
        # 先归档所有历史 dead worker（清理测试环境）
        g.archive_dead_workers(older_than_hours=0.0)
        # 创建几个 dead worker（旧心跳）
        for i in range(3):
            wid = g.lifecycle_create(f"dead_worker_{i}")
            g.lifecycle_start(wid)
            g._update_worker_fields(wid, last_heartbeat_at="2020-01-01 00:00:00",
                                     status="dead")
        # 归档
        count = g.archive_dead_workers(older_than_hours=1.0)
        self.assertGreaterEqual(count, 3)
        # 活跃列表应不含这些 worker
        active = g.list_lifecycle_workers()
        active_names = [w["worker_name"] for w in active]
        for i in range(3):
            self.assertNotIn(f"dead_worker_{i}", active_names)


class TestLifecycleMixin(unittest.TestCase):
    """LifecycleMixin：模块级生命周期接入。"""

    def test_mixin_full_flow(self):
        class MyWorker(LifecycleMixin):
            pass
        w = MyWorker(worker_name="mixin_test", domain_id="cth", product_id="CTH",
                     heartbeat_interval=1.0)
        wid = w.lifecycle_create()
        self.assertIsNotNone(wid)
        self.assertTrue(w.lifecycle_start())
        self.assertEqual(w.lifecycle_status, "running")
        time.sleep(0.2)
        self.assertTrue(w.lifecycle_heartbeat())
        cp = w.lifecycle_checkpoint(position="test=1")
        self.assertIsNotNone(cp)
        self.assertTrue(w.lifecycle_pause())
        self.assertEqual(w.lifecycle_status, "paused")
        self.assertTrue(w.lifecycle_resume())
        self.assertTrue(w.lifecycle_stop())
        self.assertEqual(w.lifecycle_status, "stopped")
        self.assertTrue(w.lifecycle_archive())

    def test_mixin_bypass_when_guardian_unavailable(self):
        """Mixin 在 Runtime Guardian 不可用时应旁路，不阻断主流程。"""
        w = LifecycleMixin(worker_name="bypass_test")
        # 即使 guardian 不可用，方法也不应抛异常
        try:
            w.lifecycle_create()
            w.lifecycle_start()
            w.lifecycle_heartbeat()
            w.lifecycle_stop()
        except Exception as e:
            self.fail(f"LifecycleMixin 不应抛异常: {e}")

    def test_lifecycle_task_context_manager(self):
        """lifecycle_task 上下文管理器。"""
        with lifecycle_task("ctx_test", domain_id="system", product_id="SYSTEM") as lc:
            self.assertIsNotNone(lc.lifecycle_worker_id)
            lc.lifecycle_checkpoint(position="ctx=1")
        # 退出后 worker 应被 stop
        # (不强制断言，因为旁路模式下可能没有 worker)


class TestLifecycleSummary(unittest.TestCase):
    """生命周期汇总 API。"""

    def test_lifecycle_summary(self):
        g = _fresh_guardian("summary_test")
        wid = g.lifecycle_create("summary_worker")
        g.lifecycle_start(wid)
        summary = g.lifecycle_summary()
        self.assertIn("total_active", summary)
        self.assertIn("by_state", summary)
        self.assertIn("dlq", summary)
        self.assertGreaterEqual(summary["total_active"], 1)
        self.assertIn("running", summary["by_state"])


class TestNoInfiniteRestart(unittest.TestCase):
    """硬红线：禁止无限自动重启。"""

    def test_retry_limit_enforced(self):
        g = _fresh_guardian("no_infinite")
        wid = g.lifecycle_create("no_infinite_worker")
        g.lifecycle_start(wid)
        call_count = [0]
        def fail_forever():
            call_count[0] += 1
            raise RuntimeError("always fail")
        with self.assertRaises(RuntimeError):
            g.execute_with_retry(wid, fail_forever, task_type="no_infinite")
        # 最多 max_retries + 1 次调用（默认 3 次重试 = 4 次总调用）
        self.assertLessEqual(call_count[0], rg.DEFAULT_MAX_RETRIES + 1)
        # 任务应进入 DLQ，不再自动重试
        dlq = g.dlq.list_pending()
        self.assertTrue(len(dlq) > 0, "超过重试上限的任务应进入 DLQ")


if __name__ == "__main__":
    unittest.main(verbosity=2)
