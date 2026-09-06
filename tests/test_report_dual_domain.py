# -*- coding: utf-8 -*-
"""
Report 双域生成测试（ZBC V2.0）
================================
覆盖：
  1. ZBMP 报告类型（6类）和 CTH 报告类型（6类）
  2. generate_report 支持 domain_id 参数
  3. CTH 报告保护太古汇专项规则
  4. ZBMP 报告不使用 CTH 专项过滤
  5. 报告文件真实落盘、大小合理、内容非空、域数据正确
  6. 共享 Report Engine 但使用各自模板
"""
import os
import sys
import json
import pytest
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from report_engine import (
    CTH_REPORT_TYPES, ZBMP_REPORT_TYPES, DUAL_DOMAIN_REPORTS,
    generate_domain_report, list_domain_reports, verify_domain_report_file,
)


class TestReportTypeDefinitions:
    """验证双域报告类型定义。"""

    def test_cth_report_types(self):
        assert "daily" in CTH_REPORT_TYPES
        assert "weekly" in CTH_REPORT_TYPES
        assert "monthly" in CTH_REPORT_TYPES
        assert "event_special" in CTH_REPORT_TYPES
        assert "risk_special" in CTH_REPORT_TYPES
        assert "taikoo_intelligence" in CTH_REPORT_TYPES

    def test_zbmp_report_types(self):
        assert "brand" in ZBMP_REPORT_TYPES
        assert "performance" in ZBMP_REPORT_TYPES
        assert "competitive" in ZBMP_REPORT_TYPES
        assert "growth" in ZBMP_REPORT_TYPES
        assert "content" in ZBMP_REPORT_TYPES
        assert "brand_risk" in ZBMP_REPORT_TYPES

    def test_report_types_are_different(self):
        """CTH 和 ZBMP 报告类型不重叠（各自专项）。"""
        cth_set = set(CTH_REPORT_TYPES)
        zbmp_set = set(ZBMP_REPORT_TYPES)
        # 两域报告类型应完全不同（daily/weekly/monthly 是 legacy 通用类型）
        # 但 domain-specific 类型不应重叠
        specific_cth = cth_set - {"daily", "weekly", "monthly"}
        specific_zbmp = zbmp_set - {"daily", "weekly", "monthly"}
        assert specific_cth.isdisjoint(specific_zbmp)

    def test_dual_domain_registry(self):
        assert "cth" in DUAL_DOMAIN_REPORTS
        assert "zbmp" in DUAL_DOMAIN_REPORTS
        assert len(DUAL_DOMAIN_REPORTS["cth"]) == 6
        assert len(DUAL_DOMAIN_REPORTS["zbmp"]) == 6


class TestGenerateDomainReport:
    """验证双域报告真实生成。"""

    def test_generate_cth_report(self, tmp_path):
        result = generate_domain_report(
            report_type="daily",
            domain_id="cth",
            output_dir=str(tmp_path),
        )
        assert result["status"] == "success"
        assert result["domain_id"] == "cth"
        assert result["product_id"] == "CTH"
        assert os.path.exists(result["file_path"])
        assert result["file_size"] > 0

    def test_generate_zbmp_report(self, tmp_path):
        result = generate_domain_report(
            report_type="brand",
            domain_id="zbmp",
            output_dir=str(tmp_path),
        )
        assert result["status"] == "success"
        assert result["domain_id"] == "zbmp"
        assert result["product_id"] == "ZBMP"
        assert os.path.exists(result["file_path"])
        assert result["file_size"] > 0

    def test_cth_report_has_protected_flags(self, tmp_path):
        """CTH 报告应包含太古汇专项保护标记。"""
        result = generate_domain_report(
            report_type="risk_special",
            domain_id="cth",
            output_dir=str(tmp_path),
        )
        report_data = result["report_data"]
        assert report_data.get("protected") is True
        cth_specific = report_data.get("cth_specific", {})
        assert cth_specific.get("subject_words_protected") is True
        assert cth_specific.get("subject_hit_enabled") is True
        assert cth_specific.get("brand_count") == 199
        assert cth_specific.get("business_formats") == 9

    def test_zbmp_report_no_cth_filtering(self, tmp_path):
        """ZBMP 报告不应使用 CTH 专项过滤条件。"""
        result = generate_domain_report(
            report_type="competitive",
            domain_id="zbmp",
            output_dir=str(tmp_path),
        )
        report_data = result["report_data"]
        assert report_data.get("protected") is False
        zbmp_specific = report_data.get("zbmp_specific", {})
        assert zbmp_specific.get("multi_brand") is True
        assert zbmp_specific.get("competitive_analysis") is True
        # ZBMP 报告不应有 cth_specific 标记
        assert "cth_specific" not in report_data or report_data.get("cth_specific") is None

    def test_report_file_content_non_empty(self, tmp_path):
        result = generate_domain_report(
            report_type="taikoo_intelligence",
            domain_id="cth",
            output_dir=str(tmp_path),
        )
        with open(result["file_path"], "r", encoding="utf-8") as f:
            data = json.load(f)
        assert len(data) > 0
        assert data["domain_id"] == "cth"
        assert data["report_type"] == "taikoo_intelligence"

    def test_invalid_domain_raises(self):
        with pytest.raises(ValueError, match="未知域"):
            generate_domain_report("daily", domain_id="nonexistent")

    def test_invalid_report_type_for_domain_raises(self):
        with pytest.raises(ValueError, match="不支持报告类型"):
            generate_domain_report("brand", domain_id="cth")  # brand 是 ZBMP 类型


