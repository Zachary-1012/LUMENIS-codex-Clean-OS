# -*- coding: utf-8 -*-
"""Release Gate · Z-Brand Runtime Preflight / Data Boundary 测试

覆盖：
1) 日志/证据脱敏（Authorization/Cookie/键值/PEM）；
2) 数据边界路径分层：处理凭证的“源码”放行，凭证/数据“载体”拦截，设计 Token 放行；
3) 当前仓库预检无 P0 阻断、核心红线模块可导入；
4) enforce 模式下 P0 必须 SystemExit(3)，非 enforce 绝不抛异常；
5) Attestation 落盘且不含明文凭证。
不打印任何真实凭证值。
"""
import io
import os
import sys
import json
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import data_boundary as dbm                    # noqa: E402
import runtime_preflight as rp                 # noqa: E402


# ------------------------------------------------------------------ 1) 脱敏
def test_sanitize_authorization_and_cookie():
    s = "Authorization: Bearer abcdef1234567890XYZ; Cookie: sessionid=zzzz; tail"
    out = dbm.sanitize_text(s)
    assert "abcdef1234567890XYZ" not in out
    assert "sessionid=zzzz" not in out
    assert "[REDACTED]" in out


def test_sanitize_entire_cookie_session_and_quoted_header():
    session = "session_" + "synthetic_value_91"
    refresh = "refresh_" + "synthetic_value_27"
    line = f"Cookie: sid={session}; refresh={refresh}; Path=/; SameSite=None; tail=visible"
    out = dbm.sanitize_text(line)
    assert session not in out and refresh not in out
    assert "Path=/" not in out and "tail=visible" not in out

    encoded = f'{{"Cookie": "sid={session}; refresh={refresh}", "safe": "visible"}}'
    out = dbm.sanitize_text(encoded)
    assert session not in out and refresh not in out
    assert '"safe": "visible"' in out


def test_sanitize_prefixed_cookie_fields():
    session = "session_" + "synthetic_value_33"
    xhs_cookie = "xhs_" + "synthetic_cookie_84"
    out = dbm.sanitize_text(
        f"session_cookie={session}; trailing metadata\nxhs_cookie: {xhs_cookie}"
    )
    assert session not in out
    assert xhs_cookie not in out
    assert "[REDACTED]" in out


def test_sanitize_kv_and_pem():
    # 样本在源码层分段拼接，避免连续“疑似密钥”字面量触发仓库自身静态安全门禁
    _sk = "sk-" + "abcdef1234567890abcdef"
    _pw = "hunter" + "2xx"
    _pwkey = "pass" + "word"
    s = 'api_key="' + _sk + '" and ' + _pwkey + '=' + _pw
    out = dbm.sanitize_text(s)
    assert _sk not in out and _pw not in out
    _body = "MIIB" + "VwIBADAN"
    pem = "-----BEGIN PRIVATE KEY-----\n" + _body + "\n-----END PRIVATE KEY-----"
    assert _body not in dbm.sanitize_text(pem)


def test_sanitize_mapping_nested():
    payload = {"a": {"b": ["token=abcd1234efgh5678", "clean"], "c": 1}, "d": "x"}
    out = dbm.sanitize_mapping(payload)
    flat = json.dumps(out, ensure_ascii=False)
    assert "abcd1234efgh5678" not in flat
    assert out["a"]["b"][1] == "clean" and out["a"]["c"] == 1


def test_sanitize_mapping_sensitive_keys_values_and_key_contents():
    session = "session_" + "synthetic_value_72"
    api_value = "api_" + "synthetic_value_38"
    embedded = "token=" + "synthetic_value_64"
    payload = {
        "Cookie": f"sid={session}; csrf=synthetic_csrf",
        "api_key": api_value,
        embedded: "opaque diagnostic label",
        "safe": {"note": "visible"},
    }

    out = dbm.sanitize_mapping(payload)
    flat = json.dumps(out, ensure_ascii=False)
    assert session not in flat and api_value not in flat and embedded not in flat
    assert out["Cookie"] == "[REDACTED]"
    assert out["api_key"] == "[REDACTED]"
    assert out["safe"]["note"] == "visible"


