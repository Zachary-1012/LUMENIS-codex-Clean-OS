# -*- coding: utf-8 -*-
"""
ZBC Phase 2 - Runtime Guardian 统一收敛 测试套件
====================================================
覆盖：
  1. 租约获取/续期/过期
  2. 心跳超时检测
  3. checkpoint 保存/恢复
  4. 重试策略和退避
  5. 熔断器状态转换 (CLOSED -> OPEN -> HALF_OPEN)
  6. DLQ 入队/出队/重放
  7. 禁止无限重启（连续失败验证第4次后进入DLQ而非重启）
  8. Reaper 回收过期租约和僵死 worker
  9. 向后兼容（Legacy 模块 import 不破坏）

测试使用独立临时数据库，不污染生产 data/monitor.db。
"""
import os
import sys
import time
import json
import tempfile
import threading
import pytest

# 项目根目录
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# 使用独立测试数据库（不污染生产库）
_TEST_DB = os.path.join(tempfile.gettempdir(), f"rg_test_{os.getpid()}_{int(time.time())}.db")
os.environ["ZBC_RUNTIME_GUARDIAN_DB"] = _TEST_DB

import runtime_guardian as rg
from runtime_guardian import (
    RuntimeGuardian, CircuitBreaker, CircuitState, WorkerLease, Heartbeat,
    Checkpoint, RetryPolicy, DLQ, DLQStatus, WorkerStatus,
    init_db, get_guardian,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="function")
def guardian():
    """每个测试用独立 Guardian 实例 + 独立 DB"""
    db_path = os.path.join(tempfile.gettempdir(), f"rg_fx_{os.getpid()}_{int(time.time()*1000)}.db")
    g = RuntimeGuardian(name=f"test_{int(time.time()*1000)}", db_path=db_path)
    yield g
    # 清理
    try:
        os.remove(db_path)
    except OSError:
        pass


@pytest.fixture(scope="function")
def dlq():
    db_path = os.path.join(tempfile.gettempdir(), f"dlq_fx_{os.getpid()}_{int(time.time()*1000)}.db")
    q = DLQ(db_path=db_path)
    yield q
    try:
        os.remove(db_path)
    except OSError:
        pass


@pytest.fixture(scope="function")
def worker_id(guardian):
    return guardian.register_worker("test_worker", {"meta": "value"})


# ---------------------------------------------------------------------------
# 1. 租约获取/续期/过期
# ---------------------------------------------------------------------------
class TestLease:
    def test_acquire_lease_success(self, guardian, worker_id):
        lease = guardian.acquire_lease(worker_id, owner="node-1", ttl_seconds=60)
        assert lease is not None
        assert lease.lease_owner == "node-1"
        assert lease.expires_at > lease.acquired_at
        assert not lease.is_expired()

    def test_acquire_lease_duplicate_owner_renews(self, guardian, worker_id):
        """同一 owner 重复获取 = 续期"""
        lease1 = guardian.acquire_lease(worker_id, owner="node-1", ttl_seconds=60)
        time.sleep(0.05)
        lease2 = guardian.acquire_lease(worker_id, owner="node-1", ttl_seconds=120)
        assert lease2 is not None
        assert lease2.expires_at > lease1.expires_at

    def test_acquire_lease_conflict_owner_fails(self, guardian, worker_id):
        """不同 owner 在租约未过期时抢占失败"""
        guardian.acquire_lease(worker_id, owner="node-1", ttl_seconds=60)
        lease2 = guardian.acquire_lease(worker_id, owner="node-2", ttl_seconds=60)
        assert lease2 is None

    def test_lease_expiry_allows_new_owner(self, guardian, worker_id):
        """租约过期后，新 owner 可以获取"""
        guardian.acquire_lease(worker_id, owner="node-1", ttl_seconds=0.1)
        time.sleep(0.15)
        lease2 = guardian.acquire_lease(worker_id, owner="node-2", ttl_seconds=60)
        assert lease2 is not None
        assert lease2.lease_owner == "node-2"

    def test_renew_lease(self, guardian, worker_id):
        guardian.acquire_lease(worker_id, owner="node-1", ttl_seconds=60)
        time.sleep(0.05)
        renewed = guardian.renew_lease(worker_id, owner="node-1", ttl_seconds=120)
        assert renewed is not None
        assert renewed.renewed_at > renewed.acquired_at

    def test_renew_lease_wrong_owner_fails(self, guardian, worker_id):
        guardian.acquire_lease(worker_id, owner="node-1", ttl_seconds=60)
        renewed = guardian.renew_lease(worker_id, owner="node-2", ttl_seconds=60)
        assert renewed is None

    def test_release_lease(self, guardian, worker_id):
        guardian.acquire_lease(worker_id, owner="node-1", ttl_seconds=60)
        ok = guardian.release_lease(worker_id, owner="node-1")
        assert ok is True
        assert guardian.get_lease(worker_id) is None

    def test_release_lease_wrong_owner_fails(self, guardian, worker_id):
        guardian.acquire_lease(worker_id, owner="node-1", ttl_seconds=60)
        ok = guardian.release_lease(worker_id, owner="node-2")
        assert ok is False

    def test_lease_is_expired(self):
        lease = WorkerLease(lease_owner="x", acquired_at=time.time() - 10, expires_at=time.time() - 5)
        assert lease.is_expired()
        lease2 = WorkerLease(lease_owner="x", acquired_at=time.time(), expires_at=time.time() + 60)
        assert not lease2.is_expired()

    def test_lease_remaining_seconds(self):
        lease = WorkerLease(lease_owner="x", acquired_at=time.time(), expires_at=time.time() + 30)
        remaining = lease.remaining_seconds()
        assert 0 < remaining <= 30


