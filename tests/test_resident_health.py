# -*- coding: utf-8 -*-
"""Resident Browser Health Monitor tests with no live profile or persistence access.

All CDP, cookie-name, recovery, cache, and check_all inputs are mocked. Tests
never probe an account or write the resident health file.
"""
import json, os, sys, unittest
from unittest.mock import MagicMock, patch
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
        """The supported default is the approved Hong Kong RedNote identity."""
        self.assertEqual(bridge.cdp_port_for(bridge.XHS_RETINAUT_NAME), 9223)
        self.assertEqual(bridge.DEFAULT_COLLECTION_ACCOUNT, bridge.XHS_RETINAUT_NAME)


class TestPortProbe(unittest.TestCase):
    def test_port_probe_uses_only_the_approved_hk_port(self):
        connection = MagicMock()
        with patch.object(rh.socket, "create_connection", return_value=connection) as connect:
            self.assertTrue(rh._check_port(9223, timeout=0.5))
        connect.assert_called_once_with(("127.0.0.1", 9223), timeout=0.5)

    def test_port_probe_failure_is_mocked(self):
        with patch.object(rh.socket, "create_connection", side_effect=OSError("mock unavailable")) as connect:
            self.assertFalse(rh._check_port(9223, timeout=0.3))
        connect.assert_called_once_with(("127.0.0.1", 9223), timeout=0.3)


class TestCDPProbe(unittest.TestCase):
    def test_cdp_http_returns_dict_or_none(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = b'{"Browser":"Mock Chromium"}'
        with patch.object(rh.ur, "urlopen", return_value=response) as urlopen:
            result = rh._check_cdp_http(9223, timeout=1.0)
        self.assertEqual(result, {"Browser": "Mock Chromium"})
        urlopen.assert_called_once_with("http://127.0.0.1:9223/json/version", timeout=1.0)

    def test_cdp_ws_returns_bool(self):
        ws = MagicMock()
        ws.recv.return_value = json.dumps({"id": 1, "result": {}})
        fake_websocket = MagicMock()
        fake_websocket.create_connection.return_value = ws
        endpoint = "ws://127.0.0.1:9223/devtools/browser/mock-only"
        with patch.object(rh, "_check_cdp_http", return_value={"webSocketDebuggerUrl": endpoint}), \
             patch.dict(sys.modules, {"websocket": fake_websocket}):
            self.assertTrue(rh._check_cdp_ws(9223, timeout=2.0))
        fake_websocket.create_connection.assert_called_once_with(endpoint, timeout=2.0)
        ws.close.assert_called_once()

    def test_cdp_http_dead_port(self):
        with patch.object(rh.ur, "urlopen", side_effect=OSError("mock unavailable")) as urlopen:
            self.assertIsNone(rh._check_cdp_http(9223, timeout=0.5))
        urlopen.assert_called_once_with("http://127.0.0.1:9223/json/version", timeout=0.5)


class TestCheckAccount(unittest.TestCase):
    def test_hk_account_health_uses_mocked_provider_only(self):
        with patch.object(rh, "_check_port", return_value=True) as port_probe, \
             patch.object(rh, "_check_cdp_http", return_value={"Browser": "Mock Chromium"}) as http_probe, \
             patch.object(rh, "_check_cdp_ws", return_value=True) as ws_probe, \
             patch.object(rh, "_cdp_get_cookies", return_value=[
                 {"name": "web_session"}, {"name": "id_token"},
             ]) as cookies_probe, \
             patch.object(rh, "_cdp_page_urls", return_value=["https://www.rednote.com/explore"]) as pages_probe:
            result = rh.check_account(bridge.XHS_RETINAUT_NAME)

        required = {"account", "cdp_port", "home_url", "checked_at", "port_alive",
                    "cdp_http_ok", "cdp_ws_ok", "login_state", "has_web_session",
                    "has_id_token", "cookie_count", "page_urls", "status", "detail"}
        self.assertTrue(required.issubset(result.keys()), f"missing keys: {required - set(result.keys())}")
        self.assertEqual(result["account"], bridge.XHS_RETINAUT_NAME)
        self.assertEqual(result["cdp_port"], 9223)
        self.assertEqual(result["status"], "HEALTHY")
        port_probe.assert_called_once_with(9223)
        http_probe.assert_called_once_with(9223)
        ws_probe.assert_called_once_with(9223)
        cookies_probe.assert_called_once_with(9223)
        pages_probe.assert_called_once_with(9223)

    def test_no_cookie_values_leaked(self):
        """Only mocked cookie names are present; values are not requested or returned."""
        with patch.object(rh, "_check_port", return_value=True), \
             patch.object(rh, "_check_cdp_http", return_value={"Browser": "Mock Chromium"}), \
             patch.object(rh, "_check_cdp_ws", return_value=True), \
             patch.object(rh, "_cdp_get_cookies", return_value=[
                 {"name": "web_session"}, {"name": "id_token"},
             ]), \
             patch.object(rh, "_cdp_page_urls", return_value=["https://www.rednote.com/explore"]):
            result = rh.check_account(bridge.XHS_RETINAUT_NAME)
        raw = json.dumps(result, ensure_ascii=False)
        self.assertNotIn("cookie_value", raw)
        self.assertNotIn("storage_state", raw)


class TestCheckAll(unittest.TestCase):
    def test_summary_structure(self):
        accounts = [bridge.DEFAULT_COLLECTION_ACCOUNT]
        mocked_results = {
            accounts[0]: {"status": "HEALTHY"},
        }
        with patch.object(rh, "check_account_with_evidence", side_effect=mocked_results.__getitem__) as check, \
             patch.object(rh, "_persist") as persist, \
             patch.object(rh, "_check_port", side_effect=AssertionError("live probe blocked")):
            result = rh.check_all()
        self.assertIn("checked_at", result)
        self.assertIn("total", result)
        self.assertIn("healthy", result)
        self.assertIn("needs_login", result)
        self.assertIn("degraded", result)
        self.assertIn("down", result)
        self.assertIn("accounts", result)
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["healthy"] + result["needs_login"] + result["degraded"] + result["down"], 1)
        self.assertEqual(set(result["accounts"]), set(accounts))
        self.assertEqual(check.call_args_list, [unittest.mock.call(account) for account in accounts])
        persist.assert_called_once_with(result)

    def test_persist_summary_is_requested_without_writing_file(self):
        accounts = [bridge.DEFAULT_COLLECTION_ACCOUNT]
        mocked_results = {account: {"status": "DOWN"} for account in accounts}
        with patch.object(rh, "check_account_with_evidence", side_effect=mocked_results.__getitem__), \
             patch.object(rh, "_persist") as persist, \
             patch.object(rh, "_check_port", side_effect=AssertionError("live probe blocked")):
            result = rh.check_all()
        persist.assert_called_once_with(result)
        self.assertEqual(result["down"], 1)


