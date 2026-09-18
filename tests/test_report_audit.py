# -*- coding: utf-8 -*-
"""
tests/test_report_audit.py — ZBC Phase 9 报告系统 artifact 真实性审计测试

核心原则：报告必须是真实 artifact，禁止假成功、空文件成功。
所有测试使用 tmp_path / mock，不触碰生产数据库，不执行真实报告生成。
"""
import hashlib
import json
import os
import sys
import tempfile
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lumenis.shared.reporting import artifact as ra


# ============================================================
# 1. report_artifact 模块基础功能
# ============================================================

class TestReportArtifactModule:
    """lumenis/shared/reporting/artifact.py 基础功能测试。"""

    def test_compute_hash_deterministic(self):
        """SHA-256 hash 对相同输入必须确定性。"""
        data = b"test report content"
        h1 = ra.compute_hash(data)
        h2 = ra.compute_hash(data)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex length

    def test_compute_hash_different_input(self):
        """不同输入必须产生不同 hash。"""
        assert ra.compute_hash(b"aaa") != ra.compute_hash(b"bbb")

    def test_generate_report_id_deterministic(self):
        """report_id 对同周期同类型必须确定性。"""
        rid1 = ra.generate_report_id("daily", "2026-09-01", "2026-09-01")
        rid2 = ra.generate_report_id("daily", "2026-09-01", "2026-09-01")
        assert rid1 == rid2
        assert rid1.startswith("RPT-daily-")

    def test_generate_report_id_different_period(self):
        """不同周期必须产生不同 report_id。"""
        rid1 = ra.generate_report_id("daily", "2026-09-01", "2026-09-01")
        rid2 = ra.generate_report_id("weekly", "2026-09-01", "2026-09-07")
        assert rid1 != rid2

    def test_build_artifact_metadata_has_all_fields(self):
        """build_artifact_metadata 必须包含所有元数据字段。"""
        report_data = {"report_type": "daily", "total_notes": 10, "positive_count": 3}
        meta = ra.build_artifact_metadata("daily", "2026-09-01", "2026-09-01", report_data)
        assert "report_id" in meta
        assert "generated_at" in meta
        assert "generator_version" in meta
        assert "data_version" in meta
        assert "artifact_hash" in meta
        assert meta["generator_version"] == ra.GENERATOR_VERSION
        assert len(meta["artifact_hash"]) == 64

    def test_build_artifact_hash_excludes_self(self):
        """artifact_hash 计算必须排除 hash 自身和 generated_at，保证可复算。"""
        report_data = {"report_type": "daily", "total_notes": 5}
        meta1 = ra.build_artifact_metadata("daily", "2026-09-01", "2026-09-01", report_data)
        # 手动复算 hash（排除 artifact_hash/generated_at/data_version）
        snapshot = {k: v for k, v in report_data.items()
                    if k not in ("artifact_hash", "generated_at", "data_version")}
        expected = hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
        ).hexdigest()
        assert meta1["artifact_hash"] == expected


# ============================================================
# 2. 文件 artifact 真实性验证
# ============================================================