# ---------------------------------------------------------------------------
# 2. 心跳超时检测
# ---------------------------------------------------------------------------
class TestHeartbeat:
    def test_heartbeat_updates_timestamp(self, guardian, worker_id):
        ok = guardian.heartbeat(worker_id)
        assert ok is True
        worker = guardian.get_worker(worker_id)
        assert worker["last_heartbeat_at"] != ""

    def test_heartbeat_missed_threshold(self):
        hb = Heartbeat(heartbeat_interval=0.05, missed_threshold=2)
        hb.beat()
        assert not hb.is_timed_out()
        time.sleep(0.15)  # 超过 interval * threshold = 0.1s
        assert hb.is_timed_out()

    def test_heartbeat_resets_missed_count_on_beat(self):
        hb = Heartbeat(heartbeat_interval=0.05, missed_threshold=2)
        hb.beat()
        time.sleep(0.15)
        assert hb.is_timed_out()
        hb.beat()
        assert hb.missed_count == 0
        assert not hb.is_timed_out()

    def test_is_worker_alive_after_heartbeat(self, guardian, worker_id):
        guardian.heartbeat(worker_id)
        assert guardian.is_worker_alive(worker_id) is True

    def test_worker_without_heartbeat_not_alive(self, guardian):
        wid = guardian.register_worker("no_hb")
        assert guardian.is_worker_alive(wid) is False

    def test_get_heartbeat_object(self, guardian, worker_id):
        guardian.heartbeat(worker_id)
        hb = guardian.get_heartbeat(worker_id)
        assert hb is not None
        assert hb.last_heartbeat_at > 0