class TestRecover(unittest.TestCase):
    def test_recover_healthy_returns_noop(self):
        """A mocked healthy HK identity returns noop without browser or disk access."""
        with patch.object(rh, "_load_state", return_value={}), \
             patch.object(rh, "check_account", return_value={"status": "HEALTHY"}) as check_account:
            result = rh.recover_account(bridge.XHS_RETINAUT_NAME)
        self.assertEqual(result["action"], "noop")
        self.assertEqual(result["reason"], "already HEALTHY")
        check_account.assert_called_once_with(bridge.XHS_RETINAUT_NAME)

    def test_unknown_account_is_policy_blocked_before_any_probe(self):
        """Unsupported identities are blocked before bridge or network resolution."""
        blocked = bridge.XHS_CN_PRIMARY_NAME
        with patch.object(rh.bridge, "cdp_port_for") as port_for, \
             patch.object(rh.bridge, "home_url_for") as home_for, \
             patch.object(rh, "_check_port") as port_probe, \
             patch.object(rh, "_check_cdp_http") as http_probe, \
             patch.object(rh, "_check_cdp_ws") as ws_probe, \
             patch.object(rh, "_cdp_get_cookies") as cookies_probe, \
             patch.object(rh, "_cdp_page_urls") as pages_probe:
            result = rh.check_account(blocked)
        self.assertEqual(result["status"], "POLICY_BLOCKED")
        port_for.assert_not_called()
        home_for.assert_not_called()
        port_probe.assert_not_called()
        http_probe.assert_not_called()
        ws_probe.assert_not_called()
        cookies_probe.assert_not_called()
        pages_probe.assert_not_called()

    def test_blocked_account_cannot_write_evidence_or_state(self):
        blocked = bridge.XHS_CN_PRIMARY_NAME
        with patch.object(rh, "check_account") as check, \
             patch.object(rh, "_load_state") as load_state, \
             patch.object(rh, "_persist_state") as persist_state:
            result = rh.check_account_with_evidence(blocked)
        self.assertEqual(result["status"], "POLICY_BLOCKED")
        check.assert_not_called()
        load_state.assert_not_called()
        persist_state.assert_not_called()

    def test_recovery_rejects_blocked_account_before_side_effects(self):
        blocked = bridge.XHS_CN_PRIMARY_NAME
        with patch.object(rh, "_load_state") as load_state, \
             patch.object(rh, "check_account") as check, \
             patch.object(rh.subprocess, "run") as run, \
             patch.object(rh.time, "sleep") as sleep, \
             patch.object(rh, "_persist_state") as persist_state:
            result = rh.recover_account(blocked)
        self.assertEqual(result["status"], "POLICY_BLOCKED")
        load_state.assert_not_called()
        check.assert_not_called()
        run.assert_not_called()
        sleep.assert_not_called()
        persist_state.assert_not_called()

    def test_recover_all_contains_only_approved_account(self):
        with patch.object(rh, "recover_account", return_value={"status": "DOWN"}) as recover:
            result = rh.recover_all()
        self.assertEqual(set(result), {bridge.DEFAULT_COLLECTION_ACCOUNT})
        recover.assert_called_once_with(bridge.DEFAULT_COLLECTION_ACCOUNT, force=False)


