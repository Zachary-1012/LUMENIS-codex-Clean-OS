# -*- coding: utf-8 -*-
"""P2-F: Browser Runtime 长驻测试框架
启动 → 健康监控 → 故障模拟 → 恢复验证
对齐 CTR-BROWSER-RUNTIME-P0-01，使用 MockAdapter 不依赖真实浏览器。
"""
import time
import pytest

from browser_runtime import (
    BrowserContract, BrowserState, FailureClass, BEEPExecutor, BEEPTrace,
    MAX_RETRY,
)


class MockAdapter(BrowserContract):
    def __init__(self):
        self._state = BrowserState.INIT
        self._health_count = 0
        self._fail_next_n = 0
        self.navigated_urls = []
        self.closed = False

    def navigate(self, url, **kw):
        if self._fail_next_n > 0:
            self._fail_next_n -= 1
            raise RuntimeError(f"Mock navigation failure: {url}")
        self.navigated_urls.append(url)
        self._state = BrowserState.ACTION
        return {"ok": True, "url": url, "state": self._state.value}

    def snapshot(self, **kw):
        if self._fail_next_n > 0:
            self._fail_next_n -= 1
            raise RuntimeError("Mock snapshot failure")
        return {"ok": True, "title": "Mock Page"}

    def screenshot(self, path=None, **kw):
        if self._fail_next_n > 0:
            self._fail_next_n -= 1
            raise RuntimeError("Mock screenshot failure")
        return {"ok": True, "path": path or "/tmp/mock.png"}

    def click(self, selector, **kw):
        if self._fail_next_n > 0:
            self._fail_next_n -= 1
            raise RuntimeError(f"Mock click failure: {selector}")
        return {"ok": True, "selector": selector}

    def type_text(self, selector, text, **kw):
        if self._fail_next_n > 0:
            self._fail_next_n -= 1
            raise RuntimeError(f"Mock type failure: {selector}")
        return {"ok": True, "selector": selector, "text": text}

    def get_text(self, selector, **kw):
        if self._fail_next_n > 0:
            self._fail_next_n -= 1
            raise RuntimeError(f"Mock get_text failure: {selector}")
        return f"Mock text for {selector}"

    def wait_for(self, selector, timeout=10, **kw):
        if self._fail_next_n > 0:
            self._fail_next_n -= 1
            return False
        return True

    def evaluate(self, js, **kw):
        if self._fail_next_n > 0:
            self._fail_next_n -= 1
            raise RuntimeError("Mock evaluate failure")
        return {"ok": True, "result": "mock_result"}

    def health(self):
        self._health_count += 1
        return {
            "ok": self._state != BrowserState.CLASSIFY_FAILURE,
            "state": self._state.value,
            "health_checks": self._health_count,
            "adapter": "mock",
            "timestamp": time.time(),
        }

    def close(self, **kw):
        self.closed = True
        self._state = BrowserState.SUCCESS
        return {"ok": True}

    def inject_failure(self, n=1, failure_class=FailureClass.TRANSIENT):
        self._fail_next_n = n


@pytest.fixture
def mock_adapter():
    yield MockAdapter()


# ============================================================
# 1. 启动测试
# ============================================================
class TestStartup:
    def test_adapter_creation(self, mock_adapter):
        assert mock_adapter is not None
        assert mock_adapter.closed is False

    def test_initial_health(self, mock_adapter):
        h = mock_adapter.health()
        assert h["ok"] is True
        assert h["state"] == BrowserState.INIT.value
        assert h["health_checks"] == 1

    def test_navigation_transitions_to_action(self, mock_adapter):
        result = mock_adapter.navigate("https://example.com")
        assert result["ok"] is True
        assert result["state"] == BrowserState.ACTION.value

    def test_startup_lifecycle(self, mock_adapter):
        h1 = mock_adapter.health()
        assert h1["state"] == BrowserState.INIT.value
        mock_adapter.navigate("https://example.com")
        h2 = mock_adapter.health()
        assert h2["state"] == BrowserState.ACTION.value
        assert h2["health_checks"] == 2


# ============================================================
# 2. 健康监控测试
# ============================================================
class TestHealthMonitoring:
    def test_continuous_health_checks(self, mock_adapter):
        for i in range(10):
            h = mock_adapter.health()
            assert h["ok"] is True
            assert h["health_checks"] == i + 1

    def test_health_state_consistency(self, mock_adapter):
        states = [mock_adapter.health()["state"] for _ in range(5)]
        assert all(s == BrowserState.INIT.value for s in states)

    def test_health_after_operations(self, mock_adapter):
        mock_adapter.navigate("https://example.com")
        mock_adapter.snapshot()
        mock_adapter.click("#button")
        h = mock_adapter.health()
        assert h["ok"] is True
        assert h["state"] == BrowserState.ACTION.value

    def test_health_monitoring_timing(self, mock_adapter):
        start = time.time()
        for _ in range(100):
            mock_adapter.health()
        assert (time.time() - start) < 1.0


