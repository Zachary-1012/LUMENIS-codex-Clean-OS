# -*- coding: utf-8 -*-
"""VIZ API 测试套件 — 函数驱动可视化后端。

覆盖：
  1. 注册表完整性（20 个函数、元数据完整、domain 合法）
  2. 各函数返回结构（current_value/delta/freshness/confidence/evidence_refs/items）
  3. 缺失值处理（null/unknown/missing，禁止 0 填充）
  4. 错误处理（函数不存在 404、参数缺失 400、域隔离 403）
  5. 域隔离（zbmp/cth/system/all）
  6. 真实 DB 数据（每个 provider 真实查询，不 mock）
  7. ui_view_model 转换链路（build_truth_table / filter_records_by_time / MetricLayer）
"""
from __future__ import annotations

import json
import os
import sys
import unittest

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask

from function_registry import (
    VIZ_FUNCTIONS,
    get_viz_function,
    list_viz_functions,
    viz_registry_metadata,
)
from ui_view_model import (
    ConfidenceLevel,
    DataStatus,
    TimeRange,
    build_truth_table,
    compute_time_bounds,
    filter_records_by_time,
)
from viz_data_provider import PROVIDER_MAP, fetch_data
from viz_api import viz_bp, register_viz_api


# ── Flask 测试客户端 ────────────────────────────────────────────────────────

def create_test_app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_viz_api(app)
    return app


# ═══════════════════════════════════════════════════════════════════════════
# 1. 注册表完整性测试
# ═══════════════════════════════════════════════════════════════════════════

class TestRegistryIntegrity(unittest.TestCase):
    """注册表完整性：20 个函数、元数据完整、domain 合法。"""

    def test_viz_functions_count(self):
        """VIZ_FUNCTIONS 至少 20 个函数。"""
        self.assertGreaterEqual(len(VIZ_FUNCTIONS), 20)

    def test_each_function_has_required_fields(self):
        """每个函数必须包含 function_name/label/description/ui_view_fn/db_tables/db_provider/param_schema/return_schema/domain。"""
        required = ["function_name", "label", "description", "ui_view_fn",
                    "db_tables", "db_provider", "param_schema", "return_schema", "domain"]
        for f in VIZ_FUNCTIONS:
            for field in required:
                self.assertIn(field, f, f"{f.get('function_name', '?')} missing {field}")

    def test_function_names_unique(self):
        """function_name 必须唯一。"""
        names = [f["function_name"] for f in VIZ_FUNCTIONS]
        self.assertEqual(len(names), len(set(names)), "duplicate function_name found")

    def test_domains_are_valid(self):
        """domain 必须是 zbmp/cth/system/all 之一。"""
        valid = {"zbmp", "cth", "system", "all"}
        for f in VIZ_FUNCTIONS:
            self.assertIn(f["domain"], valid, f"{f['function_name']} invalid domain {f['domain']}")

    def test_get_viz_function_returns_entry(self):
        """get_viz_function 能正确查找。"""
        entry = get_viz_function("overview.stats")
        self.assertIsNotNone(entry)
        self.assertEqual(entry["function_name"], "overview.stats")

    def test_get_viz_function_unknown_returns_none(self):
        """未知函数返回 None。"""
        self.assertIsNone(get_viz_function("nonexistent.function"))

    def test_list_viz_functions_by_domain(self):
        """按 domain 过滤函数。"""
        system_funcs = list_viz_functions("system")
        self.assertTrue(all(f["domain"] in ("system", "all") for f in system_funcs))

    def test_viz_registry_metadata_serializable(self):
        """元数据列表可 JSON 序列化。"""
        meta = viz_registry_metadata()
        self.assertEqual(len(meta), len(VIZ_FUNCTIONS))
        json.dumps(meta)  # 不抛异常即可

    def test_required_functions_present(self):
        """任务要求的 20 个函数全部注册。"""
        required = [
            "overview.stats", "overview.trend", "overview.industry_dist",
            "brand.top10", "brand.growth",
            "kos.list", "kos.attribution",
            "risk.active", "risk.trend",
            "events.list", "events.propagation",
            "notes.realtime", "notes.search",
            "system.runtime", "system.workers", "system.database_tables",
            "ai.call_logs",
            "collector.status", "collector.quality_gate",
        ]
        registered = {f["function_name"] for f in VIZ_FUNCTIONS}
        for name in required:
            self.assertIn(name, registered, f"required function {name} not registered")


