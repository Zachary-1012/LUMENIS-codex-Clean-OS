# -*- coding: utf-8 -*-
"""Resident Browser Health Monitor 单元测试。

覆盖：模块导入、端口探测、CDP HTTP/WS 探测、登录态检测、check_account/check_all 结构、
recover_account 对 HEALTHY 的 noop 行为、状态持久化。
不实际重启浏览器（recover 对 HEALTHY 直接 noop）。
"""
import json, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import resident_health as rh
import xhs_cookie_bridge as bridge


class TestResidentHealthImports(unittest.TestCase):
    def test_module_constants(self):
        self.assertTrue(hasattr(rh, "HEALTH_FILE"))
        self.assertTrue(hasattr(rh, "MAX_AUTO_RECOVERIES"))
        self.assertEqual(rh.MAX_AUTO_RECOVERIES, 3)
        self.assertTrue(os.path.isfile(rh.RESIDENT_LAUNCHER))

    def test_bridge_contract_alignment(self):
        """健康监控的身份列表必须与 bridge 单一事实源一致。"""
        self.assertEqual(bridge.cdp_port_for(bridge.XHS_CN_PRIMARY_NAME), 9222)
        self.assertEqual(bridge.cdp_port_for(bridge.XHS_RETINAUT_NAME), 9223)
        self.assertEqual(len(bridge.ALLOWED_USER_IDS), 2)


class TestPortProbe(unittest.TestCase):
    def test_port_alive_for_resident_9222(self):
        # 9222 驻场应在线（如果测试环境无浏览器则跳过断言，只验证不抛异常）
        result = rh._check_port(9222, timeout=0.5)
        self.assertIsInstance(result, bool)

    def test_port_dead_for_unused_port(self):
        # 找一个几乎不可能被占用的高端口
        self.assertFalse(rh._check_port(19999, timeout=0.3))


class TestCDPProbe(unittest.TestCase):
    def test_cdp_http_returns_dict_or_none(self):
        result = rh._check_cdp_http(9222, timeout=1.0)
        self.assertTrue(result is None or isinstance(result, dict))

    def test_cdp_ws_returns_bool(self):
        result = rh._check_cdp_ws(9222, timeout=2.0)
        self.assertIsInstance(result, bool)

    def test_cdp_http_dead_port(self):
        self.assertIsNone(rh._check_cdp_http(19999, timeout=0.5))


class TestCheckAccount(unittest.TestCase):
    def test_structure_complete(self):
        result = rh.check_account(bridge.XHS_CN_PRIMARY_NAME)
        required = {"account", "cdp_port", "home_url", "checked_at", "port_alive",
                    "cdp_http_ok", "cdp_ws_ok", "login_state", "has_web_session",
                    "has_id_token", "cookie_count", "page_urls", "status", "detail"}
        self.assertTrue(required.issubset(result.keys()), f"missing keys: {required - set(result.keys())}")
        self.assertEqual(result["account"], bridge.XHS_CN_PRIMARY_NAME)
        self.assertEqual(result["cdp_port"], 9222)
        self.assertIn(result["status"], ("HEALTHY", "NEEDS_LOGIN", "CDP_DEGRADED", "DOWN"))

    def test_no_cookie_values_leaked(self):
        """结果中绝不能包含 cookie 值（只含名称存在性和数量）。"""
        result = rh.check_account(bridge.XHS_CN_PRIMARY_NAME)
        raw = json.dumps(result, ensure_ascii=False)
        self.assertNotRegex(raw, r"040069[a-f0-9]{20,}")
        self.assertNotRegex(raw, r"VjEA[A-Za-z0-9+/]{20,}")


class TestCheckAll(unittest.TestCase):
    def test_summary_structure(self):
        result = rh.check_all()
        self.assertIn("checked_at", result)
        self.assertIn("total", result)
        self.assertIn("healthy", result)
        self.assertIn("needs_login", result)
        self.assertIn("degraded", result)
        self.assertIn("down", result)
        self.assertIn("accounts", result)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["healthy"] + result["needs_login"] + result["degraded"] + result["down"], 2)
        self.assertIn(bridge.XHS_CN_PRIMARY_NAME, result["accounts"])
        self.assertIn(bridge.XHS_RETINAUT_NAME, result["accounts"])

    def test_persist_file_created(self):
        rh.check_all()
        self.assertTrue(os.path.isfile(rh.HEALTH_FILE))
        with open(rh.HEALTH_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        self.assertIn("last_check", state)


class TestRecover(unittest.TestCase):
    def test_recover_healthy_returns_noop(self):
        """对 HEALTHY 身份，recover 应直接 noop，不实际重启浏览器。"""
        current = rh.check_account(bridge.XHS_CN_PRIMARY_NAME)
        if current["status"] != "HEALTHY":
            self.skipTest("primary not HEALTHY in this env, skip noop test")
        result = rh.recover_account(bridge.XHS_CN_PRIMARY_NAME)
        self.assertEqual(result["action"], "noop")
        self.assertEqual(result["reason"], "already HEALTHY")

    def test_unknown_account_follows_current_default_identity(self):
        """未知身份按当前生产默认 Retinaut/intl 身份回退，不得静默切回大陆主号。"""
        result = rh.check_account("XHS_UNKNOWN")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["cdp_port"], bridge.DEFAULT_CDP_PORT)
        self.assertEqual(result["cdp_port"], 9223)


class TestStatusCache(unittest.TestCase):
    def test_status_use_cache(self):
        rh.check_all()  # 先写入缓存
        cached = rh.status(use_cache=True)
        self.assertIsInstance(cached, dict)
        self.assertIn("accounts", cached)


if __name__ == "__main__":
    unittest.main(verbosity=2)
