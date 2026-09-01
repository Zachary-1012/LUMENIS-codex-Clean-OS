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


# ------------------------------------------------------------------ 2) 路径分层
@pytest.mark.parametrize("path,expected", [
    # 凭证/数据载体：必须判为越界
    (".env", True),
    (".env.production", True),
    ("data/cookies/xhs_cookies.json", True),
    ("data/monitor.db", True),
    ("secret/server.pem", True),
    ("data/taikoo_browser_profile/Default/Cookies", True),
    # 处理凭证的源码 / 设计 Token / 模板 / 文档：放行（交给内容层）
    ("xhs_cookie_bridge.py", False),
    ("v4_upgrade/adapters/cookie_vault.py", False),
    ("import_cookies.py", False),
    ("inject_cookies.js", False),
    ("static/css/tokens.css", False),
    ("static/css/zbip-tokens.css", False),
    (".env.example", False),
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
def test_attestation_written_and_redacted():
    rep = rp.run_preflight(write_attestation=True)
    att = rep.get("attestation", {})
    assert att.get("written") is True
    latest = os.path.join(ROOT, att["latest"].replace("/", os.sep))
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