class TestFileArtifactVerification:
    """文件 artifact 存在+非空+hash 校验。"""

    def test_verify_valid_artifact(self, tmp_path):
        """有效文件（存在+非空）必须验证通过。"""
        f = tmp_path / "report.xlsx"
        f.write_bytes(b"x" * 500)  # 超过 xlsx 最小 200 字节
        v = ra.verify_artifact_file(str(f))
        assert v["exists"] is True
        assert v["size"] == 500
        assert v["valid"] is True
        assert len(v["hash"]) == 64
        assert v["reason"] == ""

    def test_verify_nonexistent_file(self):
        """不存在的文件必须验证失败。"""
        v = ra.verify_artifact_file("/nonexistent/path/report.xlsx")
        assert v["exists"] is False
        assert v["valid"] is False
        assert "不存在" in v["reason"]

    def test_verify_empty_file_fails(self, tmp_path):
        """空文件必须验证失败（禁止空文件成功）。"""
        f = tmp_path / "report.xlsx"
        f.write_bytes(b"")
        v = ra.verify_artifact_file(str(f))
        assert v["exists"] is True
        assert v["size"] == 0
        assert v["valid"] is False
        assert "过小" in v["reason"] or "空" in v["reason"]

    def test_verify_too_small_file_fails(self, tmp_path):
        """过小文件（低于格式最小字节数）必须验证失败。"""
        f = tmp_path / "report.xlsx"
        f.write_bytes(b"x" * 10)  # xlsx 最小 200
        v = ra.verify_artifact_file(str(f))
        assert v["valid"] is False

    def test_verify_csv_min_bytes(self, tmp_path):
        """CSV 最小 32 字节，32 字节以上应通过。"""
        f = tmp_path / "report.csv"
        f.write_bytes(b"x" * 40)
        v = ra.verify_artifact_file(str(f))
        assert v["valid"] is True

    def test_verify_empty_path_fails(self):
        """空路径必须验证失败。"""
        v = ra.verify_artifact_file("")
        assert v["valid"] is False

    def test_assert_artifact_or_raise_valid(self, tmp_path):
        """assert_artifact_or_raise 对有效文件不抛异常。"""
        f = tmp_path / "report.docx"
        f.write_bytes(b"x" * 300)
        v = ra.assert_artifact_or_raise(str(f))
        assert v["valid"] is True

    def test_assert_artifact_or_raise_invalid(self, tmp_path):
        """assert_artifact_or_raise 对空文件必须抛 RuntimeError。"""
        f = tmp_path / "report.docx"
        f.write_bytes(b"")
        with pytest.raises(RuntimeError, match="artifact 校验失败"):
            ra.assert_artifact_or_raise(str(f))

    def test_compute_file_hash_matches(self, tmp_path):
        """compute_file_hash 必须与 compute_hash 一致。"""
        f = tmp_path / "data.bin"
        content = b"hello world" * 100
        f.write_bytes(content)
        assert ra.compute_file_hash(str(f)) == ra.compute_hash(content)


# ============================================================
# 3. 报告 dict artifact 验证
# ============================================================

class TestReportDictVerification:
    """verify_report_dict 对 DB/内存报告 dict 的校验。"""

    def test_valid_report_dict(self):
        """有效报告 dict 必须验证通过。"""
        report = {
            "report_type": "daily",
            "report_date": "2026-09-01",
            "total_notes": 10,
            "generated_at": "2026-09-01 10:00:00",
            "report_id": "RPT-daily-2026-09-01-2026-09-01",
            "artifact_hash": "a" * 64,
        }
        v = ra.verify_report_dict(report)
        assert v["valid"] is True
        assert v["report_id"] == report["report_id"]

    def test_empty_report_fails(self):
        """空报告必须验证失败。"""
        assert ra.verify_report_dict(None)["valid"] is False
        assert ra.verify_report_dict({})["valid"] is False
        assert ra.verify_report_dict([])["valid"] is False

    def test_missing_report_type_fails(self):
        """缺少 report_type 必须验证失败。"""
        report = {"report_date": "2026-09-01", "total_notes": 5}
        assert ra.verify_report_dict(report)["valid"] is False

    def test_missing_report_date_fails(self):
        """缺少 report_date 必须验证失败。"""
        report = {"report_type": "daily", "total_notes": 5}
        assert ra.verify_report_dict(report)["valid"] is False

    def test_non_numeric_total_notes_fails(self):
        """total_notes 非数字必须验证失败。"""
        report = {"report_type": "daily", "report_date": "2026-09-01", "total_notes": "abc"}
        assert ra.verify_report_dict(report)["valid"] is False

    def test_report_id_generated_when_missing(self):
        """缺少 report_id 时应自动生成（不影响 valid）。"""
        report = {
            "report_type": "weekly",
            "report_date": "2026-09-07",
            "period_start": "2026-09-01",
            "period_end": "2026-09-07",
            "total_notes": 20,
        }
        v = ra.verify_report_dict(report)
        assert v["valid"] is True
        assert v["report_id"] == "RPT-weekly-2026-09-01-2026-09-07"


# ============================================================
# 4. 时间口径测试（publish_datetime vs captured_at）
# ============================================================

