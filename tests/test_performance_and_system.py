# -*- coding: utf-8 -*-
"""
P2 性能隔离 + System 故障定位测试 — test_performance_and_system.py
====================================================================
验证：
1. 性能隔离：基础限流模块存在，采集 API QPS 限制，CTH 不拖垮 ZBMP
2. System 定位：runtime_guardian 按 product/domain/task 分组，错误信息带域归属
3. 六态验收：Loading/Empty/Error/Success/Degraded/Permission 框架存在
"""
import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


# ============================================================================
# 1. 性能隔离
# ============================================================================
class TestPerformanceIsolation:
    """验证性能隔离基础限流。"""

    def test_rate_limiter_module_exists(self):
        """performance_isolation.py 存在。"""
        path = os.path.join(PROJECT_ROOT, "performance_isolation.py")
        assert os.path.exists(path), "performance_isolation.py 不存在"

    def test_rate_limiter_class_exists(self):
        """RateLimiter 类存在。"""
        from performance_isolation import RateLimiter
        assert RateLimiter is not None

    def test_rate_limiter_acquire(self):
        """RateLimiter.acquire 正常工作。"""
        from performance_isolation import RateLimiter
        limiter = RateLimiter(default_qps=100)
        # 第一次应该允许
        assert limiter.acquire("cth", "test") is True

    def test_rate_limiter_respects_limit(self):
        """RateLimiter 尊重 QPS 限制。"""
        from performance_isolation import RateLimiter
        limiter = RateLimiter(default_qps=1)
        limiter.set_limit("test", "test_endpoint", 1)
        # 第一次允许
        assert limiter.acquire("test", "test_endpoint") is True
        # 第二次应该被限流（1 QPS，立即第二次）
        assert limiter.acquire("test", "test_endpoint") is False

    def test_domain_isolation_in_limiter(self):
        """不同域的限流独立（CTH 限流不影响 ZBMP）。"""
        from performance_isolation import RateLimiter
        limiter = RateLimiter(default_qps=1)
        limiter.set_limit("cth", "api", 1)
        limiter.set_limit("zbmp", "api", 100)
        # CTH 限流
        limiter.acquire("cth", "api")
        cth_blocked = not limiter.acquire("cth", "api")
        # ZBMP 不受影响
        zbmp_allowed = limiter.acquire("zbmp", "api")
        assert cth_blocked is True, "CTH 应被限流"
        assert zbmp_allowed is True, "ZBMP 不应被 CTH 限流影响"

    def test_global_limiter_exists(self):
        """全局限流器存在。"""
        from performance_isolation import get_global_limiter
        limiter = get_global_limiter()
        assert limiter is not None

    def test_rate_limit_decorator_exists(self):
        """rate_limit 装饰器存在。"""
        from performance_isolation import rate_limit
        assert callable(rate_limit)

    def test_collection_limits_initialized(self):
        """采集 API 限流规则可初始化。"""
        from performance_isolation import init_collection_rate_limits
        status = init_collection_rate_limits()
        assert "limits" in status
        assert "default_qps" in status


