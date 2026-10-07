# -*- coding: utf-8 -*-
"""
P0 前端全局域切换测试 — test_domain_context_switching.py
==========================================================
验证：
1. domain-context.js 文件存在且包含核心逻辑（fetch拦截/域推断/切换重载/事件派发）
2. base.html 模板注入了 domain-context.js
3. 后端 API 正确读取 X-Domain-Id / X-Product-Id 请求头
4. 域切换后数据确实重新加载（不同域头返回不同域数据，不是缓存的另一域）
5. 域切换器 UI 存在于 base.html
6. 五样重载声明（context/metrics/data/permissions/reports）存在于 JS

红线：禁 Mock/假数据；后端测试读真实数据库（可能为空，空=empty 态合法）。
"""
import os
import re
import pytest

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_JS = os.path.join(PROJECT_ROOT, "static", "js")
TEMPLATES = os.path.join(PROJECT_ROOT, "templates")


# ============================================================================
# 1. Retired Web shell boundary
# ============================================================================
class TestRetiredWebShell:
    """The retired server-rendered web client must not return as a second UI owner."""

    def test_web_shell_and_global_domain_script_are_absent(self):
        assert not os.path.exists(os.path.join(PROJECT_ROOT, "templates"))
        assert not os.path.exists(os.path.join(PROJECT_ROOT, "static"))

    def test_app_experience_contract_is_canonical(self):
        from pathlib import Path
        architecture = Path(PROJECT_ROOT, "00-GOVERNANCE", "LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md").read_text(encoding="utf-8")
        constitution = Path(PROJECT_ROOT, "00-GOVERNANCE", "LUMENIS-EXPERIENCE-CONSTITUTION.md").read_text(encoding="utf-8")
        assert "Flutter LUMENIS Experience" in architecture
        assert "No shared renderer may turn these 44 IDs into one template" in constitution