class TestTime口径:
    """报告时间口径必须默认 publish_datetime，不得混淆 captured_at。"""

    def test_database_get_notes_uses_publish_date(self):
        """database.get_notes_by_date_range 的 SQL 必须使用 publish_date。"""
        import inspect
        import database as db
        source = inspect.getsource(db.get_notes_by_date_range)
        assert "publish_date BETWEEN" in source
        # 不得使用 collected_at 作为主筛选
        assert "collected_at BETWEEN" not in source

    def test_database_get_stats_uses_publish_date(self):
        """database.get_stats_by_date_range 必须使用 publish_date。"""
        import inspect
        import database as db
        source = inspect.getsource(db.get_stats_by_date_range)
        assert "publish_date BETWEEN" in source
        assert "collected_at BETWEEN" not in source

    def test_export_filter_uses_publish_date(self):
        """Shared Reporting export_api.filter_notes_by_period 必须使用 publish_date。"""
        import inspect
        from lumenis.shared.reporting import export_api as er
        source = inspect.getsource(er.filter_notes_by_period)
        assert "publish_date" in source
        # 日报逻辑用 publish_date >= day_before，周期用 publish_date BETWEEN
        assert "publish_date >= ?" in source or "publish_date >= ? AND publish_date <= ?" in source

    def test_report_export_engine_uses_publish_date(self):
        """Shared Reporting export_engine._notes 必须优先使用 publish_date。"""
        import inspect
        # 动态导入 report_export 下的模块
        import importlib.util
        mod_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "lumenis", "shared", "reporting", "export_engine.py")
        spec = importlib.util.spec_from_file_location("report_export_engine", mod_path)
        mod = importlib.util.module_from_spec(spec)
        # 不执行模块（避免依赖），只读源码
        with open(mod_path, "r", encoding="utf-8") as f:
            source = f.read()
        assert "publish_date" in source
        assert "publish_datetime" in source

    def test_report_filter_fallback_collected_at_is_flagged(self):
        """Shared Reporting filtering 在无 publish_date 时回退 collected_at，这是已知行为。
        测试确认回退逻辑存在（审计标记为 P2 待优化）。"""
        import inspect
        from lumenis.shared.reporting import filtering as rf
        source = inspect.getsource(rf.filter_notes_for_daily_report)
        # 确认存在 collected_at 回退（已知时间口径混淆点）
        assert "collected_at" in source


# ============================================================
# 5. 主体过滤测试
# ============================================================

class TestSubjectFiltering:
    """报告数据必须经过 SUBJECT_WORDS/subject_hit() 过滤。"""

    def test_database_verified_base_has_subject_filter(self):
        """database._verified_base 必须包含主体过滤。"""
        import inspect
        import database as db
        source = inspect.getsource(db._verified_base)
        assert "is_taikoo_verified=1" in source
        assert "relevance_status" in source
        assert "subject" in source.lower() or "_subject_clause" in source

    def test_export_report_has_subject_filter(self):
        """Shared Reporting export_api.filter_notes_by_period 必须包含主体过滤（Phase 9 修复）。"""
        import inspect
        from lumenis.shared.reporting import export_api as er
        source = inspect.getsource(er.filter_notes_by_period)
        assert "is_taikoo_verified=1" in source
        assert "subject_sql_and_values" in source or "subject" in source.lower()

    def test_report_export_engine_has_subject_filter(self):
        """Shared Reporting export_engine._notes 必须包含主体过滤（Phase 9 修复）。"""
        mod_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "lumenis", "shared", "reporting", "export_engine.py")
        with open(mod_path, "r", encoding="utf-8") as f:
            source = f.read()
        assert "is_taikoo_verified=1" in source
        assert "subject_sql_and_values" in source

    def test_api_report_daily_has_subject_filter(self):
        """Shared Reporting routes.api_report_daily 必须包含 subject_sql_and_values。"""
        import inspect
        from lumenis.shared.reporting import routes as rap
        source = inspect.getsource(rap.api_report_daily)
        assert "subject_sql_and_values" in source

    def test_no_full_table_scan_in_export(self):
        """Shared Reporting export_api 不得出现无主体过滤的全表扫描 SELECT * FROM notes WHERE 1=1。"""
        import inspect
        from lumenis.shared.reporting import export_api as er
        source = inspect.getsource(er.filter_notes_by_period)
        # 修复后不应有裸的 WHERE 1=1 全表扫描
        assert "SELECT * FROM notes WHERE 1=1" not in source


# ============================================================
# 6. export 不重复生成（artifact 复用）
# ============================================================