# ═══════════════════════════════════════════════════════════════════════════
# 2. Data Provider 真实 DB 测试
# ═══════════════════════════════════════════════════════════════════════════

class TestDataProviderRealDB(unittest.TestCase):
    """每个 provider 真实查询 DB，不 mock。"""

    def test_provider_map_has_all_functions(self):
        """PROVIDER_MAP 覆盖所有 VIZ_FUNCTIONS。"""
        for f in VIZ_FUNCTIONS:
            self.assertIn(f["function_name"], PROVIDER_MAP,
                          f"no provider for {f['function_name']}")

    def test_provider_map_count_matches(self):
        """PROVIDER_MAP 数量与 VIZ_FUNCTIONS 一致。"""
        self.assertEqual(len(PROVIDER_MAP), len(VIZ_FUNCTIONS))

    def test_fetch_overview_stats(self):
        """overview.stats 真实查询。"""
        r = fetch_data("overview.stats", {})
        self.assertIn(r.status, (DataStatus.OK, DataStatus.NO_DATA, DataStatus.ERROR))
        self.assertIsInstance(r.records, list)

    def test_fetch_system_runtime(self):
        """system.runtime 真实查询。"""
        r = fetch_data("system.runtime", {})
        self.assertIn(r.status, (DataStatus.OK, DataStatus.NO_DATA, DataStatus.ERROR))

    def test_fetch_system_database_tables(self):
        """system.database_tables 返回所有表。"""
        r = fetch_data("system.database_tables", {})
        self.assertEqual(r.status, DataStatus.OK)
        self.assertGreater(len(r.records), 0)
        # 每条记录有 table_name 和 row_count
        for rec in r.records:
            self.assertIn("table_name", rec)
            self.assertIn("row_count", rec)

    def test_fetch_ai_call_logs(self):
        """ai.call_logs 真实查询。"""
        r = fetch_data("ai.call_logs", {})
        self.assertIn(r.status, (DataStatus.OK, DataStatus.NO_DATA, DataStatus.ERROR))

    def test_fetch_notes_realtime(self):
        """notes.realtime 真实查询。"""
        r = fetch_data("notes.realtime", {})
        self.assertIn(r.status, (DataStatus.OK, DataStatus.NO_DATA, DataStatus.ERROR))

    def test_fetch_unknown_function_returns_error(self):
        """未知函数返回 DataStatus.ERROR。"""
        r = fetch_data("nonexistent.function", {})
        self.assertEqual(r.status, DataStatus.ERROR)
        self.assertIsNotNone(r.error)

    def test_fetch_events_propagation_requires_event_id(self):
        """events.propagation 缺少 event_id 返回错误。"""
        r = fetch_data("events.propagation", {})
        self.assertEqual(r.status, DataStatus.ERROR)

    def test_fetch_notes_search_requires_keyword(self):
        """notes.search 缺少 keyword 返回错误。"""
        r = fetch_data("notes.search", {})
        self.assertEqual(r.status, DataStatus.ERROR)


# ═══════════════════════════════════════════════════════════════════════════
# 3. ui_view_model 转换链路测试
# ═══════════════════════════════════════════════════════════════════════════

