# -*- coding: utf-8 -*-
"""
OSAI × ZBC Browser Runtime 契约符合性测试（P0-BR）
验证 ZBC browser_runtime 实现是否符合 CTR-BROWSER-RUNTIME-P0-01 契约。
通过 sys.path 插入 ZBC 路径，import 实际模块验证接口。
ZBC 路径：D:\\Taikoo-monitor-new（可通过环境变量 ZBC_REPO_PATH 覆盖）
"""
import os
import sys
import pytest

ZBC_PATH = os.environ.get("ZBC_REPO_PATH", r"D:\Taikoo-monitor-new")


@pytest.fixture(scope="session")
def zbc_imports():
    """插入 ZBC 路径并 import browser_runtime 模块。"""
    if not os.path.isdir(ZBC_PATH):
        pytest.skip(f"ZBC repo not found at {ZBC_PATH}")
    if ZBC_PATH not in sys.path:
        sys.path.insert(0, ZBC_PATH)
    from browser_runtime import contract, policy, router
    from browser_runtime.adapters import playwright_adapter
    return {
        "contract": contract,
        "policy": policy,
        "router": router,
        "playwright_adapter": playwright_adapter,
    }


class TestBrowserContractInterface:
    """BrowserContract 接口必须符合契约定义。"""

    def test_contract_module_exists(self, zbc_imports):
        assert zbc_imports["contract"] is not None

    def test_browser_contract_class_exists(self, zbc_imports):
        assert hasattr(zbc_imports["contract"], "BrowserContract")

    def test_browser_contract_has_core_methods(self, zbc_imports):
        bc = zbc_imports["contract"].BrowserContract
        # 契约要求的核心方法（ZBC 实际接口）
        required = ["navigate", "snapshot", "click", "type_text", "evaluate",
                    "health", "close", "get_text", "screenshot", "wait_for",
                    "classify_failure", "state_sequence"]
        for method in required:
            assert hasattr(bc, method), f"BrowserContract 缺少方法: {method}"

    def test_browser_state_enum_exists(self, zbc_imports):
        assert hasattr(zbc_imports["contract"], "BrowserState")

    def test_browser_state_has_core_states(self, zbc_imports):
        bs = zbc_imports["contract"].BrowserState
        # 契约要求的核心状态
        required = ["INIT", "BROWSER_READY", "PAGE_READY", "SESSION_VALID",
                    "TASK_READY", "ACTION", "VERIFY", "SUCCESS", "VERIFY_FAILED",
                    "CLASSIFY_FAILURE"]
        for state in required:
            assert hasattr(bs, state), f"BrowserState 缺少状态: {state}"

    def test_beep_executor_exists(self, zbc_imports):
        assert hasattr(zbc_imports["contract"], "BEEPExecutor")

    def test_beep_executor_has_run(self, zbc_imports):
        be = zbc_imports["contract"].BEEPExecutor
        assert hasattr(be, "run"), "BEEPExecutor 必须有 run 方法"

    def test_max_retry_is_3_module_level(self, zbc_imports):
        """MAX_RETRY 是模块级常量（契约要求有限重试=3）。"""
        contract = zbc_imports["contract"]
        assert hasattr(contract, "MAX_RETRY"), "contract 模块必须定义 MAX_RETRY"
        assert contract.MAX_RETRY == 3, f"MAX_RETRY 必须为 3（契约要求），当前为 {contract.MAX_RETRY}"

    def test_failure_class_exists(self, zbc_imports):
        assert hasattr(zbc_imports["contract"], "FailureClass")

    def test_failure_class_has_core_types(self, zbc_imports):
        fc = zbc_imports["contract"].FailureClass
        # 契约要求的失败分类（全大写枚举）
        required = ["TRANSIENT", "SESSION", "PAGE_CHANGED", "PERMISSION",
                    "PLATFORM_RISK", "UNKNOWN"]
        for ft in required:
            assert hasattr(fc, ft), f"FailureClass 缺少类型: {ft}"

    def test_classify_failure_is_contract_method(self, zbc_imports):
        """classify_failure 是 BrowserContract 实例方法。"""
        bc = zbc_imports["contract"].BrowserContract
        assert hasattr(bc, "classify_failure"), "BrowserContract 必须有 classify_failure 方法"