# ============================================================
# 3. 故障模拟测试
# ============================================================
class TestFailureSimulation:
    def test_transient_failure_retry(self, mock_adapter):
        mock_adapter.inject_failure(n=1)
        executor = BEEPExecutor(max_retry=3)
        trace = executor.run("navigate", lambda: mock_adapter.navigate("https://example.com"))
        assert trace.result == "SUCCESS"

    def test_unknown_failure_exhausted(self, mock_adapter):
        mock_adapter.inject_failure(n=10, failure_class=FailureClass.UNKNOWN)
        executor = BEEPExecutor(max_retry=2)
        trace = executor.run("navigate", lambda: mock_adapter.navigate("https://example.com"))
        assert trace.result != "SUCCESS"
        assert trace.error is not None

    def test_failure_classification(self):
        assert BrowserContract.classify_failure("Connection reset by peer") == FailureClass.TRANSIENT
        assert BrowserContract.classify_failure("401 Unauthorized") == FailureClass.SESSION

    def test_state_sequence(self):
        seq = BrowserContract.state_sequence()
        assert isinstance(seq, list)
        assert len(seq) > 0
        assert BrowserState.INIT.value in seq

    def test_multiple_failures_recovery(self, mock_adapter):
        mock_adapter.inject_failure(n=3)
        executor = BEEPExecutor(max_retry=5)
        trace = executor.run("snapshot", lambda: mock_adapter.snapshot())
        assert trace.result == "SUCCESS"

    def test_failure_trace_evidence(self, mock_adapter):
        mock_adapter.inject_failure(n=1)
        executor = BEEPExecutor(max_retry=2)
        trace = executor.run("click", lambda: mock_adapter.click("#bad-selector"))
        evidence = trace.to_evidence()
        assert "action" in evidence
        assert "steps" in evidence
        assert isinstance(evidence["steps"], list)


# ============================================================
# 4. 恢复验证测试
# ============================================================
class TestRecoveryVerification:
    def test_recovery_after_transient_failure(self, mock_adapter):
        mock_adapter.inject_failure(n=1)
        with pytest.raises(Exception):
            mock_adapter.navigate("https://fail.com")
        result = mock_adapter.navigate("https://recover.com")
        assert result["ok"] is True

    def test_health_recovery_after_failure(self, mock_adapter):
        mock_adapter.inject_failure(n=1)
        try:
            mock_adapter.navigate("https://fail.com")
        except Exception:
            pass
        assert mock_adapter.health()["ok"] is True

    def test_full_recovery_lifecycle(self, mock_adapter):
        assert mock_adapter.navigate("https://normal.com")["ok"] is True
        mock_adapter.inject_failure(n=2)
        fail_count = 0
        for _ in range(2):
            try:
                mock_adapter.navigate("https://fail.com")
            except Exception:
                fail_count += 1
        assert fail_count == 2
        assert mock_adapter.navigate("https://recover.com")["ok"] is True
        for i in range(5):
            assert mock_adapter.snapshot()["ok"] is True

    def test_beep_executor_recovery(self, mock_adapter):
        mock_adapter.inject_failure(n=1)
        executor = BEEPExecutor(max_retry=3)
        t1 = executor.run("navigate", lambda: mock_adapter.navigate("https://retry.com"))
        assert t1.result == "SUCCESS"
        t2 = executor.run("snapshot", lambda: mock_adapter.snapshot())
        assert t2.result == "SUCCESS"
        t3 = executor.run("click", lambda: mock_adapter.click("#btn"))
        assert t3.result == "SUCCESS"

    def test_close_after_recovery(self, mock_adapter):
        mock_adapter.navigate("https://example.com")
        mock_adapter.inject_failure(n=1)
        try:
            mock_adapter.snapshot()
        except Exception:
            pass
        mock_adapter.snapshot()
        assert mock_adapter.close()["ok"] is True
        assert mock_adapter.closed is True
        assert mock_adapter.health()["state"] == BrowserState.SUCCESS.value


# ============================================================
# 5. 完整长驻生命周期测试
# ============================================================
class TestResidentLifecycle:
    def test_full_resident_cycle(self, mock_adapter):
        executor = BEEPExecutor(max_retry=3)

        # Phase 1: 启动
        assert mock_adapter.health()["state"] == BrowserState.INIT.value

        # Phase 2: 健康监控
        for _ in range(10):
            assert mock_adapter.health()["ok"] is True

        # Phase 3: 正常操作
        t1 = executor.run("navigate", lambda: mock_adapter.navigate("https://example.com"))
        assert t1.result == "SUCCESS"
        t2 = executor.run("snapshot", lambda: mock_adapter.snapshot())
        assert t2.result == "SUCCESS"

        # Phase 4: 故障模拟 + 自动重试
        mock_adapter.inject_failure(n=2)
        t3 = executor.run("navigate", lambda: mock_adapter.navigate("https://fail-retry.com"))
        assert t3.result == "SUCCESS"

        # Phase 5: 恢复验证
        for i in range(5):
            t = executor.run(f"recovery_{i}", lambda: mock_adapter.snapshot())
            assert t.result == "SUCCESS"

        # Phase 6: 关闭
        mock_adapter.close()
        assert mock_adapter.closed is True

    def test_resident_with_unknown_failure(self, mock_adapter):
        executor = BEEPExecutor(max_retry=2)
        mock_adapter.navigate("https://example.com")
        mock_adapter.inject_failure(n=10, failure_class=FailureClass.UNKNOWN)
        t = executor.run("bad_navigate", lambda: mock_adapter.navigate("https://fail.com"))
        assert t.result != "SUCCESS"
        mock_adapter.inject_failure(n=0)
        assert mock_adapter.navigate("https://recovered.com")["ok"] is True
        for _ in range(3):
            assert mock_adapter.snapshot()["ok"] is True

    def test_resident_health_under_stress(self, mock_adapter):
        for i in range(100):
            if i % 3 == 0:
                mock_adapter.navigate(f"https://example{i}.com")
            elif i % 3 == 1:
                mock_adapter.snapshot()
            else:
                mock_adapter.click(f"#btn{i}")
            assert mock_adapter.health()["ok"] is True
        h_final = mock_adapter.health()
        assert h_final["health_checks"] >= 100
        assert h_final["state"] == BrowserState.ACTION.value


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