class TestViewModelTransform(unittest.TestCase):
    """ui_view_model 转换函数：build_truth_table / compute_time_bounds / filter_records_by_time。"""

    def test_compute_time_bounds_d7(self):
        """D7 时间范围返回 7 天前到现在。"""
        start, end = compute_time_bounds(TimeRange.D7)
        self.assertIsNotNone(start)
        self.assertLess(start, end)

    def test_compute_time_bounds_now_returns_none_start(self):
        """NOW 返回 (None, now)。"""
        start, end = compute_time_bounds(TimeRange.NOW)
        self.assertIsNone(start)
        self.assertIsNotNone(end)

    def test_filter_records_by_time_filters(self):
        """filter_records_by_time 按时间过滤。"""
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        old = (now - timedelta(days=10)).isoformat()
        recent = (now - timedelta(days=1)).isoformat()
        records = [
            {"publish_datetime": old, "id": 1},
            {"publish_datetime": recent, "id": 2},
        ]
        filtered = filter_records_by_time(records, TimeRange.D7, now=now)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["id"], 2)

    def test_build_truth_table_no_data(self):
        """空 DataResult 构建 TruthTable 返回 NO_DATA。"""
        from ui_view_model import DataQuery, DataResult
        dr = DataResult(query=DataQuery(source="test"), records=[], total=0, status=DataStatus.NO_DATA)
        tt = build_truth_table(dr)
        self.assertFalse(tt.exists)
        self.assertEqual(tt.status, DataStatus.NO_DATA)
        self.assertEqual(tt.confidence, ConfidenceLevel.UNKNOWN)

    def test_build_truth_table_error(self):
        """错误 DataResult 构建 TruthTable 返回 ERROR。"""
        from ui_view_model import DataQuery, DataResult
        dr = DataResult(query=DataQuery(source="test"), records=[], total=0,
                         status=DataStatus.ERROR, error="db connection failed")
        tt = build_truth_table(dr)
        self.assertEqual(tt.status, DataStatus.ERROR)
        self.assertEqual(tt.confidence, ConfidenceLevel.UNKNOWN)
        self.assertIsNotNone(tt.error)


# ═══════════════════════════════════════════════════════════════════════════
# 4. API 端点测试（Flask test client）
# ═══════════════════════════════════════════════════════════════════════════

class TestVizApiEndpoints(unittest.TestCase):
    """API 端点：registry / function / 错误处理 / 域隔离。"""

    @classmethod
    def setUpClass(cls):
        cls.app = create_test_app()
        cls.client = cls.app.test_client()

    def test_registry_endpoint_returns_200(self):
        """GET /api/viz/registry 返回 200。"""
        resp = self.client.get("/api/viz/registry")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["total"], len(VIZ_FUNCTIONS))

    def test_registry_endpoint_has_function_list(self):
        """registry 返回函数列表。"""
        resp = self.client.get("/api/viz/registry")
        data = resp.get_json()
        funcs = data["data"]["functions"]
        self.assertIsInstance(funcs, list)
        self.assertGreater(len(funcs), 0)
        # 每个函数有 function_name
        for f in funcs:
            self.assertIn("function_name", f)

    def test_overview_stats_endpoint(self):
        """GET /api/viz/overview.stats 返回标准结构。"""
        resp = self.client.get("/api/viz/overview.stats")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("success", data)
        self.assertIn("data", data)
        self.assertIn("function_name", data)
        self.assertEqual(data["function_name"], "overview.stats")

    def test_response_has_view_model_fields(self):
        """响应 data 包含 current_value/delta/freshness/confidence/evidence_refs/items。"""
        resp = self.client.get("/api/viz/overview.stats")
        data = resp.get_json()
        view = data["data"]
        for field in ("current_value", "delta", "freshness", "confidence", "evidence_refs", "items"):
            self.assertIn(field, view, f"missing field {field}")

    def test_response_has_domain_identifiers(self):
        """响应包含 domain_id/product_id。"""
        resp = self.client.get("/api/viz/overview.stats")
        data = resp.get_json()
        self.assertIn("domain_id", data)
        self.assertIn("product_id", data)

    def test_unknown_function_returns_404(self):
        """未知函数返回 404 + 可用函数列表。"""
        resp = self.client.get("/api/viz/nonexistent.function")
        self.assertEqual(resp.status_code, 404)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("available_functions", data)
        self.assertGreater(len(data["available_functions"]), 0)

    def test_missing_required_param_returns_400(self):
        """缺少必填参数返回 400。"""
        resp = self.client.get("/api/viz/notes.search")  # keyword required
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("error", data)

    def test_post_method_supported(self):
        """POST /api/viz/<function_name> 支持复杂参数。"""
        resp = self.client.post("/api/viz/overview.stats",
                                 data=json.dumps({"time_range": "7d"}),
                                 content_type="application/json")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["function_name"], "overview.stats")

    def test_system_runtime_endpoint(self):
        """system.runtime 返回真实系统数据。"""
        resp = self.client.get("/api/viz/system.runtime?domain_id=system")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIsNotNone(data["data"]["items"])

    def test_system_database_tables_endpoint(self):
        """system.database_tables 返回表列表。"""
        resp = self.client.get("/api/viz/system.database_tables?domain_id=system")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertGreater(len(data["data"]["items"]), 0)

    def test_ai_call_logs_endpoint(self):
        """ai.call_logs 返回调用日志。"""
        resp = self.client.get("/api/viz/ai.call_logs?domain_id=system")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("success", data)

    def test_domain_isolation_zbmp_only(self):
        """zbmp 域函数在 cth domain 下返回 403。"""
        # overview.industry_dist is zbmp domain
        resp = self.client.get("/api/viz/overview.industry_dist?domain_id=cth")
        self.assertEqual(resp.status_code, 403)
        data = resp.get_json()
        self.assertFalse(data["success"])

    def test_all_domain_function_works_for_any_domain(self):
        """all 域函数在任何 domain 下都可访问。"""
        resp = self.client.get("/api/viz/overview.stats?domain_id=zbmp")
        self.assertEqual(resp.status_code, 200)

    def test_data_status_explicitly_returned(self):
        """data_status 字段显式返回（ok/no_data/error）。"""
        resp = self.client.get("/api/viz/overview.stats")
        data = resp.get_json()
        self.assertIn("data_status", data["data"])
        self.assertIn(data["data"]["data_status"], ("ok", "no_data", "error", "stale", "partial", "unavailable"))

    def test_no_api_key_in_output(self):
        """响应中不包含 API key / secret / password。"""
        resp = self.client.get("/api/viz/ai.call_logs")
        raw = resp.get_data(as_text=True).lower()
        for sensitive in ("api_key", "secret", "password", "authorization", "bearer", "cookie"):
            self.assertNotIn(sensitive, raw, f"sensitive field {sensitive} found in output")


