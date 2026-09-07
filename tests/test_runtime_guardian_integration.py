# -*- coding: utf-8 -*-
"""
ZBC Runtime Guardian — 采集链路集成测试
==========================================
工单：ZBC-PHASE2-RUNTIME-GUARDIAN Shard B
覆盖场景：
  1. 正常采集 → 心跳 → checkpoint → 完成
  2. 采集失败 → 重试 → 超过上限 → DLQ（不阻塞主链路）
  3. worker 假死 → 心跳超时 → Reaper 检测 → 标记 DEAD
  4. CircuitBreaker 触发 → 冷却 → HALF_OPEN → 恢复
  5. ai_channel CircuitBreaker 收敛验证（继承 runtime_guardian）
  6. collector_automation 生命周期：注册→租约→心跳→清理
  7. collector.collect_all 旁路参数：不传 guardian 时行为不变

测试使用独立临时数据库，不污染生产 data/monitor.db。
所有采集动作均 mock，不启动真实浏览器。
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

# 使用独立测试数据库（必须在 import runtime_guardian 之前设置）
_TEST_DB = os.path.join(tempfile.gettempdir(), f"rg_integ_{os.getpid()}_{int(time.time())}.db")
os.environ["ZBC_RUNTIME_GUARDIAN_DB"] = _TEST_DB

import runtime_guardian as rg
from runtime_guardian import (
    RuntimeGuardian, CircuitBreaker, CircuitState, WorkerStatus,
    RetryPolicy, DLQStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="function")
def guardian():
    """每个测试用独立 Guardian 实例 + 独立 DB"""
    db_path = os.path.join(tempfile.gettempdir(), f"rg_integ_fx_{os.getpid()}_{int(time.time()*1000)}.db")
    g = RuntimeGuardian(name=f"integ_{int(time.time()*1000)}", db_path=db_path)
    # 短退避策略，避免测试等待
    g.set_retry_policy(RetryPolicy(
        max_retries=2, backoff_base=0.01, backoff_max=0.01,
        circuit_breaker_threshold=10,
    ))
    yield g
    try:
        os.remove(db_path)
    except OSError:
        pass


@pytest.fixture(scope="function")
def worker_id(guardian):
    return guardian.register_worker("integ_collector", {"platform": "xhs"})


# ---------------------------------------------------------------------------
# 场景1：正常采集 → 心跳 → checkpoint → 完成
# ---------------------------------------------------------------------------
class TestNormalCollectionLifecycle:
    def test_heartbeat_checkpoint_complete_flow(self, guardian, worker_id):
        """模拟正常采集：获取租约→心跳→逐关键词checkpoint→完成→释放租约"""
        owner = f"test-pid-{os.getpid()}"
        lease = guardian.acquire_lease(worker_id, owner, ttl_seconds=60)
        assert lease is not None
        assert lease.lease_owner == owner

        # 模拟3个关键词采集
        run_id = f"run_normal_{int(time.time())}"
        for idx in range(3):
            guardian.heartbeat(worker_id)
            guardian.save_checkpoint(
                run_id=run_id, worker_id=worker_id,
                position=f"keyword_idx={idx}",
                metadata={"keyword": f"kw_{idx}", "notes_so_far": idx * 5},
            )
            time.sleep(0.02)

        # 验证 worker 存活
        assert guardian.is_worker_alive(worker_id) is True

        # 验证 checkpoint 可追溯
        cps = guardian.checkpoints.list_checkpoints(run_id)
        assert len(cps) == 3
        latest = guardian.get_latest_checkpoint(run_id)
        assert latest["position"] == "keyword_idx=2"
        assert latest["metadata"]["notes_so_far"] == 10

        # 完成后释放租约
        guardian.save_checkpoint(
            run_id=run_id, worker_id=worker_id,
            position="completed notes=15", state="completed",
        )
        ok = guardian.release_lease(worker_id, owner)
        assert ok is True
        assert guardian.get_lease(worker_id) is None

        # 更新 worker 状态
        guardian.update_worker_status(worker_id, WorkerStatus.STOPPED, reason="completed")
        worker = guardian.get_worker(worker_id)
        assert worker["status"] == WorkerStatus.STOPPED.value

    def test_supervised_worker_context_manager(self, guardian):
        """supervised_worker 上下文管理器：自动注册/租约/心跳/释放"""
        with guardian.supervised_worker("ctx_collect", owner="test-node") as (wid, lease):
            assert wid is not None
            assert lease is not None
            assert lease.lease_owner == "test-node"
            guardian.heartbeat(wid)
            guardian.save_checkpoint(run_id="ctx_run", worker_id=wid, position="page=1")
            worker = guardian.get_worker(wid)
            assert worker["status"] == WorkerStatus.RUNNING.value
        # 退出后租约自动释放
        assert guardian.get_lease(wid) is None

    def test_resume_from_checkpoint(self, guardian, worker_id):
        """异常中断后可从 checkpoint 恢复位置"""
        run_id = "run_resume"
        guardian.save_checkpoint(
            run_id=run_id, worker_id=worker_id,
            position="keyword_idx=5 keyword=太古汇 活动 notes=23",
            metadata={"keyword_idx": 5, "keyword": "太古汇 活动", "notes_so_far": 23},
        )
        resumed = []

        def resume_fn(cp):
            resumed.append(cp["position"])
            resumed.append(cp["metadata"]["keyword_idx"])
            return cp["metadata"]["notes_so_far"]

        found, result = guardian.checkpoints.resume_from_checkpoint(run_id, resume_fn)
        assert found is True
        assert result == 23
        assert resumed[0] == "keyword_idx=5 keyword=太古汇 活动 notes=23"
        assert resumed[1] == 5


# ---------------------------------------------------------------------------
# 场景2：采集失败 → 重试 → 超过上限 → DLQ
# ---------------------------------------------------------------------------
class TestFailureRetryDLQ:
    def test_keyword_failure_goes_to_dlq(self, guardian, worker_id):
        """单个关键词持续失败：重试耗尽后进入 DLQ，不阻塞主链路"""
        call_count = {"n": 0}

        def failing_keyword():
            call_count["n"] += 1
            raise ConnectionError(f"keyword search failed #{call_count['n']}")

        # max_retries=2 → 总共尝试3次（1次初始 + 2次重试），第3次失败后入 DLQ
        with pytest.raises(RuntimeError, match="moved to DLQ"):
            guardian.execute_with_retry(
                worker_id, failing_keyword,
                task_type="xhs_keyword_search",
                payload={"keyword": "太古汇 投诉"},
                run_id="run_dlq_test",
            )

        assert call_count["n"] == 3  # 初始1次 + 2次重试
        # DLQ 中有记录
        pending = guardian.dlq.list_pending()
        target = [p for p in pending if p.get("run_id") == "run_dlq_test"]
        assert len(target) == 1
        assert target[0]["payload"]["keyword"] == "太古汇 投诉"
        assert target[0]["error_type"] == "ConnectionError"

        # worker 状态为 FAILED
        worker = guardian.get_worker(worker_id)
        assert worker["status"] == WorkerStatus.FAILED.value
        assert "max_retries_exceeded" in worker["recovery_reason"]

    def test_dlq_does_not_block_other_keywords(self, guardian, worker_id):
        """一个关键词进 DLQ 后，其他关键词可继续正常采集"""
        results = []

        def kw_success():
            results.append("success")
            return {"notes": [{"id": 1}]}

        def kw_fail():
            raise RuntimeError("always fail")

        # 关键词1成功
        r1 = guardian.execute_with_retry(worker_id, kw_success, task_type="search", run_id="run_mixed")
        assert r1["notes"][0]["id"] == 1

        # 关键词2失败进DLQ
        with pytest.raises(RuntimeError, match="moved to DLQ"):
            guardian.execute_with_retry(worker_id, kw_fail, task_type="search", run_id="run_mixed")

        # 关键词3仍然成功（DLQ不阻塞）
        r3 = guardian.execute_with_retry(worker_id, kw_success, task_type="search", run_id="run_mixed")
        assert r3["notes"][0]["id"] == 1

        assert results == ["success", "success"]

    def test_dlq_replay_success(self, guardian, worker_id):
        """DLQ 中的任务可被人工重放，成功后标记 done"""
        guardian.dlq.enqueue(
            worker_id=worker_id, run_id="run_replay",
            task_type="xhs_keyword_search",
            payload={"keyword": "太古汇", "replay": True},
            error="timeout", error_type="TimeoutError",
        )
        replayed = []

        def handler(payload):
            replayed.append(payload["keyword"])

        ok, fail = guardian.dlq.replay(handler, max_items=10)
        assert ok == 1
        assert fail == 0
        assert replayed == ["太古汇"]
        # 重放成功后状态为 done
        pending = guardian.dlq.list_pending()
        assert all(p.get("run_id") != "run_replay" for p in pending)


# ---------------------------------------------------------------------------
# 场景3：worker 假死 → 心跳超时 → Reaper 检测 → 恢复
# ---------------------------------------------------------------------------
class TestWorkerZombieDetection:
    def test_zombie_worker_reaped_by_heartbeat_timeout(self, guardian):
        """worker 心跳超时后被 Reaper 标记为 DEAD，租约自动释放"""
        wid = guardian.register_worker("zombie_collector")
        owner = "zombie-node"
        guardian.acquire_lease(wid, owner, ttl_seconds=120)
        guardian.heartbeat(wid)

        # 手动把心跳时间改到很久以前（模拟假死）
        guardian._update_worker_fields(wid, last_heartbeat_at="2020-01-01 00:00:00")

        # Reaper 检测
        result = guardian.reap_now(heartbeat_timeout=1.0)
        assert wid in result["reaped_zombies"]

        # worker 被标记 DEAD
        worker = guardian.get_worker(wid)
        assert worker["status"] == WorkerStatus.DEAD.value
        assert worker["recovery_reason"] == "heartbeat_timeout"
        # 租约已释放
        assert worker["lease_owner"] == ""

    def test_expired_lease_reaped(self, guardian):
        """租约过期后被 Reaper 回收"""
        wid = guardian.register_worker("lease_expired")
        guardian.acquire_lease(wid, owner="node-1", ttl_seconds=0.05)
        time.sleep(0.1)

        result = guardian.reap_now(heartbeat_timeout=999)
        assert wid in result["reaped_leases"]
        worker = guardian.get_worker(wid)
        assert worker["lease_owner"] == ""
        assert worker["status"] == WorkerStatus.DEAD.value

    def test_healthy_worker_not_reaped(self, guardian, worker_id):
        """健康 worker（有最新心跳）不会被 Reaper 误杀"""
        guardian.acquire_lease(worker_id, owner="node-1", ttl_seconds=60)
        guardian.heartbeat(worker_id)
        result = guardian.reap_now(heartbeat_timeout=60)
        assert worker_id not in result["reaped_zombies"]
        assert worker_id not in result["reaped_leases"]

    def test_reaper_background_thread(self, guardian):
        """Reaper 后台线程可启动并运行"""
        guardian.start_reaper(interval=0.1)
        assert guardian._reaper_running is True
        time.sleep(0.25)
        guardian.stop_reaper()
        assert guardian._reaper_running is False


# ---------------------------------------------------------------------------
# 场景4：CircuitBreaker 触发 → 冷却 → HALF_OPEN → 恢复
# ---------------------------------------------------------------------------
class TestCircuitBreakerFullCycle:
    def test_circuit_breaker_open_half_open_closed(self):
        """完整熔断周期：CLOSED → OPEN → HALF_OPEN → CLOSED"""
        cb = CircuitBreaker(name="integ_test", failure_threshold=2, reset_timeout=0.1)
        assert cb.state == rg.CircuitState.CLOSED
        assert cb.allow_request() is True

        # 2次失败 → OPEN
        cb.record_failure()
        cb.record_failure()
        assert cb.state == rg.CircuitState.OPEN
        assert cb.allow_request() is False

        # 冷却后 → HALF_OPEN
        time.sleep(0.15)
        assert cb.state == rg.CircuitState.HALF_OPEN
        assert cb.allow_request() is True

        # HALF_OPEN 成功 → CLOSED
        cb.record_success()
        assert cb.state == rg.CircuitState.CLOSED
        assert cb.allow_request() is True

    def test_half_open_failure_reopens(self):
        """HALF_OPEN 试探失败 → 重新 OPEN"""
        cb = CircuitBreaker(name="reopen_test", failure_threshold=2, reset_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == rg.CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == rg.CircuitState.OPEN

    def test_circuit_breaker_blocks_execute_when_open(self, guardian, worker_id):
        """熔断 OPEN 时 execute_with_retry 直接拒绝，不调用实际函数"""
        guardian.set_retry_policy(RetryPolicy(
            max_retries=1, backoff_base=0.01, backoff_max=0.01,
            circuit_breaker_threshold=3,
        ))
        cb = guardian.get_circuit_breaker(worker_id)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == rg.CircuitState.OPEN

        call_count = {"n": 0}

        def should_not_run():
            call_count["n"] += 1
            return "ok"

        with pytest.raises(RuntimeError, match="CircuitBreaker OPEN"):
            guardian.execute_with_retry(worker_id, should_not_run)

        assert call_count["n"] == 0  # 熔断时不调用

    def test_circuit_breaker_with_injected_clock(self):
        """now_func 注入支持（ai_channel 收敛后的测试兼容性）"""
        fake_time = [1000.0]
        cb = CircuitBreaker(
            name="clock_test", failure_threshold=1, reset_timeout=30,
            now_func=lambda: fake_time[0],
        )
        cb.record_failure()
        assert cb.state == rg.CircuitState.OPEN
        # 推进假时钟到冷却后
        fake_time[0] = 1050.0
        assert cb.state == rg.CircuitState.HALF_OPEN


# ---------------------------------------------------------------------------
# 场景5：ai_channel CircuitBreaker 收敛验证
# ---------------------------------------------------------------------------
class TestAICircuitBreakerConvergence:

    @pytest.fixture(autouse=True)
    def _reset_ai_channel_globals(self):
        """Reset ai_channel global breaker/provider cache before each test.

        Other test files may leave ai_channel.breaker or provider breaker cache in a
        modified state. Resetting before each test guarantees isolation.
        """
        import ai_channel
        # Save originals (other test files may monkeypatch CircuitBreaker/breaker)
        _saved_cb = getattr(ai_channel, 'CircuitBreaker', None)
        _saved_breaker = getattr(ai_channel, 'breaker', None)
        _saved_pbs = getattr(ai_channel, '_provider_breakers', None)
        # Ensure real CircuitBreaker class is visible
        if _saved_cb is None or not isinstance(_saved_cb, type):
            from runtime_guardian import CircuitBreaker as _RGB
            ai_channel.CircuitBreaker = _RGB
        # Guarantee a valid global breaker instance
        try:
            ai_channel.breaker = ai_channel.CircuitBreaker(fail_threshold=5, cooldown_sec=300)
        except Exception:
            pass
        # Clear provider breaker cache
        if isinstance(getattr(ai_channel, '_provider_breakers', None), dict):
            ai_channel._provider_breakers.clear()
        else:
            ai_channel._provider_breakers = {}
        yield
        # Restore originals after test
        if _saved_cb is not None:
            ai_channel.CircuitBreaker = _saved_cb
        if _saved_breaker is not None:
            ai_channel.breaker = _saved_breaker
        if _saved_pbs is not None:
            ai_channel._provider_breakers = _saved_pbs
    def test_ai_channel_cb_inherits_runtime_guardian(self):
        """ai_channel.CircuitBreaker 继承自 runtime_guardian.CircuitBreaker"""
        import ai_channel
        assert issubclass(ai_channel.CircuitBreaker, rg.CircuitBreaker)

    def test_ai_channel_cb_state_transitions(self):
        """ai_channel.CircuitBreaker 状态转换正常（字符串状态兼容）"""
        import ai_channel
        b = ai_channel.CircuitBreaker(fail_threshold=2, cooldown_sec=0.1)
        assert b.state == ai_channel.CircuitBreaker.CLOSED
        b.record_failure()
        b.record_failure()
        assert b.state == ai_channel.CircuitBreaker.OPEN
        time.sleep(0.15)
        assert b.state == ai_channel.CircuitBreaker.HALF_OPEN
        b.record_success()
        assert b.state == ai_channel.CircuitBreaker.CLOSED
        assert b.consecutive_failures == 0

    def test_ai_channel_cb_extra_fields(self):
        """ai_channel.CircuitBreaker 保留传输层额外字段"""
        import ai_channel
        b = ai_channel.CircuitBreaker(fail_threshold=1, cooldown_sec=30)
        b.record_success(latency_ms=150)
        assert b.last_latency_ms == 150
        assert b.success_count == 1
        b.record_failure(kind='network')
        assert b.last_error_kind == 'network'
        assert b.failure_count == 1
        snap = b.snapshot()
        assert snap['last_latency_ms'] == 150
        assert snap['last_error_kind'] == 'network'
        assert 'state' in snap

    def test_ai_channel_cb_injected_clock(self):
        """ai_channel.CircuitBreaker 支持 now_func 注入（原测试兼容性）"""
        import ai_channel
        now = [1000.0]
        b = ai_channel.CircuitBreaker(fail_threshold=1, cooldown_sec=30, now_func=lambda: now[0])
        b.record_failure()
        assert b.state == ai_channel.CircuitBreaker.OPEN
        now[0] = 1050.0
        assert b.state == ai_channel.CircuitBreaker.HALF_OPEN

    def test_ai_channel_global_breaker(self):
        """ai_channel 全局 breaker 实例可用"""
        import ai_channel
        assert ai_channel.breaker is not None
        assert isinstance(ai_channel.breaker, ai_channel.CircuitBreaker)
        snap = ai_channel.breaker.snapshot()
        assert 'state' in snap

    def test_ai_channel_provider_breaker(self):
        """ai_channel ProviderBreaker 使用收敛后的 CircuitBreaker"""
        import ai_channel
        pb = ai_channel.get_provider_breaker("test_provider", fail_threshold=1, cooldown_sec=30)
        assert pb is not None
        assert isinstance(pb.breaker, ai_channel.CircuitBreaker)
        pb.record_failure()
        assert pb.state == ai_channel.CircuitBreaker.OPEN


# ---------------------------------------------------------------------------
# 场景6：collector_automation 生命周期集成
# ---------------------------------------------------------------------------
class TestCollectorAutomationLifecycle:
    def test_automation_has_guardian_methods(self):
        """CollectorAutomation 具备 Runtime Guardian 集成方法"""
        import collector_automation as ca
        assert hasattr(ca, '_RG_AVAILABLE')
        assert ca._RG_AVAILABLE is True
        inst = ca.CollectorAutomation()
        assert hasattr(inst, '_get_guardian')
        assert hasattr(inst, '_start_heartbeat')
        assert hasattr(inst, '_heartbeat_loop')
        assert hasattr(inst, '_stop_heartbeat')
        assert hasattr(inst, '_rg_cleanup')
        assert hasattr(inst, '_max_task_duration')

    def test_automation_guardian_not_none(self):
        """CollectorAutomation._get_guardian 返回有效实例"""
        import collector_automation as ca
        inst = ca.CollectorAutomation()
        g = inst._get_guardian()
        assert g is not None
        assert isinstance(g, rg.RuntimeGuardian)

    def test_automation_heartbeat_start_stop(self):
        """心跳线程可启动和停止"""
        import collector_automation as ca
        inst = ca.CollectorAutomation()
        g = inst._get_guardian()
        wid = g.register_worker("hb_test_automation")
        inst._worker_id = wid
        inst._lease_owner = "test"
        inst._start_heartbeat(wid)
        assert inst._heartbeat_thread is not None
        assert inst._heartbeat_thread.is_alive()
        time.sleep(0.15)  # 等待至少一次心跳
        inst._stop_heartbeat()
        assert inst._heartbeat_thread is None
        # 验证心跳已写入
        worker = g.get_worker(wid)
        assert worker["last_heartbeat_at"] != ""

    def test_automation_rg_cleanup(self):
        """_rg_cleanup 释放租约并更新 worker 状态"""
        import collector_automation as ca
        inst = ca.CollectorAutomation()
        g = inst._get_guardian()
        wid = g.register_worker("cleanup_test")
        owner = f"pid-{os.getpid()}"
        g.acquire_lease(wid, owner, ttl_seconds=60)
        inst._worker_id = wid
        inst._lease_owner = owner
        inst._task_start_ts = time.time()

        task = {'id': 'test_task', 'status': 'completed'}
        inst._rg_cleanup(task)

        assert inst._worker_id is None
        assert inst._lease_owner is None
        assert inst._task_start_ts is None
        worker = g.get_worker(wid)
        assert worker["status"] == WorkerStatus.STOPPED.value
        assert worker["lease_owner"] == ""

    def test_automation_task_timeout_detection(self):
        """心跳线程检测任务超时并标记 worker FAILED"""
        import collector_automation as ca
        inst = ca.CollectorAutomation()
        inst._max_task_duration = 0.05  # 极短超时用于测试
        g = inst._get_guardian()
        wid = g.register_worker("timeout_test")
        owner = "timeout-node"
        g.acquire_lease(wid, owner, ttl_seconds=120)
        inst._worker_id = wid
        inst._lease_owner = owner
        # 设为10秒前，让心跳首次迭代立即检测到超时
        inst._task_start_ts = time.time() - 10
        inst._start_heartbeat(wid)
        time.sleep(0.3)  # 等待心跳线程至少运行一次
        inst._stop_heartbeat()
        worker = g.get_worker(wid)
        assert worker["status"] == WorkerStatus.FAILED.value
        assert "task_timeout" in worker["recovery_reason"]


# ---------------------------------------------------------------------------
# 场景7：collector.collect_all 旁路参数兼容性
# ---------------------------------------------------------------------------
class TestCollectorCollectAllBypass:
    def test_collect_all_signature_has_guardian_params(self):
        """collect_all 签名包含 guardian/worker_id/run_id 可选参数"""
        import collector
        import inspect
        sig = inspect.signature(collector.collect_all)
        params = list(sig.parameters.keys())
        assert 'guardian' in params
        assert 'worker_id' in params
        assert 'run_id' in params
        # 均为可选参数
        assert sig.parameters['guardian'].default is None
        assert sig.parameters['worker_id'].default is None

    def test_collect_one_keyword_helper(self):
        """_collect_one_keyword 辅助函数存在且可调用"""
        import collector
        assert hasattr(collector, '_collect_one_keyword')
        assert callable(collector._collect_one_keyword)

    def test_collector_import_ok(self):
        """collector 模块可正常导入（不破坏现有功能）"""
        import collector
        assert hasattr(collector, 'collect_all')
        assert hasattr(collector, 'search_xiaohongshu')
        assert hasattr(collector, 'MONITOR_KEYWORDS')
        assert hasattr(collector, 'classify_collect_state')

    def test_collector_rg_available(self):
        """collector 模块中 Runtime Guardian 旁路可用"""
        import collector
        assert hasattr(collector, '_RG_AVAILABLE')
        assert collector._RG_AVAILABLE is True


# ---------------------------------------------------------------------------
# 场景8：健康检查综合
# ---------------------------------------------------------------------------
class TestHealthCheckIntegration:
    def test_health_check_shows_worker_states(self, guardian, worker_id):
        """健康检查能反映 worker 状态和 DLQ 情况"""
        guardian.acquire_lease(worker_id, owner="node-1", ttl_seconds=60)
        guardian.heartbeat(worker_id)
        guardian.dlq.enqueue(worker_id=worker_id, task_type="test")

        health = guardian.health_check()
        assert health["overall"] == "healthy"
        assert health["workers"]["running"] >= 1
        assert health["dlq"]["pending"] >= 1
        assert health["guardian_name"] == guardian.name

    def test_health_check_degraded_on_failure(self, guardian, worker_id):
        """worker FAILED 时健康检查为 degraded"""
        guardian.update_worker_status(worker_id, WorkerStatus.FAILED, reason="test")
        health = guardian.health_check()
        assert health["overall"] == "degraded"
        assert health["workers"]["failed"] >= 1