# ---------------------------------------------------------------------------
# 3. checkpoint 保存/恢复
# ---------------------------------------------------------------------------
class TestCheckpoint:
    def test_save_checkpoint(self, guardian, worker_id):
        cp_id = guardian.save_checkpoint(
            run_id="run_001", worker_id=worker_id,
            position="page=3", state="active",
            metadata={"scroll": 3, "keyword": "太古汇"},
        )
        assert cp_id and len(cp_id) > 0
        worker = guardian.get_worker(worker_id)
        assert worker["checkpoint_id"] == cp_id
        assert worker["last_checkpoint_at"] != ""

    def test_get_latest_checkpoint(self, guardian, worker_id):
        guardian.save_checkpoint(run_id="run_002", worker_id=worker_id, position="page=1")
        time.sleep(0.02)
        guardian.save_checkpoint(run_id="run_002", worker_id=worker_id, position="page=5")
        latest = guardian.get_latest_checkpoint("run_002")
        assert latest is not None
        assert latest["position"] == "page=5"

    def test_get_latest_checkpoint_not_found(self, guardian):
        assert guardian.get_latest_checkpoint("nonexistent_run") is None

    def test_list_checkpoints(self, guardian, worker_id):
        for i in range(3):
            guardian.save_checkpoint(run_id="run_003", worker_id=worker_id, position=f"page={i}")
            time.sleep(0.02)
        cps = guardian.checkpoints.list_checkpoints("run_003")
        assert len(cps) == 3
        positions = {cp["position"] for cp in cps}
        assert positions == {"page=0", "page=1", "page=2"}

    def test_resume_from_checkpoint(self, guardian, worker_id):
        guardian.save_checkpoint(
            run_id="run_004", worker_id=worker_id,
            position="page=10", metadata={"kw": "test"},
        )
        resumed_data = []

        def resume_fn(cp):
            resumed_data.append(cp["position"])
            return cp["position"]

        found, result = guardian.checkpoints.resume_from_checkpoint("run_004", resume_fn)
        assert found is True
        assert result == "page=10"
        assert resumed_data == ["page=10"]

    def test_resume_from_checkpoint_not_found(self, guardian):
        found, result = guardian.checkpoints.resume_from_checkpoint("no_run", lambda cp: None)
        assert found is False
        assert result is None


# ---------------------------------------------------------------------------
# 4. 重试策略和退避
# ---------------------------------------------------------------------------
class TestRetryPolicy:
    def test_default_policy(self):
        p = RetryPolicy()
        assert p.max_retries == 3
        assert p.backoff_base == 2.0
        assert p.backoff_max == 60.0

    def test_backoff_exponential(self):
        p = RetryPolicy(backoff_base=2.0, backoff_max=60.0)
        assert p.backoff_seconds(1) == 2.0
        assert p.backoff_seconds(2) == 4.0
        assert p.backoff_seconds(3) == 8.0
        assert p.backoff_seconds(4) == 16.0

    def test_backoff_capped_at_max(self):
        p = RetryPolicy(backoff_base=10.0, backoff_max=30.0)
        assert p.backoff_seconds(1) == 10.0
        assert p.backoff_seconds(2) == 30.0  # 10^2=100 但封顶30
        assert p.backoff_seconds(3) == 30.0

    def test_backoff_zero_attempt(self):
        p = RetryPolicy()
        assert p.backoff_seconds(0) == 0.0

    def test_should_retry(self):
        p = RetryPolicy(max_retries=3)
        assert p.should_retry(0) is True
        assert p.should_retry(1) is True
        assert p.should_retry(2) is True
        assert p.should_retry(3) is False  # 第3次尝试后不再重试

    def test_execute_with_retry_success_first_try(self, guardian, worker_id):
        calls = []
        def task():
            calls.append(1)
            return "ok"
        result = guardian.execute_with_retry(worker_id, task)
        assert result == "ok"
        assert len(calls) == 1

    def test_execute_with_retry_succeeds_after_failures(self, guardian, worker_id):
        calls = {"n": 0}
        def task():
            calls["n"] += 1
            if calls["n"] < 3:
                raise ValueError(f"fail {calls['n']}")
            return "recovered"
        # 使用短退避
        guardian.set_retry_policy(RetryPolicy(max_retries=3, backoff_base=0.01, backoff_max=0.01))
        result = guardian.execute_with_retry(worker_id, task)
        assert result == "recovered"
        assert calls["n"] == 3

    def test_execute_with_retry_records_failure_count(self, guardian, worker_id):
        def task():
            raise RuntimeError("always fail")
        guardian.set_retry_policy(RetryPolicy(max_retries=2, backoff_base=0.01, backoff_max=0.01))
        with pytest.raises(RuntimeError, match="moved to DLQ"):
            guardian.execute_with_retry(worker_id, task, task_type="test")
        worker = guardian.get_worker(worker_id)
        assert worker["failure_count"] >= 2
        assert worker["retry_count"] >= 2


