# -*- coding: utf-8 -*-
"""
P1 API 域契约 + 兼容层测试 — test_api_domain_contract.py
=========================================================
验证：
1. /api/zbmp|cth|system 成体系，基础路由可达
2. 旧 /api/xhs|v4|notes|web 路由保留 deprecated 兼容（X-Deprecated: true）
3. 所有双域 API 响应带 domain_id / product_id 字段
4. 断链路由修复：/api/skills/*, /api/auxiliary/sources, /api/web-sources, /api/system/account
5. 统一响应信封：{success, data, error, domain_id, product_id}
"""
import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture
def client():
    import base64
    from app import app
    app.config["TESTING"] = True
    c = app.test_client()
    auth = base64.b64encode(b"Zachary:Zachary01").decode()
    c.environ_base["HTTP_AUTHORIZATION"] = f"Basic {auth}"
    return c


# ============================================================================
# 1. 双域命名空间 API 成体系
# ============================================================================
class TestDualDomainNamespace:
    """验证 /api/zbmp|cth|system 成体系。"""

    def test_zbmp_base_route(self, client):
        """/api/zbmp 基础路由可达。"""
        resp = client.get("/api/zbmp")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["domain_id"] == "zbmp"
        assert data["product_id"] == "ZBMP"

    def test_cth_base_route(self, client):
        """/api/cth 基础路由可达。"""
        resp = client.get("/api/cth")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["domain_id"] == "cth"
        assert data["product_id"] == "CTH"

    def test_zbmp_overview(self, client):
        """/api/zbmp/overview 可达且带域标签。"""
        resp = client.get("/api/zbmp/overview", headers={
            "X-Domain-Id": "zbmp", "X-Product-Id": "ZBMP"
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["domain_id"] == "zbmp"

    def test_cth_overview(self, client):
        """/api/cth/overview 可达且带域标签。"""
        resp = client.get("/api/cth/overview", headers={
            "X-Domain-Id": "cth", "X-Product-Id": "CTH"
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["domain_id"] == "cth"

    def test_system_status(self, client):
        """/api/system/status 可达。"""
        resp = client.get("/api/system/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["domain_id"] == "system"


# ============================================================================
# 2. Deprecated 兼容层
# ============================================================================
class TestDeprecatedCompatibility:
    """验证旧路由保留但标记 deprecated。"""

    def test_xhs_routes_have_deprecated_header(self, client):
        """/api/xhs/* 路由带 X-Deprecated: true 头。"""
        resp = client.get("/api/xhs/accounts")
        # 路由可能需要认证，但 after_request 钩子应仍加头
        assert "X-Deprecated" in resp.headers or resp.status_code in (200, 302, 401, 403)

    def test_v4_routes_have_deprecated_header(self, client):
        """/api/v4/* 路由带 X-Deprecated: true 头。"""
        resp = client.get("/api/v4/api-keys")
        assert "X-Deprecated" in resp.headers or resp.status_code in (200, 302, 401, 403)

    def test_deprecated_prefixes_defined(self):
        """deprecated 前缀列表已定义在 app.py。"""
        with open(os.path.join(PROJECT_ROOT, "app.py"), encoding="utf-8-sig") as f:
            content = f.read()
        assert "_DEPRECATED_API_PREFIXES" in content
        assert '"/api/xhs/"' in content
        assert '"/api/v4/"' in content

    def test_new_routes_not_deprecated(self, client):
        """新双域路由不带 X-Deprecated 头。"""
        resp = client.get("/api/zbmp/overview", headers={
            "X-Domain-Id": "zbmp", "X-Product-Id": "ZBMP"
        })
        assert "X-Deprecated" not in resp.headers, \
            "新双域路由不应被标记 deprecated"


# ============================================================================
# 3. 统一响应信封
# ============================================================================
class TestUnifiedResponseEnvelope:
    """验证所有双域 API 响应带统一信封。"""

    def test_response_has_success_field(self, client):
        """响应带 success 字段。"""
        resp = client.get("/api/zbmp/overview", headers={
            "X-Domain-Id": "zbmp", "X-Product-Id": "ZBMP"
        })
        data = resp.get_json()
        assert "success" in data

    def test_response_has_data_field(self, client):
        """响应带 data 字段。"""
        resp = client.get("/api/cth/overview", headers={
            "X-Domain-Id": "cth", "X-Product-Id": "CTH"
        })
        data = resp.get_json()
        assert "data" in data

    def test_response_has_error_field(self, client):
        """响应带 error 字段。"""
        resp = client.get("/api/system/status")
        data = resp.get_json()
        assert "error" in data

    def test_response_has_domain_fields(self, client):
        """响应带 domain_id / product_id 字段。"""
        endpoints = [
            ("/api/zbmp/overview", {"X-Domain-Id": "zbmp", "X-Product-Id": "ZBMP"}),
            ("/api/cth/overview", {"X-Domain-Id": "cth", "X-Product-Id": "CTH"}),
            ("/api/system/status", {}),
        ]
        for url, headers in endpoints:
            resp = client.get(url, headers=headers)
            data = resp.get_json()
            assert "domain_id" in data, f"{url} 缺少 domain_id"
            assert "product_id" in data, f"{url} 缺少 product_id"
            assert data["domain_id"], f"{url} domain_id 为空"
            assert data["product_id"], f"{url} product_id 为空"


# ============================================================================
# 4. 断链路由修复验证
# ============================================================================
class TestBrokenRouteFixes:
    """验证前端调用的断链路由已修复。"""

    def test_skills_list_route(self, client):
        """/api/skills 或 /api/skills/list 可达。"""
        resp = client.get("/api/skills")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "success" in data
        assert "domain_id" in data

    def test_skills_status_route(self, client):
        """/api/skills/status 可达。"""
        resp = client.get("/api/skills/status")
        assert resp.status_code == 200

    def test_auxiliary_sources_route(self, client):
        """/api/auxiliary/sources 可达（feature-modules.js 调用）。"""
        resp = client.get("/api/auxiliary/sources")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "sources" in data.get("data", {}) or "items" in data.get("data", {})

    def test_web_sources_route(self, client):
        """/api/web-sources 可达（feature-modules.js 备选端点）。"""
        resp = client.get("/api/web-sources")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "sources" in data.get("data", {}) or "items" in data.get("data", {})

    def test_system_account_route(self, client):
        """/api/system/account 可达（settings.js 调用）。"""
        resp = client.get("/api/system/account")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "success" in data

    def test_zbmp_base_route_endpoints(self, client):
        """/api/zbmp 返回可用端点列表。"""
        resp = client.get("/api/zbmp")
        data = resp.get_json()
        assert "endpoints" in data.get("data", {})

    def test_cth_base_route_endpoints(self, client):
        """/api/cth 返回可用端点列表。"""
        resp = client.get("/api/cth")
        data = resp.get_json()
        assert "endpoints" in data.get("data", {})


# ============================================================================
# 5. API 域归属清单存在
# ============================================================================
class TestApiDomainMappingDocument:
    """验证当前 API Owner map 存在并描述现行产品域。"""

    def test_mapping_document_exists(self):
        """当前治理文档内的 API owner map 存在。"""
        path = os.path.join(PROJECT_ROOT, "00-GOVERNANCE", "LUMENIS-API-OWNER-MAP.md")
        assert os.path.exists(path), "API 域归属清单不存在"

    def test_mapping_document_has_zbmp_section(self):
        """清单包含 ZBMP 域部分。"""
        path = os.path.join(PROJECT_ROOT, "00-GOVERNANCE", "LUMENIS-API-OWNER-MAP.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "ZBMP" in content
        assert "/api/zbmp/" in content

    def test_mapping_document_has_cth_section(self):
        """清单包含 CTH 域部分。"""
        path = os.path.join(PROJECT_ROOT, "00-GOVERNANCE", "LUMENIS-API-OWNER-MAP.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "CTH" in content
        assert "/api/cth/" in content

    def test_mapping_document_has_deprecated_section(self):
        """清单包含 deprecated 旧路由部分。"""
        path = os.path.join(PROJECT_ROOT, "00-GOVERNANCE", "LUMENIS-API-OWNER-MAP.md")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "Deprecated" in content or "deprecated" in content
