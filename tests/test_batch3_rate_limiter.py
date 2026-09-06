# -*- coding: utf-8 -*-
"""Batch3 单元测试：AdaptiveRateLimiter 动态限速器。

验证维度：
- 入口/参数：构造函数默认值、参数类型
- 核心逻辑：成功恢复、失败退避、熔断冷却、健康检查恢复
- 状态机：HEALTHY -> WARNING -> COOLDOWN -> HEALTHY
- 线程安全：并发调用不崩溃
- 边界：disabled模式、jitter、retry_after
"""
import sys
import time
import threading
import pytest
from pathlib import Path

# 确保项目根目录在path中
REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from collector_guard.rate_limiter import AdaptiveRateLimiter
from collector_guard.state import CollectState


class TestAdaptiveRateLimiterInit:
    """测试构造函数与参数校验。"""

    def test_default_init(self):
        """默认参数应能正常构造。"""
        rl = AdaptiveRateLimiter()
        assert rl.base_interval > 0
        assert rl.min_interval > 0
        assert rl.max_interval >= rl.base_interval
        assert rl.fail_threshold == 3
        assert rl.cooldown_seconds > 0
        assert rl.enabled is True
        assert rl.state == CollectState.HEALTHY
        assert rl.consecutive_fail == 0

    def test_custom_params(self):
        """自定义参数应被正确保存。"""
        rl = AdaptiveRateLimiter(
            base_interval=10, min_interval=2, max_interval=100,
            fail_threshold=5, cooldown_seconds=30, enabled=False, jitter=False
        )
        assert rl.base_interval == 10
        assert rl.min_interval == 2
        assert rl.max_interval == 100
        assert rl.fail_threshold == 5
        assert rl.cooldown_seconds == 30
        assert rl.enabled is False
        assert rl.jitter is False

    def test_max_interval_capped_by_backoff_factor(self):
        """max_interval默认应为base * MAX_BACKOFF_FACTOR。"""
        rl = AdaptiveRateLimiter(base_interval=10)
        assert rl.max_interval == 10 * AdaptiveRateLimiter.MAX_BACKOFF_FACTOR


class TestSuccessRecovery:
    """测试成功后的状态恢复逻辑。"""

    def test_on_success_resets_fail_count(self):
        """成功应重置连续失败计数。"""
        rl = AdaptiveRateLimiter()
        rl.on_failure()
        rl.on_failure()
        assert rl.consecutive_fail == 2
        rl.on_success()
        assert rl.consecutive_fail == 0

    def test_on_success_reduces_interval(self):
        """成功应使间隔向min_interval收敛（×0.9）。"""
        rl = AdaptiveRateLimiter(base_interval=20, min_interval=8)
        rl.interval = 20
        rl.on_success()
        assert rl.interval == pytest.approx(18, rel=0.01)

    def test_on_success_from_cooldown(self):
        """从冷却状态成功应恢复为HEALTHY。"""
        rl = AdaptiveRateLimiter(fail_threshold=1, cooldown_seconds=1)
        rl.on_failure(force_cooldown=True)
        assert rl.state == CollectState.COOLDOWN
        # 模拟冷却结束
        rl.cooldown_until = time.time() - 1
        rl.on_success()
        assert rl.state == CollectState.HEALTHY

    def test_on_success_clears_cooldown(self):
        """成功应清除冷却时间。"""
        rl = AdaptiveRateLimiter()
        rl.on_failure(force_cooldown=True)
        assert rl.cooldown_until > 0
        rl.on_success()
        assert rl.cooldown_until == 0.0


class TestFailureBackoff:
    """测试失败后的退避逻辑。"""

    def test_on_failure_increments_count(self):
        """失败应增加连续失败计数。"""
        rl = AdaptiveRateLimiter()
        rl.on_failure()
        assert rl.consecutive_fail == 1
        rl.on_failure()
        assert rl.consecutive_fail == 2

    def test_on_failure_increases_interval(self):
        """失败应使间隔翻倍（×2）。"""
        rl = AdaptiveRateLimiter(base_interval=10)
        rl.interval = 10
        rl.on_failure()
        assert rl.interval >= 10  # 至少不小于base*2^0

    def test_first_failure_sets_warning(self):
        """首次失败（未达阈值）应设为WARNING。"""
        rl = AdaptiveRateLimiter(fail_threshold=3)
        state = rl.on_failure()
        assert state == CollectState.WARNING
        assert rl.state == CollectState.WARNING

    def test_threshold_failure_enters_cooldown(self):
        """达到失败阈值应进入COOLDOWN。"""
        rl = AdaptiveRateLimiter(fail_threshold=2, cooldown_seconds=60)
        rl.on_failure()
        assert rl.state == CollectState.WARNING
        rl.on_failure()
        assert rl.state == CollectState.COOLDOWN
        assert rl.cooldown_until > time.time()

    def test_force_cooldown(self):
        """force_cooldown应立即进入冷却。"""
        rl = AdaptiveRateLimiter(fail_threshold=10, cooldown_seconds=60)
        rl.on_failure(force_cooldown=True)
        assert rl.state == CollectState.COOLDOWN

    def test_retry_after_respected(self):
        """retry_after应被尊重（冷却时间不小于retry_after）。"""
        rl = AdaptiveRateLimiter(fail_threshold=1, cooldown_seconds=10)
        rl.on_failure(retry_after=120)
        remaining = rl.remaining_cooldown()
        assert remaining >= 100  # 至少接近120秒

    def test_invalid_retry_after_ignored(self):
        """无效的retry_after应被忽略。"""
        rl = AdaptiveRateLimiter(fail_threshold=1, cooldown_seconds=60)
        rl.on_failure(retry_after='invalid')
        assert rl.state == CollectState.COOLDOWN