class TestBrowserPolicyEngine:
    """BrowserPolicyEngine 必须符合契约（策略门）。"""

    def test_policy_engine_exists(self, zbc_imports):
        assert hasattr(zbc_imports["policy"], "BrowserPolicyEngine")

    def test_policy_decision_has_levels(self, zbc_imports):
        pd = zbc_imports["policy"].PolicyDecision
        # 契约要求的决策级别
        required = ["ALLOW", "CAUTION", "NEED_CONFIRM", "SAFE_STOP"]
        for level in required:
            assert hasattr(pd, level), f"PolicyDecision 缺少级别: {level}"

    def test_default_allowed_domains_exists(self, zbc_imports):
        assert hasattr(zbc_imports["policy"], "DEFAULT_ALLOWED_DOMAINS")
        assert len(zbc_imports["policy"].DEFAULT_ALLOWED_DOMAINS) >= 1

    def test_global_policy_engine_instance(self, zbc_imports):
        assert hasattr(zbc_imports["policy"], "browser_policy_engine")


class TestBrowserRouter:
    """BrowserRouter 必须符合契约（Provider 注册/选择/降级/策略门）。"""

    def test_router_class_exists(self, zbc_imports):
        assert hasattr(zbc_imports["router"], "BrowserRouter")

    def test_router_has_policy_gate(self, zbc_imports):
        assert hasattr(zbc_imports["router"].BrowserRouter, "policy_gate")


class TestPlaywrightAdapter:
    """PlaywrightAdapter 必须实现 BrowserContract 接口。"""

    def test_playwright_adapter_class_exists(self, zbc_imports):
        assert hasattr(zbc_imports["playwright_adapter"], "PlaywrightAdapter")

    def test_playwright_adapter_name(self, zbc_imports):
        pa = zbc_imports["playwright_adapter"].PlaywrightAdapter
        assert hasattr(pa, "NAME")
        assert pa.NAME == "playwright", f"PlaywrightAdapter.NAME 应为 'playwright'，当前为 {pa.NAME}"

    def test_playwright_adapter_implements_contract_methods(self, zbc_imports):
        pa = zbc_imports["playwright_adapter"].PlaywrightAdapter
        bc = zbc_imports["contract"].BrowserContract
        # 验证 PlaywrightAdapter 实现了 BrowserContract 的所有公共方法
        contract_methods = [m for m in dir(bc) if not m.startswith("_") and callable(getattr(bc, m, None))]
        for method in contract_methods:
            assert hasattr(pa, method), f"PlaywrightAdapter 缺少 BrowserContract 方法: {method}"

    def test_playwright_adapter_supports_cdp_url(self, zbc_imports):
        """P0-BR 接入：PlaywrightAdapter 必须支持 cdp_url 参数（connect_over_cdp）。"""
        import inspect
        pa = zbc_imports["playwright_adapter"].PlaywrightAdapter
        sig = inspect.signature(pa.__init__)
        assert "cdp_url" in sig.parameters, "PlaywrightAdapter.__init__ 必须支持 cdp_url 参数"

    def test_playwright_adapter_supports_user_data_dir(self, zbc_imports):
        """P0-BR-06：PlaywrightAdapter 必须支持 user_data_dir 参数（profile 隔离）。"""
        import inspect
        pa = zbc_imports["playwright_adapter"].PlaywrightAdapter
        sig = inspect.signature(pa.__init__)
        assert "user_data_dir" in sig.parameters, "PlaywrightAdapter.__init__ 必须支持 user_data_dir 参数"


class TestEvidenceContract:
    """Evidence 必须符合契约（BEEPTrace.to_evidence + evidence_exporter）。"""

    def test_beep_trace_has_to_evidence(self, zbc_imports):
        assert hasattr(zbc_imports["contract"], "BEEPTrace")
        assert hasattr(zbc_imports["contract"].BEEPTrace, "to_evidence")

    def test_evidence_exporter_module_exists(self, zbc_imports):
        try:
            from platform_adapters import evidence_exporter
            assert evidence_exporter is not None
        except ImportError:
            pytest.skip("evidence_exporter not found in platform_adapters")
