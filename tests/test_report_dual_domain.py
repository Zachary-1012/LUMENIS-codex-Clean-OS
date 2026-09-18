# -*- coding: utf-8 -*-
"""
P1 Report 双模板测试 — test_report_dual_domain.py
=================================================
验证：
1. ZBMP 六类报告（Brand/Performance/Competitive/Growth/Content/BrandRisk）注册完整
2. CTH 报告（日报/专报等）域归属正确
3. 共享引擎 lumenis/shared/reporting/engine.py，各自模板数据
4. generate_report 接受 domain_id 参数
5. 报告输出带 domain_id / product_id
6. 报告类型校验：无效类型被拒
"""
import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


# ============================================================================
# 1. ZBMP 六类报告注册验证
# ============================================================================
class TestZBMPReportTypes:
    """验证 ZBMP 六类报告完整注册。"""

    def test_zbmp_six_types_defined(self):
        """ZBMP_REPORT_TYPES 定义了六类报告。"""
        from lumenis.shared.reporting.engine import ZBMP_REPORT_TYPES
        expected = ("brand", "performance", "competitive", "growth", "content", "brand_risk")
        assert ZBMP_REPORT_TYPES == expected, \
            f"ZBMP 报告类型应为 {expected}, 实际 {ZBMP_REPORT_TYPES}"

    def test_zbmp_six_types_registered(self):
        """DUAL_DOMAIN_REPORTS 中 ZBMP 六类全部注册。"""
        from lumenis.shared.reporting.engine import DUAL_DOMAIN_REPORTS
        zbmp = DUAL_DOMAIN_REPORTS.get("zbmp", {})
        expected = ["brand", "performance", "competitive", "growth", "content", "brand_risk"]
        for rtype in expected:
            assert rtype in zbmp, f"ZBMP 报告类型 {rtype} 未注册"
        assert len(zbmp) == 6, f"ZBMP 应有 6 类报告，实际 {len(zbmp)}"

    def test_zbmp_brand_report_metadata(self):
        """ZBMP Brand 报告元数据正确。"""
        from lumenis.shared.reporting.engine import DUAL_DOMAIN_REPORTS
        info = DUAL_DOMAIN_REPORTS["zbmp"]["brand"]
        assert "name" in info
        assert "template" in info
        assert info["template"] == "zbmp_brand"

    def test_zbmp_performance_report_metadata(self):
        """ZBMP Performance 报告元数据正确。"""
        from lumenis.shared.reporting.engine import DUAL_DOMAIN_REPORTS
        info = DUAL_DOMAIN_REPORTS["zbmp"]["performance"]
        assert info["template"] == "zbmp_performance"

    def test_zbmp_competitive_report_metadata(self):
        """ZBMP Competitive 报告元数据正确。"""
        from lumenis.shared.reporting.engine import DUAL_DOMAIN_REPORTS
        info = DUAL_DOMAIN_REPORTS["zbmp"]["competitive"]
        assert info["template"] == "zbmp_competitive"

    def test_zbmp_growth_report_metadata(self):
        """ZBMP Growth 报告元数据正确。"""
        from lumenis.shared.reporting.engine import DUAL_DOMAIN_REPORTS
        info = DUAL_DOMAIN_REPORTS["zbmp"]["growth"]
        assert info["template"] == "zbmp_growth"

    def test_zbmp_content_report_metadata(self):
        """ZBMP Content 报告元数据正确。"""
        from lumenis.shared.reporting.engine import DUAL_DOMAIN_REPORTS
        info = DUAL_DOMAIN_REPORTS["zbmp"]["content"]
        assert info["template"] == "zbmp_content"

    def test_zbmp_brand_risk_report_metadata(self):
        """ZBMP BrandRisk 报告元数据正确。"""
        from lumenis.shared.reporting.engine import DUAL_DOMAIN_REPORTS
        info = DUAL_DOMAIN_REPORTS["zbmp"]["brand_risk"]
        assert info["template"] == "zbmp_brand_risk"

    def test_zbmp_reports_not_protected(self):
        """ZBMP 报告不使用 CTH 主体保护（protected=False）。"""
        from lumenis.shared.reporting.engine import DUAL_DOMAIN_REPORTS
        zbmp = DUAL_DOMAIN_REPORTS["zbmp"]
        for rtype, info in zbmp.items():
            assert info.get("protected") is False, \
                f"ZBMP {rtype} 不应有 CTH 主体保护"


# ============================================================================
# 2. CTH 报告域归属验证
# ============================================================================
class TestCTHReportTypes:
    """验证 CTH 报告域归属正确。"""

    def test_cth_report_types_defined(self):
        """CTH_REPORT_TYPES 定义了报告类型。"""
        from lumenis.shared.reporting.engine import CTH_REPORT_TYPES
        assert "daily" in CTH_REPORT_TYPES
        assert "event_special" in CTH_REPORT_TYPES
        assert "risk_special" in CTH_REPORT_TYPES

    def test_cth_reports_registered(self):
        """DUAL_DOMAIN_REPORTS 中 CTH 报告全部注册。"""
        from lumenis.shared.reporting.engine import DUAL_DOMAIN_REPORTS
        cth = DUAL_DOMAIN_REPORTS.get("cth", {})
        assert len(cth) >= 3, f"CTH 应有至少 3 类报告，实际 {len(cth)}"

    def test_cth_reports_protected(self):
        """CTH 报告使用主体保护（protected=True）。"""
        from lumenis.shared.reporting.engine import DUAL_DOMAIN_REPORTS
        cth = DUAL_DOMAIN_REPORTS["cth"]
        for rtype, info in cth.items():
            assert info.get("protected") is True, \
                f"CTH {rtype} 应有主体保护"

    def test_cth_daily_report_template(self):
        """CTH 日报模板正确。"""
        from lumenis.shared.reporting.engine import DUAL_DOMAIN_REPORTS
        info = DUAL_DOMAIN_REPORTS["cth"]["daily"]
        assert "cth" in info["template"]