class TestExportArtifactReuse:
    """同周期同格式已有有效 artifact 时应可复用，避免重复生成。"""

    def test_find_existing_artifact_finds_valid(self, tmp_path):
        """find_existing_artifact 应找到同周期的有效文件。"""
        # 创建一个模拟已有导出文件
        existing = tmp_path / "太古汇舆情_daily_2026-09-01_2026-09-01.xlsx"
        existing.write_bytes(b"x" * 500)
        result = ra.find_existing_artifact(str(tmp_path), "daily", "2026-09-01", "2026-09-01", "xlsx")
        assert result is not None
        assert os.path.basename(result) == existing.name

    def test_find_existing_artifact_skips_empty(self, tmp_path):
        """find_existing_artifact 应跳过空文件（不复用无效 artifact）。"""
        empty = tmp_path / "太古汇舆情_daily_2026-09-01_2026-09-01.xlsx"
        empty.write_bytes(b"")  # 空文件
        result = ra.find_existing_artifact(str(tmp_path), "daily", "2026-09-01", "2026-09-01", "xlsx")
        assert result is None  # 空文件不应被复用

    def test_find_existing_artifact_nonexistent_dir(self):
        """目录不存在时返回 None。"""
        result = ra.find_existing_artifact("/nonexistent/dir", "daily", "2026-09-01", "2026-09-01", "xlsx")
        assert result is None

    def test_find_existing_artifact_wrong_format(self, tmp_path):
        """不同格式不应匹配。"""
        f = tmp_path / "太古汇舆情_daily_2026-09-01_2026-09-01.xlsx"
        f.write_bytes(b"x" * 500)
        result = ra.find_existing_artifact(str(tmp_path), "daily", "2026-09-01", "2026-09-01", "docx")
        assert result is None


# ============================================================
# 7. Shared Reporting engine 落库验证（mock，不碰真实 DB）
# ============================================================

class TestReportEngineArtifactVerification:
    """Shared Reporting engine.generate_report 必须验证落库成功。"""

    def test_generate_report_raises_on_zero_row_id(self):
        """save_daily_report 返回 0 或 None 时必须抛异常（禁止假成功）。"""
        from lumenis.shared.reporting import engine as report_engine
        # mock 所有外部依赖
        with patch.object(report_engine.db, 'get_notes_by_date_range', return_value=[]), \
             patch.object(report_engine.db, 'get_stats_by_date_range', return_value={'total': 0}), \
             patch.object(report_engine.ai_analyzer, 'generate_period_report', return_value={}), \
             patch.object(report_engine.ai_filter, 'run_filter_batch', return_value=None), \
             patch.object(report_engine.db, 'save_daily_report', return_value=0):
            with pytest.raises(RuntimeError, match="落库失败"):
                report_engine.generate_report("daily", "2026-09-01", "2026-09-01")

    def test_generate_report_raises_on_none_row_id(self):
        """save_daily_report 返回 None 时必须抛异常。"""
        from lumenis.shared.reporting import engine as report_engine
        with patch.object(report_engine.db, 'get_notes_by_date_range', return_value=[]), \
             patch.object(report_engine.db, 'get_stats_by_date_range', return_value={'total': 0}), \
             patch.object(report_engine.ai_analyzer, 'generate_period_report', return_value={}), \
             patch.object(report_engine.ai_filter, 'run_filter_batch', return_value=None), \
             patch.object(report_engine.db, 'save_daily_report', return_value=None):
            with pytest.raises(RuntimeError, match="落库失败"):
                report_engine.generate_report("daily", "2026-09-01", "2026-09-01")

    def test_generate_report_success_has_artifact_metadata(self):
        """成功生成的报告必须包含 artifact 元数据字段。"""
        from lumenis.shared.reporting import engine as report_engine
        mock_report = {"summary": "test", "top_topics": [], "hot_notes": []}
        with patch.object(report_engine.db, 'get_notes_by_date_range', return_value=[]), \
             patch.object(report_engine.db, 'get_stats_by_date_range', return_value={'total': 0}), \
             patch.object(report_engine.ai_analyzer, 'generate_period_report', return_value=mock_report), \
             patch.object(report_engine.ai_filter, 'run_filter_batch', return_value=None), \
             patch.object(report_engine.daily, 'generate_daily_digest', return_value={}), \
             patch.object(report_engine.db, 'save_daily_report', return_value=42) as mock_save:
            report, digest = report_engine.generate_report("daily", "2026-09-01", "2026-09-01")
            assert report["_db_row_id"] == 42
            assert report["_artifact_verified"] is True
            assert "report_id" in report
            assert "artifact_hash" in report
            assert "generator_version" in report
            assert "data_version" in report
            assert "source_snapshot" in report
            # 验证 save_daily_report 收到了元数据
            saved = mock_save.call_args[0][0]
            assert saved["report_id"].startswith("RPT-daily-")
            assert len(saved["artifact_hash"]) == 64

    def test_get_bundle_cached_returns_regenerated_false(self):
        """get_bundle 缓存命中时 regenerated=False。"""
        from lumenis.shared.reporting import engine as report_engine
        cached_report = {
            "report_type": "daily", "report_date": "2026-09-01",
            "total_notes": 5, "report_id": "RPT-daily-2026-09-01-2026-09-01",
        }
        with patch.object(report_engine.db, 'get_latest_report', return_value=cached_report), \
             patch.object(report_engine.db, 'get_latest_digest', return_value={}):
            bundle = report_engine.get_bundle("daily", "2026-09-01")
            assert bundle["regenerated"] is False
            assert bundle["artifact_verified"] is True

    def test_get_bundle_miss_triggers_regeneration_flag(self):
        """get_bundle 缓存未命中时 regenerated=True（调用方可感知数据漂移）。"""
        from lumenis.shared.reporting import engine as report_engine
        with patch.object(report_engine.db, 'get_latest_report', return_value=None), \
             patch.object(report_engine, 'generate_report', return_value=({"_artifact_verified": True, "_db_row_id": 1}, {})):
            bundle = report_engine.get_bundle("daily", "2026-09-01")
            assert bundle["regenerated"] is True