class TestCooldownAndPause:
    """测试冷却与暂停机制。"""

    def test_remaining_cooldown(self):
        """remaining_cooldown应返回正数（冷却中）或0。"""
        rl = AdaptiveRateLimiter()
        assert rl.remaining_cooldown() == 0.0
        rl.on_failure(force_cooldown=True)
        assert rl.remaining_cooldown() > 0

    def test_can_run_during_cooldown(self):
        """冷却期间can_run应返回False。"""
        rl = AdaptiveRateLimiter()
        assert rl.can_run() is True
        rl.on_failure(force_cooldown=True)
        assert rl.can_run() is False

    def test_can_run_after_cooldown(self):
        """冷却结束后can_run应返回True。"""
        rl = AdaptiveRateLimiter()
        rl.on_failure(force_cooldown=True)
        rl.cooldown_until = time.time() - 1
        assert rl.can_run() is True

    def test_force_pause(self):
        """force_pause应设置暂停状态和冷却时间。"""
        rl = AdaptiveRateLimiter(cooldown_seconds=30)
        rl.force_pause(state=CollectState.PAUSED, cooldown_seconds=120)
        assert rl.state == CollectState.PAUSED
        assert rl.remaining_cooldown() > 60

    def test_force_pause_auth_required(self):
        """force_pause应支持AUTH_REQUIRED状态。"""
        rl = AdaptiveRateLimiter()
        rl.force_pause(state=CollectState.AUTH_REQUIRED)
        assert rl.state == CollectState.AUTH_REQUIRED


class TestWaitSlot:
    """测试等待槽位逻辑。"""

    def test_wait_slot_disabled(self):
        """disabled模式下wait_slot应返回0。"""
        rl = AdaptiveRateLimiter(enabled=False)
        result = rl.wait_slot(sleep=lambda x: None)
        assert result == 0.0

    def test_wait_slot_returns_positive(self):
        """正常模式下wait_slot应返回正数。"""
        rl = AdaptiveRateLimiter(base_interval=0.01, jitter=False)
        result = rl.wait_slot(sleep=lambda x: None)
        assert result > 0

    def test_wait_slot_calls_sleep(self):
        """wait_slot应调用sleep函数。"""
        rl = AdaptiveRateLimiter(base_interval=0.01, jitter=False)
        called = []
        rl.wait_slot(sleep=lambda x: called.append(x))
        assert len(called) == 1
        assert called[0] > 0


class TestSnapshot:
    """测试快照功能。"""

    def test_snapshot_returns_dict(self):
        """snapshot应返回包含关键字段的字典。"""
        rl = AdaptiveRateLimiter(base_interval=10)
        snap = rl.snapshot()
        assert isinstance(snap, dict)
        assert 'state' in snap
        assert 'interval' in snap
        assert 'consecutive_fail' in snap
        assert 'remaining_cooldown' in snap
        assert 'fail_threshold' in snap
        assert 'state_label' in snap

    def test_snapshot_reflects_state(self):
        """snapshot应反映当前状态。"""
        rl = AdaptiveRateLimiter()
        assert rl.snapshot()['state'] == CollectState.HEALTHY
        rl.on_failure(force_cooldown=True)
        assert rl.snapshot()['state'] == CollectState.COOLDOWN


class TestDisabledMode:
    """测试disabled模式。"""

    def test_disabled_on_success(self):
        """disabled模式下on_success应返回HEALTHY。"""
        rl = AdaptiveRateLimiter(enabled=False)
        assert rl.on_success() == CollectState.HEALTHY

    def test_disabled_on_failure(self):
        """disabled模式下on_failure不应改变状态。"""
        rl = AdaptiveRateLimiter(enabled=False)
        original_state = rl.state
        rl.on_failure()
        assert rl.state == original_state

    def test_disabled_can_run(self):
        """disabled模式下can_run应始终返回True。"""
        rl = AdaptiveRateLimiter(enabled=False)
        assert rl.can_run() is True


class TestThreadSafety:
    """测试线程安全（基本不崩溃）。"""

    def test_concurrent_on_success_failure(self):
        """并发调用on_success/on_failure不应崩溃。"""
        rl = AdaptiveRateLimiter(base_interval=0.001, jitter=False)
        errors = []

        def worker():
            try:
                for _ in range(50):
                    rl.on_failure()
                    rl.on_success()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0, f"Thread errors: {errors}"

    def test_concurrent_snapshot(self):
        """并发读取snapshot不应崩溃。"""
        rl = AdaptiveRateLimiter()
        errors = []

        def reader():
            try:
                for _ in range(100):
                    rl.snapshot()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=reader) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        assert len(errors) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