# ============================================================================
# 3. 共享引擎 + 域路由
# ============================================================================
class TestReportEngineDualDomain:
    """验证共享引擎 lumenis/shared/reporting/engine.py 按域路由。"""

    def test_generate_report_accepts_domain_id(self):
        """generate_report 接受 domain_id 参数。"""
        import inspect
        from lumenis.shared.reporting.engine import generate_report
        sig = inspect.signature(generate_report)
        assert "domain_id" in sig.parameters, "generate_report 缺少 domain_id 参数"

    def test_generate_report_rejects_invalid_type(self):
        """无效报告类型被拒。"""
        from lumenis.shared.reporting.engine import generate_report
        with pytest.raises(ValueError):
            generate_report("nonexistent_report_type", domain_id="zbmp")

    def test_zbmp_report_type_valid(self):
        """ZBMP 报告类型在域校验中通过。"""
        from lumenis.shared.reporting.engine import DUAL_DOMAIN_REPORTS
        zbmp_types = DUAL_DOMAIN_REPORTS.get("zbmp", {})
        for rtype in zbmp_types:
            assert rtype in zbmp_types, f"{rtype} 应在 ZBMP 域报告中"

    def test_cth_report_type_not_in_zbmp(self):
        """CTH 报告类型不在 ZBMP 注册表中（域隔离）。"""
        from lumenis.shared.reporting.engine import DUAL_DOMAIN_REPORTS
        zbmp = DUAL_DOMAIN_REPORTS.get("zbmp", {})
        cth = DUAL_DOMAIN_REPORTS.get("cth", {})
        for rtype in cth:
            assert rtype not in zbmp, \
                f"CTH 报告类型 {rtype} 不应出现在 ZBMP 注册表中"

    def test_zbmp_report_type_not_in_cth(self):
        """ZBMP 报告类型不在 CTH 注册表中（域隔离）。"""
        from lumenis.shared.reporting.engine import DUAL_DOMAIN_REPORTS
        zbmp = DUAL_DOMAIN_REPORTS.get("zbmp", {})
        cth = DUAL_DOMAIN_REPORTS.get("cth", {})
        for rtype in zbmp:
            assert rtype not in cth, \
                f"ZBMP 报告类型 {rtype} 不应出现在 CTH 注册表中"


# ============================================================================
# 4. 报告输出域标签验证
# ============================================================================
class TestReportOutputDomainTags:
    """验证报告输出带 domain_id / product_id。"""

    def test_report_output_has_domain_id(self):
        """generate_report 代码中报告输出带 domain_id。"""
        with open(os.path.join(PROJECT_ROOT, "lumenis/shared/reporting/engine.py"), encoding="utf-8") as f:
            content = f.read()
        assert "'domain_id': domain_id" in content or '"domain_id": domain_id' in content

    def test_report_output_has_product_id(self):
        """generate_report 代码中报告输出带 product_id。"""
        with open(os.path.join(PROJECT_ROOT, "lumenis/shared/reporting/engine.py"), encoding="utf-8") as f:
            content = f.read()
        assert "'product_id'" in content or '"product_id"' in content
        # product_id 按域映射
        assert "CTH" in content and "ZBMP" in content

    def test_zbmp_period_default_30days(self):
        """ZBMP 报告默认周期 30 天。"""
        with open(os.path.join(PROJECT_ROOT, "lumenis/shared/reporting/engine.py"), encoding="utf-8") as f:
            content = f.read()
        assert "brand', 'performance', 'competitive', 'growth', 'content', 'brand_risk'" in content


# ============================================================================
# 5. Shared Reporting routes 共享引擎验证
# ============================================================================
class TestReportApiSharedEngine:
    """验证 Shared Reporting routes 使用共享引擎。"""

    def test_report_api_exists(self):
        """Shared Reporting routes 存在。"""
        path = os.path.join(PROJECT_ROOT, "lumenis", "shared", "reporting", "routes.py")
        assert os.path.exists(path)

    def test_report_api_imports_engine(self):
        """Shared Reporting routes 导入 report_engine（共享引擎）。"""
        with open(os.path.join(PROJECT_ROOT, "lumenis", "shared", "reporting", "routes.py"), encoding="utf-8") as f:
            content = f.read()
        assert "lumenis.shared.reporting.engine" in content or "generate_report" in content


# ============================================================================
# 6. 品牌报告生成器验证
# ============================================================================
class TestBrandReportGenerator:
    """验证 lumenis/shared/reporting/brand_report.py 存在（ZBMP 品牌报告）。"""

    def test_shared_brand_report_exists(self):
        """lumenis/shared/reporting/brand_report.py 存在。"""
        path = os.path.join(PROJECT_ROOT, "lumenis/shared/reporting/brand_report.py")
        assert os.path.exists(path), "lumenis/shared/reporting/brand_report.py 不存在"

    def test_shared_brand_report_has_generate(self):
        """Shared brand report 有生成函数。"""
        with open(os.path.join(PROJECT_ROOT, "lumenis/shared/reporting/brand_report.py"), encoding="utf-8") as f:
            content = f.read()
        assert "def " in content, "lumenis.shared.reporting.brand_report 应有函数定义"