# ═══════════════════════════════════════════════════════════════════════════
# 5. 缺失值处理测试
# ═══════════════════════════════════════════════════════════════════════════

class TestMissingValueHandling(unittest.TestCase):
    """数据缺失显式 null/unknown/missing，禁止 0 或默认值填充。"""

    def test_empty_data_current_value_is_none(self):
        """无数据时 current_value 为 None（不是 0）。"""
        from ui_view_model import DataQuery, DataResult, DataStatus
        dr = DataResult(query=DataQuery(source="test"), records=[], total=0, status=DataStatus.NO_DATA)
        tt = build_truth_table(dr)
        # current_value 应该由调用方根据 metrics 计算，空数据时 MetricValue.value 为 None
        from ui_view_model import MetricLayer
        ml = MetricLayer()
        metrics = ml.compute_all([])
        self.assertIsNone(metrics["total"].value)

    def test_confidence_unknown_for_no_data(self):
        """无数据时 confidence 为 unknown。"""
        from ui_view_model import DataQuery, DataResult, DataStatus
        dr = DataResult(query=DataQuery(source="test"), records=[], total=0, status=DataStatus.NO_DATA)
        tt = build_truth_table(dr)
        self.assertEqual(tt.confidence, ConfidenceLevel.UNKNOWN)

    def test_freshness_unknown_for_no_timestamp(self):
        """无 source_timestamp 时 freshness 相关字段为 None/unknown。"""
        from ui_view_model import DataQuery, DataResult, DataStatus
        dr = DataResult(query=DataQuery(source="test"), records=[], total=0,
                         status=DataStatus.NO_DATA, source_timestamp=None)
        tt = build_truth_table(dr)
        self.assertIsNone(tt.staleness_seconds)
        self.assertFalse(tt.fresh)

    def test_delta_unknown_when_no_previous(self):
        """无上一周期数据时 delta 方向为 unknown/flat，值为 None。"""
        from ui_view_model import Delta
        d = Delta()
        self.assertIsNone(d.value)
        self.assertIsNone(d.percent)
        self.assertEqual(d.direction, "flat")


if __name__ == "__main__":
    unittest.main(verbosity=2)