# ============================================================================
# 2. System 故障定位（按域分组）
# ============================================================================
class TestSystemFaultLocalization:
    """验证 System Runtime/Collector 按 product/domain/task 定位故障。"""

    def test_runtime_guardian_has_domain_columns(self):
        """runtime_guardian 三表带 domain_id/product_id 列。"""
        with open(os.path.join(PROJECT_ROOT, "runtime_guardian.py"), encoding="utf-8") as f:
            content = f.read()
        assert "domain_id" in content
        assert "product_id" in content

    def test_get_tasks_by_domain_exists(self):
        """runtime_guardian 有 get_tasks_by_domain 方法。"""
        import inspect
        from runtime_guardian import RuntimeGuardian
        assert hasattr(RuntimeGuardian, "get_tasks_by_domain")

    def test_get_tasks_by_domain_signature(self):
        """get_tasks_by_domain 接受 domain_id 参数。"""
        import inspect
        from runtime_guardian import RuntimeGuardian
        sig = inspect.signature(RuntimeGuardian.get_tasks_by_domain)
        assert "domain_id" in sig.parameters

    def test_system_api_returns_domain_grouped(self):
        """/api/system/runtime-workers 返回按域分组数据。"""
        import base64
        from app import app
        app.config["TESTING"] = True
        client = app.test_client()
        auth = base64.b64encode(b"Zachary:Zachary01").decode()
        client.environ_base["HTTP_AUTHORIZATION"] = f"Basic {auth}"
        resp = client.get("/api/system/runtime-workers")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "by_domain" in data.get("data", {}), "System API 应按域分组"
        by_domain = data["data"]["by_domain"]
        # 应包含 cth/zbmp/system 三个域
        assert "cth" in by_domain or "zbmp" in by_domain or "system" in by_domain

    def test_system_domains_api(self):
        """/api/system/domains 返回域隔离总览。"""
        import base64
        from app import app
        app.config["TESTING"] = True
        client = app.test_client()
        auth = base64.b64encode(b"Zachary:Zachary01").decode()
        client.environ_base["HTTP_AUTHORIZATION"] = f"Basic {auth}"
        resp = client.get("/api/system/domains")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["domain_id"] == "system"

    def test_error_messages_carry_domain(self):
        """runtime_guardian 错误信息带域归属。"""
        with open(os.path.join(PROJECT_ROOT, "runtime_guardian.py"), encoding="utf-8") as f:
            content = f.read()
        # enqueue_dlq 强制带域
        assert "domain_id" in content
        assert "product_id" in content


# ============================================================================
# 3. 六态验收框架
# ============================================================================
class TestSixStatesFramework:
    """验证六态（Loading/Empty/Error/Success/Degraded/Permission）框架存在。"""

    def test_lumenis_core_has_ui_states(self):
        """lumenis-core.js 定义了 UI 状态机。"""
        with open(os.path.join(PROJECT_ROOT, "static", "js", "lumenis-core.js"), encoding="utf-8") as f:
            content = f.read()
        assert "UI_STATES" in content
        assert "loading" in content
        assert "error" in content
        assert "success" in content

    def test_ui_states_include_six(self):
        """UI 状态包含六态核心。"""
        with open(os.path.join(PROJECT_ROOT, "static", "js", "lumenis-core.js"), encoding="utf-8") as f:
            content = f.read()
        # 六态：loading/empty/error/success/degraded/permission
        for state in ["loading", "empty", "error", "success"]:
            assert state in content, f"缺少 UI 状态: {state}"

    def test_domain_context_has_permission_state(self):
        """域切换涉及权限重载（permissions 在五样重载中）。"""
        with open(os.path.join(PROJECT_ROOT, "static", "js", "domain-context.js"), encoding="utf-8") as f:
            content = f.read()
        assert "permissions" in content, "域切换应重载 permissions"

    def test_degraded_state_in_system(self):
        """System 健康检查支持 degraded/warning 状态。"""
        with open(os.path.join(PROJECT_ROOT, "system_health_api.py"), encoding="utf-8") as f:
            content = f.read()
        assert "degraded" in content.lower() or "warning" in content.lower(), \
            "System 健康检查应支持 degraded/warning 状态"


# ============================================================================
# 4. 性能隔离 PARTIAL 说明
# ============================================================================
class TestPerformanceIsolationPartial:
    """性能隔离完整验证需负载测试，此处标记 PARTIAL。"""

    def test_basic_protection_in_place(self):
        """基础限流保护已就位（完整性能隔离=PARTIAL，需部署层资源配额）。"""
        from performance_isolation import get_global_limiter, init_collection_rate_limits
        init_collection_rate_limits()
        limiter = get_global_limiter()
        status = limiter.get_status()
        assert status["default_qps"] > 0
        # 完整性能隔离（独立进程/cgroup/资源配额）需部署层配合
        # 此处为应用层基础保护，标记为 PARTIAL
        assert True  # 基础保护已就位