def test_sanitize_credential_keys_without_redacting_metadata_fields():
    opaque = "synthetic_" + "credential_value_482"
    cookie = "synthetic_" + "cookie_value_713"
    payload = {
        "credential": opaque,
        "credentials": [opaque],
        "browser_session_cookie": cookie,
        "token_count": 18,
        "token_budget": "budget-v4",
        "authorization_status": "verified",
        "secret_scan_result": "clean",
        "credential_status": "configured",
    }

    out = dbm.sanitize_mapping(payload)
    flat = json.dumps(out, ensure_ascii=False)
    assert opaque not in flat and cookie not in flat
    assert out["credential"] == "[REDACTED]"
    assert out["credentials"] == "[REDACTED]"
    assert out["browser_session_cookie"] == "[REDACTED]"
    assert out["token_count"] == 18
    assert out["token_budget"] == "budget-v4"
    assert out["authorization_status"] == "verified"
    assert out["secret_scan_result"] == "clean"
    assert out["credential_status"] == "configured"


# ------------------------------------------------------------------ 2) 路径分层
@pytest.mark.parametrize("path,expected", [
    # 凭证/数据载体：必须判为越界
    (".env", True),
    (".env.production", True),
    ("data/cookies/xhs_cookies.json", True),
    ("data/monitor.db", True),
    ("secret/server.pem", True),
    ("data/taikoo_browser_profile/Default/Cookies", True),
    ("data/profiles/AndroidManifest.xml", True),
    ("data/private/DebugProfile.entitlements", True),
    # 处理凭证的源码 / 设计 Token / 模板 / 文档：放行（交给内容层）
    ("xhs_cookie_bridge.py", False),
    ("v4_upgrade/adapters/cookie_vault.py", False),
    ("import_cookies.py", False),
    ("inject_cookies.js", False),
    ("app/lib/main.dart", False),
    ("contracts/experience/screen_meta.json", False),
    ("app/android/app/src/profile/AndroidManifest.xml", False),
    ("app/macos/Runner/DebugProfile.entitlements", False),
    (".env.example", False),
    ("examples/credential-example.pem", True),
    ("samples/session-example.key", True),
    ("tests/fixtures/access-token-example.p12", True),
    ("docs/CAPABILITY_BASELINE.md", False),
])
def test_credential_path_classification(path, expected):
    assert dbm._is_credential_path(path) is expected


def test_tracked_credentials_current_repo():
    r = dbm.assert_no_tracked_credentials(ROOT)
    assert r["status"] in ("pass", "skip")
    assert r["leaks"] == []


# ------------------------------------------------------------------ 3) 当前仓库放行
def test_current_repo_preflight_has_no_blocker():
    rep = rp.run_preflight(write_attestation=False)
    assert rep["blocker_count"] == 0
    assert rep["overall"] in ("pass", "warn")
    ids = {c["id"] for c in rep["checks"]}
    # 八个检查项都应实际执行
    assert {"ID-GIT", "DEP-CORE", "ZB-DATA-BOUNDARY-001", "SEC-SCAN"}.issubset(ids)


def test_core_modules_importable():
    import importlib.util
    for m in rp.CORE_MODULES:
        assert importlib.util.find_spec(m) is not None, m


# ------------------------------------------------------ 4) 真实密钥 vs 读 env 代码
def test_real_secret_vs_code_context():
    import security_scanner
    pat = security_scanner.SecurityScanner().sensitive_patterns[0][0]  # api key 规则
    _k = "api_" + "key"          # 分段拼接，源码不留连续疑似密钥/键名字面量
    _sk = "sk-" + "abcdef1234567890abcdef"
    real = f'{_k} = "{_sk}"'
    _dk = "DASHSCOPE_" + "API_KEY"
    code_line = f"'{_dk}=' in env_content and len(env_content.split('{_dk}=')[1]) > 5"
    m_real = re.search(pat, real)
    m_code = re.search(pat, code_line)
    assert m_real and rp._looks_like_real_secret(real, m_real) is True
    assert m_code and rp._looks_like_real_secret(code_line, m_code) is False