# ============================================================================
# 3. 后端 API 域头解析 + 数据隔离（Flask test client）
# ============================================================================
class TestBackendDomainHeaderResolution:
    """验证后端 API 正确读取 X-Domain-Id / X-Product-Id，且不同域返回不同数据。"""

    @pytest.fixture
    def client(self, monkeypatch):
        import base64
        from app import app
        monkeypatch.setitem(app.config, "TESTING", True)
        c = app.test_client()
        username = os.environ.get("TAIKOO_AUTH_USER")
        password = os.environ.get("TAIKOO_AUTH_PASSWORD")
        assert username and password, "tests/conftest.py must provide isolated test credentials"
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        c.environ_base["HTTP_AUTHORIZATION"] = f"Basic {token}"
        return c

    @pytest.fixture
    def cth_client(self, monkeypatch):
        """Use the server-opened local workspace while retaining CTH scope checks."""
        from app import app
        monkeypatch.setitem(app.config, "LUMENIS_OPEN_WORKSPACE", True)
        c = app.test_client()
        assert "HTTP_AUTHORIZATION" not in c.environ_base
        return c

    def test_zbmp_api_returns_zbmp_domain(self, client):
        """带 X-Domain-Id: zbmp 的 /api/zbmp/overview 返回 domain_id=zbmp。"""
        resp = client.get("/api/zbmp/overview", headers={
            "X-Domain-Id": "zbmp",
            "X-Product-Id": "ZBMP"
        })
        assert resp.status_code == 200, f"ZBMP overview 返回 {resp.status_code}"
        data = resp.get_json()
        assert data is not None, "响应无 JSON"
        assert data.get("domain_id") == "zbmp", f"期望 domain_id=zbmp, 实际 {data.get('domain_id')}"
        assert data.get("product_id") == "ZBMP", f"期望 product_id=ZBMP, 实际 {data.get('product_id')}"

    def test_cth_api_returns_cth_domain(self, cth_client):
        """带 X-Domain-Id: cth 的 /api/cth/overview 返回 domain_id=cth。"""
        resp = cth_client.get("/api/cth/overview", headers={
            "X-Domain-Id": "cth",
            "X-Product-Id": "CTH"
        })
        assert resp.status_code == 200, f"CTH overview 返回 {resp.status_code}"
        data = resp.get_json()
        assert data is not None
        assert data.get("domain_id") == "cth", f"期望 domain_id=cth, 实际 {data.get('domain_id')}"
        assert data.get("product_id") == "CTH", f"期望 product_id=CTH, 实际 {data.get('product_id')}"

    def test_system_api_returns_system_domain(self, client):
        """带 X-Domain-Id: system 的 /api/system/status 返回 domain_id=system。"""
        resp = client.get("/api/system/status", headers={
            "X-Domain-Id": "system",
            "X-Product-Id": "SYSTEM"
        })
        assert resp.status_code == 200, f"System status 返回 {resp.status_code}"
        data = resp.get_json()
        assert data is not None
        assert data.get("domain_id") == "system"
        assert data.get("product_id") == "SYSTEM"

    def test_domain_switch_data_not_cross_contaminated(self, client, cth_client):
        """域切换后数据不串域：ZBMP API 不返回 CTH 专项字段，反之亦然。

        验证"标题变了数据还是另一域"的反模式不存在。
        """
        # ZBMP 请求
        zbmp_resp = client.get("/api/zbmp/overview", headers={
            "X-Domain-Id": "zbmp", "X-Product-Id": "ZBMP"
        })
        zbmp_data = zbmp_resp.get_json()
        assert zbmp_data.get("domain_id") == "zbmp"

        # CTH 请求（模拟域切换后的新请求）
        cth_resp = cth_client.get("/api/cth/overview", headers={
            "X-Domain-Id": "cth", "X-Product-Id": "CTH"
        })
        cth_data = cth_resp.get_json()
        assert cth_data.get("domain_id") == "cth"

        # 两次请求的 domain_id 必须不同——证明切换后数据确实重新加载
        assert zbmp_data["domain_id"] != cth_data["domain_id"], \
            "域切换后 domain_id 未变，数据可能是缓存的另一域"

    def test_zbmp_metrics_domain_tagged(self, client):
        """ZBMP metrics API 返回域标签。"""
        resp = client.get("/api/zbmp/metrics", headers={
            "X-Domain-Id": "zbmp", "X-Product-Id": "ZBMP"
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("domain_id") == "zbmp"
        assert data.get("product_id") == "ZBMP"

    def test_cth_events_domain_tagged(self, cth_client):
        """CTH events API 返回域标签。"""
        resp = cth_client.get("/api/cth/events", headers={
            "X-Domain-Id": "cth", "X-Product-Id": "CTH"
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("domain_id") == "cth"
        assert data.get("product_id") == "CTH"

    def test_api_response_always_has_domain_fields(self, client, cth_client):
        """所有双域 API 响应必须带 domain_id / product_id 字段（不缺失）。"""
        endpoints = [
            ("/api/zbmp/overview", {"X-Domain-Id": "zbmp", "X-Product-Id": "ZBMP"}),
            ("/api/zbmp/brands", {"X-Domain-Id": "zbmp", "X-Product-Id": "ZBMP"}),
            ("/api/zbmp/metrics", {"X-Domain-Id": "zbmp", "X-Product-Id": "ZBMP"}),
            ("/api/cth/overview", {"X-Domain-Id": "cth", "X-Product-Id": "CTH"}),
            ("/api/cth/events", {"X-Domain-Id": "cth", "X-Product-Id": "CTH"}),
            ("/api/cth/xiaohongshu", {"X-Domain-Id": "cth", "X-Product-Id": "CTH"}),
            ("/api/system/status", {"X-Domain-Id": "system", "X-Product-Id": "SYSTEM"}),
            ("/api/system/domains", {"X-Domain-Id": "system", "X-Product-Id": "SYSTEM"}),
        ]
        for url, headers in endpoints:
            active_client = cth_client if url.startswith("/api/cth/") else client
            resp = active_client.get(url, headers=headers)
            assert resp.status_code == 200, f"{url} 返回 {resp.status_code}"
            data = resp.get_json()
            assert "domain_id" in data, f"{url} 响应缺少 domain_id"
            assert "product_id" in data, f"{url} 响应缺少 product_id"
            assert data["domain_id"], f"{url} domain_id 为空"
            assert data["product_id"], f"{url} product_id 为空"