class TestVerifyDomainReportFile:
    """验证报告文件校验。"""

    def test_verify_valid_cth_report(self, tmp_path):
        result = generate_domain_report(
            "daily", "cth", output_dir=str(tmp_path),
        )
        verification = verify_domain_report_file(result["file_path"])
        assert verification["valid"] is True
        assert verification["domain_id"] == "cth"
        assert verification["product_id"] == "CTH"
        assert verification["content_non_empty"] is True
        assert verification["size_reasonable"] is True

    def test_verify_valid_zbmp_report(self, tmp_path):
        result = generate_domain_report(
            "growth", "zbmp", output_dir=str(tmp_path),
        )
        verification = verify_domain_report_file(result["file_path"])
        assert verification["valid"] is True
        assert verification["domain_id"] == "zbmp"
        assert verification["product_id"] == "ZBMP"

    def test_verify_nonexistent_file(self):
        verification = verify_domain_report_file("/nonexistent/path/report.json")
        assert verification["valid"] is False
        assert verification["reason"] == "文件不存在"

    def test_verify_empty_file(self, tmp_path):
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("")
        verification = verify_domain_report_file(str(empty_file))
        assert verification["valid"] is False
        assert verification["file_size"] == 0


class TestListDomainReports:
    def test_list_all_domains(self):
        reports = list_domain_reports()
        assert "cth" in reports
        assert "zbmp" in reports

    def test_list_specific_domain(self):
        reports = list_domain_reports(domain_id="cth")
        assert "cth" in reports
        assert "zbmp" not in reports

    def test_report_names(self):
        reports = list_domain_reports()
        assert reports["cth"]["daily"]["name"] == "太古汇日报"
        assert reports["zbmp"]["brand"]["name"] == "品牌报告"


class TestReportDomainIsolation:
    """验证报告域隔离：CTH 和 ZBMP 报告数据不混。"""

    def test_cth_and_zbmp_reports_separate_files(self, tmp_path):
        cth_result = generate_domain_report(
            "daily", "cth", output_dir=str(tmp_path),
        )
        zbmp_result = generate_domain_report(
            "brand", "zbmp", output_dir=str(tmp_path),
        )
        # 文件路径不同
        assert cth_result["file_path"] != zbmp_result["file_path"]
        # 域身份不同
        assert cth_result["domain_id"] != zbmp_result["domain_id"]
        # 两个文件都存在
        assert os.path.exists(cth_result["file_path"])
        assert os.path.exists(zbmp_result["file_path"])

    def test_report_generator_version(self, tmp_path):
        result = generate_domain_report(
            "content", "zbmp", output_dir=str(tmp_path),
        )
        assert result["report_data"]["generator_version"] == "dual-domain-v2.0"