# ============================================================
# 8. DB 迁移列存在性
# ============================================================

class TestDatabaseMigration:
    """daily_reports 表必须包含 Phase 9 新增的 artifact 元数据列。"""

    def test_daily_reports_has_artifact_columns(self):
        """daily_reports 表必须有 report_id/artifact_hash/generator_version/data_version/source_snapshot。"""
        import sqlite3
        import database as db
        # 用内存数据库测试迁移
        conn = sqlite3.connect(":memory:")
        conn.executescript(db.SCHEMA)
        # 应用 REPORT_MIGRATIONS
        cols = {r[1] for r in conn.execute('PRAGMA table_info(daily_reports)').fetchall()}
        for col, ddl in db.REPORT_MIGRATIONS.items():
            if col not in cols:
                conn.execute(ddl)
        cols = {r[1] for r in conn.execute('PRAGMA table_info(daily_reports)').fetchall()}
        conn.close()
        required = ['report_id', 'artifact_hash', 'generator_version', 'data_version', 'source_snapshot']
        for col in required:
            assert col in cols, f"daily_reports 缺少列: {col}"

    def test_save_daily_report_includes_artifact_fields(self):
        """save_daily_report 的 INSERT/UPDATE 必须包含 artifact 元数据字段。"""
        import inspect
        import database as db
        source = inspect.getsource(db.save_daily_report)
        for field in ['report_id', 'artifact_hash', 'generator_version', 'data_version', 'source_snapshot']:
            assert field in source, f"save_daily_report 缺少字段: {field}"


# ============================================================
# 9. API 层假成功防护（源码静态检查）
# ============================================================

class TestAPIFakeSuccessPrevention:
    """API 层不得存在异常时返回 ok=True 的假成功模式。"""

    def test_reports_list_no_fake_success_on_error(self):
        """api_reports_list 异常分支必须返回 ok=False。"""
        import inspect
        from lumenis.shared.reporting import routes as rap
        source = inspect.getsource(rap.api_reports_list)
        # 异常分支不应有 ok: True
        except_section = source.split("except Exception")[1] if "except Exception" in source else ""
        assert "'ok': True" not in except_section
        assert "'ok': False" in except_section or "ok': False" in except_section

    def test_generate_report_verifies_artifact(self):
        """api_generate_report 必须验证 _artifact_verified。"""
        import inspect
        from lumenis.shared.reporting import routes as rap
        source = inspect.getsource(rap.api_generate_report)
        assert "_artifact_verified" in source
        assert "_db_row_id" in source

    def test_brand_report_export_verifies_file(self):
        """brand_report_export 必须调用 artifact 验证。"""
        import inspect
        from lumenis.shared.reporting import routes as rap
        source = inspect.getsource(rap.brand_report_export)
        assert "verify_artifact_file" in source or "artifact" in source.lower()

    def test_api_report_uses_verify_report_dict(self):
        """api_report 必须调用 verify_report_dict 而非仅 bool(report)。"""
        import inspect
        from lumenis.shared.reporting import routes as rap
        source = inspect.getsource(rap.api_report)
        assert "verify_report_dict" in source
        # 不应仅有 bool(bundle.get('report'))
        assert "bool(bundle.get('report'))" not in source


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])