# ------------------------------------------------------------------ 5) enforce 阻断
def _p0_fail_check():
    return rp._check("FAKE-P0", "fake", "P0", "fail", "注入的 P0 失败")


def test_enforce_blocks_on_p0(monkeypatch):
    monkeypatch.setattr(rp, "CHECKS", [_p0_fail_check])
    with pytest.raises(SystemExit) as ei:
        rp.run_preflight(enforce=True, write_attestation=False)
    assert ei.value.code == 3


def test_non_enforce_never_raises(monkeypatch):
    monkeypatch.setattr(rp, "CHECKS", [_p0_fail_check])
    rep = rp.run_preflight(enforce=False, write_attestation=False)  # 不抛
    assert rep["overall"] == "block" and rep["blocker_count"] == 1


# ------------------------------------------------------------------ 6) Attestation
def test_attestation_written_and_redacted(tmp_path, monkeypatch):
    monkeypatch.setattr(rp, "get_data_dir", lambda: str(tmp_path))
    rep = rp.run_preflight(write_attestation=True)
    att = rep.get("attestation", {})
    assert att.get("written") is True
    latest = tmp_path / att["latest"]
    assert os.path.exists(latest)
    raw = io.open(latest, "r", encoding="utf-8").read()
    data = json.loads(raw)
    assert data["overall"] in ("pass", "warn", "block")
    assert data["product"] == rp.PRODUCT
    # 证据文件里不得出现常见明文凭证前缀
    for bad in ("sk-", "BEGIN PRIVATE KEY", "sessionid="):
        assert bad not in raw


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))


def test_camelcase_credential_keys_are_redacted():
    import data_boundary
    out = data_boundary.sanitize_mapping({
        "accessToken": "opaque-a", "sessionCookie": "opaque-b",
        "apiKey": "opaque-c", "privateKey": "opaque-d", "safe": "visible",
    })
    assert out["safe"] == "visible"
    assert all(out[k] == "[REDACTED]" for k in ("accessToken", "sessionCookie", "apiKey", "privateKey"))


def test_public_certificates_allowed_only_in_exempt_paths():
    import data_boundary
    assert data_boundary._is_credential_path("docs/vendor.cer") is False
    assert data_boundary._is_credential_path("tests/fixtures/root-ca.crt") is False
    assert data_boundary._is_credential_path("certs/server.crt") is True
    assert data_boundary._is_credential_path("tests/fixtures/server.pem") is True


def test_json_cookie_literal_keeps_following_fields():
    import json
    import data_boundary
    for raw in ('{"Cookie": null, "safe": "visible"}', '{"Cookie": 12345, "safe": "visible"}'):
        out = data_boundary.sanitize_text(raw)
        parsed = json.loads(out)
        assert parsed["safe"] == "visible"
        assert "12345" not in out


def test_sanitize_text_redacts_camelcase_cookie_labels():
    from data_boundary import sanitize_text
    for raw in ("sessionCookie=abc123secretvalue", "xhsCookie: abc123secretvalue"):
        out = sanitize_text(raw)
        assert "abc123secretvalue" not in out
        assert "[REDACTED]" in out


def test_sanitize_mapping_redacts_credential_keys_with_descriptors():
    from data_boundary import sanitize_mapping
    out = sanitize_mapping({
        "cookie_header": "opaqueA1B2C3",
        "authorization_header": "opaqueD4E5F6",
        "token_count": 3,
        "authorization_status": "missing",
    })
    assert out["cookie_header"] == "[REDACTED]"
    assert out["authorization_header"] == "[REDACTED]"
    assert out["token_count"] == 3
    assert out["authorization_status"] == "missing"