class TestStatusCache(unittest.TestCase):
    def test_status_use_cache(self):
        summary = {"checked_at": "mock-only", "accounts": {}}
        with patch.object(rh, "_load_state", return_value={"last_check": summary}):
            cached = rh.status(use_cache=True)
        self.assertIsInstance(cached, dict)
        self.assertEqual(cached, summary)



class TestResidentHealthDisconnectContract(unittest.TestCase):
    def test_cookie_probe_disconnect_is_degraded_not_needs_login(self):
        websocket_module = MagicMock()
        with patch.dict(sys.modules, {"websocket": websocket_module}), \
             patch.object(rh, "_check_port", return_value=True), \
             patch.object(rh, "_check_cdp_http", return_value={"Browser": "Mock Chromium"}), \
             patch.object(rh, "_check_cdp_ws", return_value=True), \
             patch.object(rh.ur, "urlopen", side_effect=OSError("mock CDP disconnect")), \
             patch.object(rh, "_cdp_page_urls") as page_probe:
            result = rh.check_account(bridge.XHS_RETINAUT_NAME)

        self.assertEqual(result["status"], "CDP_DEGRADED")
        self.assertEqual(result["login_state"], "unknown")
        page_probe.assert_not_called()

    def test_page_probe_disconnect_is_not_reported_healthy(self):
        cookies = [{"name": "web_session"}, {"name": "id_token"}]
        with patch.object(rh, "_check_port", return_value=True), \
             patch.object(rh, "_check_cdp_http", return_value={"Browser": "Mock Chromium"}), \
             patch.object(rh, "_check_cdp_ws", return_value=True), \
             patch.object(rh, "_cdp_get_cookies", return_value=cookies), \
             patch.object(rh.ur, "urlopen", side_effect=OSError("mock CDP disconnect")):
            result = rh.check_account(bridge.XHS_RETINAUT_NAME)

        self.assertEqual(result["status"], "CDP_DEGRADED")
        self.assertEqual(result["login_state"], "unknown")

    def test_page_probe_rejects_missing_or_malformed_page(self):
        for targets in ([], [{"type": "page", "url": 42}]):
            with self.subTest(targets=targets):
                response = MagicMock()
                response.__enter__.return_value.read.return_value = json.dumps(
                    targets
                ).encode("utf-8")
                with patch.object(rh.ur, "urlopen", return_value=response):
                    self.assertIsNone(rh._cdp_page_urls(9223))

    def test_successful_empty_cookie_probe_still_means_needs_login(self):
        with patch.object(rh, "_check_port", return_value=True), \
             patch.object(rh, "_check_cdp_http", return_value={"Browser": "Mock Chromium"}), \
             patch.object(rh, "_check_cdp_ws", return_value=True), \
             patch.object(rh, "_cdp_get_cookies", return_value=[]), \
             patch.object(rh, "_cdp_page_urls", return_value=[]):
            result = rh.check_account(bridge.XHS_RETINAUT_NAME)

        self.assertEqual(result["status"], "NEEDS_LOGIN")

    def test_cdp_cookie_probe_preserves_successful_empty_list(self):
        ws = MagicMock()
        ws.recv.side_effect = [
            json.dumps({"id": 1, "result": {}}),
            json.dumps({"id": 2, "result": {"cookies": []}}),
        ]
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps([
            {"type": "page", "webSocketDebuggerUrl": "ws://127.0.0.1/mock"}
        ]).encode("utf-8")
        websocket_module = MagicMock()
        websocket_module.create_connection.return_value = ws

        with patch.dict(sys.modules, {"websocket": websocket_module}), \
             patch.object(rh.ur, "urlopen", return_value=response) as urlopen:
            cookies = rh._cdp_get_cookies(9223)

        self.assertEqual(cookies, [])
        urlopen.assert_called_once_with("http://127.0.0.1:9223/json/list", timeout=1.0)
        websocket_module.create_connection.assert_called_once_with(
            "ws://127.0.0.1/mock", timeout=3.0
        )
        ws.close.assert_called_once()

if __name__ == "__main__":
    unittest.main(verbosity=2)