# ---------------------------------------------------------------------------
# 5. 熔断器状态转换
# ---------------------------------------------------------------------------
class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker(name="test", failure_threshold=3)
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_transitions_to_open_after_threshold(self):
        cb = CircuitBreaker(name="test", failure_threshold=3, reset_timeout=300)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_does_not_open_before_threshold(self):
        cb = CircuitBreaker(name="test", failure_threshold=5)
        for _ in range(4):
            cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_half_open_after_reset_timeout(self):
        cb = CircuitBreaker(name="test", failure_threshold=2, reset_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.allow_request() is True

    def test_half_open_success_closes(self):
        cb = CircuitBreaker(name="test", failure_threshold=2, reset_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(name="test", failure_threshold=2, reset_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(name="test", failure_threshold=5)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb._failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_execute_when_open_raises(self):
        cb = CircuitBreaker(name="test", failure_threshold=1, reset_timeout=300)
        cb.record_failure()
        with pytest.raises(RuntimeError, match="CircuitBreaker"):
            cb.execute(lambda: "should not run")

    def test_execute_success(self):
        cb = CircuitBreaker(name="test")
        result = cb.execute(lambda: 42)
        assert result == 42

    def test_execute_failure_records(self):
        cb = CircuitBreaker(name="test", failure_threshold=10)
        with pytest.raises(ValueError):
            cb.execute(lambda: (_ for _ in ()).throw(ValueError("test")))
        assert cb._failure_count == 1

    def test_stats(self):
        cb = CircuitBreaker(name="stat_test", failure_threshold=3)
        cb.record_failure()
        stats = cb.stats()
        assert stats["name"] == "stat_test"
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 1
        assert stats["failure_threshold"] == 3

    def test_reset(self):
        cb = CircuitBreaker(name="test", failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED
        assert cb._failure_count == 0


# ---------------------------------------------------------------------------
# 6. DLQ 入队/出队/重放
# ---------------------------------------------------------------------------
class TestDLQ:
    def test_enqueue(self, dlq):
        dlq_id = dlq.enqueue(
            worker_id="w1", run_id="r1", task_type="collect",
            payload={"keyword": "太古汇"}, error="timeout", error_type="TimeoutError",
        )
        assert dlq_id and len(dlq_id) > 0
        item = dlq.get(dlq_id)
        assert item is not None
        assert item["worker_id"] == "w1"
        assert item["status"] == DLQStatus.PENDING.value
        assert item["payload"]["keyword"] == "太古汇"

    def test_list_pending(self, dlq):
        for i in range(3):
            dlq.enqueue(worker_id=f"w{i}", task_type="test")
        pending = dlq.list_pending()
        assert len(pending) == 3

    def test_ack(self, dlq):
        dlq_id = dlq.enqueue(worker_id="w1", task_type="test")
        ok = dlq.ack(dlq_id)
        assert ok is True
        item = dlq.get(dlq_id)
        assert item["status"] == DLQStatus.DONE.value
        assert item["resolved_at"] != ""

    def test_mark_processing(self, dlq):
        dlq_id = dlq.enqueue(worker_id="w1", task_type="test")
        ok = dlq.mark_processing(dlq_id)
        assert ok is True
        item = dlq.get(dlq_id)
        assert item["status"] == DLQStatus.PROCESSING.value

    def test_fail_retry_increments_attempts(self, dlq):
        dlq_id = dlq.enqueue(worker_id="w1", task_type="test", max_attempts=3)
        dlq.fail_retry(dlq_id, error="err1", error_type="E1")
        item = dlq.get(dlq_id)
        assert item["attempts"] == 1
        assert item["status"] == DLQStatus.PENDING.value

    def test_fail_retry_marks_dead_after_max(self, dlq):
        dlq_id = dlq.enqueue(worker_id="w1", task_type="test", max_attempts=2)
        dlq.fail_retry(dlq_id, error="err1")
        dlq.fail_retry(dlq_id, error="err2")
        item = dlq.get(dlq_id)
        assert item["attempts"] == 2
        assert item["status"] == DLQStatus.DEAD.value

    def test_stats(self, dlq):
        id1 = dlq.enqueue(worker_id="w1", task_type="test")
        id2 = dlq.enqueue(worker_id="w2", task_type="test")
        dlq.ack(id1)
        stats = dlq.stats()
        assert stats["total"] == 2
        assert stats["pending"] == 1
        assert stats["done"] == 1

    def test_replay_success(self, dlq):
        dlq.enqueue(worker_id="w1", task_type="test", payload={"val": 1})
        dlq.enqueue(worker_id="w2", task_type="test", payload={"val": 2})
        replayed = []
        def handler(payload):
            replayed.append(payload["val"])
        ok, fail = dlq.replay(handler)
        assert ok == 2
        assert fail == 0
        assert sorted(replayed) == [1, 2]

    def test_replay_failure(self, dlq):
        dlq.enqueue(worker_id="w1", task_type="test", payload={"val": 1}, max_attempts=5)
        def handler(payload):
            raise RuntimeError("replay failed")
        ok, fail = dlq.replay(handler)
        assert ok == 0
        assert fail == 1

    def test_get_nonexistent(self, dlq):
        assert dlq.get("nonexistent") is None


# ---------------------------------------------------------------------------
# 7. 禁止无限重启（核心验收）
# ---------------------------------------------------------------------------
class TestNoInfiniteRestart:
    def test_continuous_failures_go_to_dlq_not_infinite_retry(self, guardian, worker_id):
        """
        模拟连续失败：默认 max_retries=3，第4次失败后应进入 DLQ，
        抛出 RuntimeError 且不再自动重试。
        """
        call_count = {"n": 0}
        def always_fail():
            call_count["n"] += 1
            raise ConnectionError(f"failure #{call_count['n']}")

        guardian.set_retry_policy(RetryPolicy(
            max_retries=3, backoff_base=0.01, backoff_max=0.01,
            circuit_breaker_threshold=10,  # 不让熔断器提前介入
        ))

        with pytest.raises(RuntimeError, match="moved to DLQ"):
            guardian.execute_with_retry(worker_id, always_fail, task_type="collect")

        # 验证：总共调用了 max_retries+1 = 4 次（初始1次 + 3次重试），不是无限
        assert call_count["n"] == 4, f"Expected 4 calls, got {call_count['n']}"

        # 验证：DLQ 中有记录
        dlq_stats = guardian.dlq.stats()
        assert dlq_stats["pending"] >= 1

        # 验证：worker 状态为 FAILED
        worker = guardian.get_worker(worker_id)
        assert worker["status"] == WorkerStatus.FAILED.value
        assert "max_retries_exceeded" in worker["recovery_reason"]

    def test_circuit_breaker_blocks_after_5_failures(self, guardian, worker_id):
        """
        熔断器阈值=5：连续5次失败后熔断，后续请求直接拒绝并入 DLQ，
        不再执行实际任务（禁止无限重启）。
        """
        guardian.set_retry_policy(RetryPolicy(
            max_retries=1, backoff_base=0.01, backoff_max=0.01,
            circuit_breaker_threshold=5,
        ))
        cb = guardian.get_circuit_breaker(worker_id)

        # 先手动触发5次失败让熔断器打开
        for _ in range(5):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # 此时 execute_with_retry 应直接被熔断器拦截，不调用 func
        call_count = {"n": 0}
        def should_not_run():
            call_count["n"] += 1
            return "ok"

        with pytest.raises(RuntimeError, match="CircuitBreaker OPEN"):
            guardian.execute_with_retry(worker_id, should_not_run)

        assert call_count["n"] == 0, "Function should NOT be called when circuit is OPEN"

    def test_dlq_prevents_data_loss(self, guardian, worker_id):
        """失败任务进入 DLQ 后可被重放，数据不丢失"""
        guardian.set_retry_policy(RetryPolicy(
            max_retries=1, backoff_base=0.01, backoff_max=0.01,
            circuit_breaker_threshold=10,
        ))

        def fail_task():
            raise ValueError("payload must be preserved")

        with pytest.raises(RuntimeError):
            guardian.execute_with_retry(
                worker_id, fail_task, task_type="collect",
                payload={"keyword": "太古汇", "page": 5},
                run_id="run_dlq_test",
            )

        # DLQ 中应能找到该任务且 payload 完整
        pending = guardian.dlq.list_pending()
        assert len(pending) >= 1
        target = [p for p in pending if p.get("run_id") == "run_dlq_test"]
        assert len(target) == 1
        assert target[0]["payload"]["keyword"] == "太古汇"
        assert target[0]["payload"]["page"] == 5


# ---------------------------------------------------------------------------
# 8. Reaper 回收
# ---------------------------------------------------------------------------
class TestReaper:
    def test_reap_expired_leases(self, guardian):
        wid = guardian.register_worker("reap_test")
        guardian.acquire_lease(wid, owner="node-1", ttl_seconds=0.05)
        time.sleep(0.1)
        result = guardian.reap_now(heartbeat_timeout=999)
        assert wid in result["reaped_leases"]
        worker = guardian.get_worker(wid)
        assert worker["lease_owner"] == ""
        assert worker["status"] == WorkerStatus.DEAD.value

    def test_reap_zombie_workers(self, guardian):
        wid = guardian.register_worker("zombie_test")
        guardian.acquire_lease(wid, owner="node-1", ttl_seconds=60)
        guardian.heartbeat(wid)
        # 手动把心跳时间改到很久以前
        guardian._update_worker_fields(wid, last_heartbeat_at="2020-01-01 00:00:00")
        result = guardian.reap_now(heartbeat_timeout=1.0)
        assert wid in result["reaped_zombies"]
        worker = guardian.get_worker(wid)
        assert worker["status"] == WorkerStatus.DEAD.value
        assert worker["recovery_reason"] == "heartbeat_timeout"

    def test_reaper_does_not_touch_healthy_workers(self, guardian, worker_id):
        guardian.acquire_lease(worker_id, owner="node-1", ttl_seconds=60)
        guardian.heartbeat(worker_id)
        result = guardian.reap_now(heartbeat_timeout=60)
        assert worker_id not in result["reaped_leases"]
        assert worker_id not in result["reaped_zombies"]


# ---------------------------------------------------------------------------
# 9. 健康检查与状态
# ---------------------------------------------------------------------------
class TestHealthCheck:
    def test_health_check_returns_structure(self, guardian):
        health = guardian.health_check()
        assert "timestamp" in health
        assert "overall" in health
        assert "workers" in health
        assert "dlq" in health
        assert "circuit_breakers" in health

    def test_health_check_overall_healthy(self, guardian):
        health = guardian.health_check()
        assert health["overall"] == "healthy"

    def test_health_check_degraded_with_failed_worker(self, guardian, worker_id):
        guardian.update_worker_status(worker_id, WorkerStatus.FAILED, reason="test")
        health = guardian.health_check()
        assert health["overall"] == "degraded"
        assert health["workers"]["failed"] >= 1


# ---------------------------------------------------------------------------
# 10. supervised_worker 上下文管理器
# ---------------------------------------------------------------------------
class TestSupervisedWorker:
    def test_context_manager_registers_and_releases(self, guardian):
        with guardian.supervised_worker("ctx_worker", owner="test-node") as (wid, lease):
            assert wid is not None
            assert lease is not None
            assert lease.lease_owner == "test-node"
            worker = guardian.get_worker(wid)
            assert worker["status"] == WorkerStatus.RUNNING.value
        # 退出后租约释放
        assert guardian.get_lease(wid) is None

    def test_context_manager_releases_on_exception(self, guardian):
        wid_out = []
        with pytest.raises(ValueError):
            with guardian.supervised_worker("ctx_err", owner="test-node") as (wid, lease):
                wid_out.append(wid)
                raise ValueError("test exception")
        assert guardian.get_lease(wid_out[0]) is None


# ---------------------------------------------------------------------------
# 11. 向后兼容验证
# ---------------------------------------------------------------------------
class TestBackwardCompatibility:
    def test_legacy_system_guardian_import(self):
        import system_guardian
        assert hasattr(system_guardian, 'health_check')
        assert hasattr(system_guardian, 'global_exception_handler')
        assert hasattr(system_guardian, 'auto_recovery')
        assert hasattr(system_guardian, 'load_status')
        assert hasattr(system_guardian, 'save_status')

    def test_legacy_system_guardian_health_check_runs(self):
        import system_guardian
        result = system_guardian.health_check()
        assert 'status' in result
        assert 'checks' in result

    def test_legacy_stability_monitor_import(self):
        import stability_monitor
        assert hasattr(stability_monitor, 'StabilityMonitor')
        assert hasattr(stability_monitor, 'get_stability_monitor')
        sm = stability_monitor.StabilityMonitor()
        assert sm is not None

    def test_legacy_system_watchdog_import(self):
        import system_watchdog
        assert hasattr(system_watchdog, 'SystemWatchdog')
        assert hasattr(system_watchdog, 'main')
        wd = system_watchdog.SystemWatchdog()
        assert wd is not None

    def test_runtime_guardian_independent_import(self):
        """runtime_guardian 可独立 import，不依赖个人路径。
        reload 会重建模块内所有类对象，导致 ai_channel 等下游模块继承链断裂。
        因此保存关键类对象，断言后立即恢复，避免跨模块污染。"""
        import importlib
        import runtime_guardian
        # 保存 reload 前的关键类对象（下游模块如 ai_channel 引用这些对象）
        _saved = {
            k: getattr(runtime_guardian, k)
            for k in ('CircuitBreaker', 'CircuitState', 'RuntimeGuardian',
                      'DLQ', 'WorkerStatus', 'RetryPolicy', 'DLQStatus')
            if hasattr(runtime_guardian, k)
        }
        try:
            importlib.reload(runtime_guardian)
            assert hasattr(runtime_guardian, 'RuntimeGuardian')
            assert hasattr(runtime_guardian, 'CircuitBreaker')
            assert hasattr(runtime_guardian, 'DLQ')
        finally:
            # 恢复原始类对象，保持下游模块继承链有效
            for k, v in _saved.items():
                setattr(runtime_guardian, k, v)

    def test_db_tables_created(self, guardian):
        """验证三张新表已创建且不破坏现有表"""
        import sqlite3
        conn = sqlite3.connect(guardian._db_path)
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()]
        conn.close()
        assert 'runtime_guardian_workers' in tables
        assert 'runtime_guardian_checkpoints' in tables
        assert 'runtime_guardian_dlq' in tables

    def test_get_instance_singleton(self):
        g1 = get_guardian("singleton_test")
        g2 = get_guardian("singleton_test")
        assert g1 is g2

    def test_different_instances_different_names(self):
        g1 = get_guardian("inst_a")
        g2 = get_guardian("inst_b")
        assert g1 is not g2


# ---------------------------------------------------------------------------
# 12. Worker 管理
# ---------------------------------------------------------------------------
class TestWorkerManagement:
    def test_register_worker(self, guardian):
        wid = guardian.register_worker("my_worker", {"key": "val"})
        assert wid is not None
        worker = guardian.get_worker(wid)
        assert worker["worker_name"] == "my_worker"
        assert worker["status"] == WorkerStatus.IDLE.value
        assert worker["metadata"]["key"] == "val"

    def test_get_nonexistent_worker(self, guardian):
        assert guardian.get_worker("nonexistent") is None

    def test_list_workers(self, guardian):
        guardian.register_worker("w1")
        guardian.register_worker("w2")
        workers = guardian.list_workers()
        assert len(workers) >= 2

    def test_list_workers_by_status(self, guardian, worker_id):
        guardian.update_worker_status(worker_id, WorkerStatus.RUNNING, reason="test")
        running = guardian.list_workers(status=WorkerStatus.RUNNING.value)
        assert any(w["worker_id"] == worker_id for w in running)

    def test_update_worker_status(self, guardian, worker_id):
        ok = guardian.update_worker_status(worker_id, WorkerStatus.FAILED, reason="test fail")
        assert ok is True
        worker = guardian.get_worker(worker_id)
        assert worker["status"] == WorkerStatus.FAILED.value
        assert worker["recovery_reason"] == "test fail"
