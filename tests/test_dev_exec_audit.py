# -*- coding: utf-8 -*-
"""dev_exec_core 代码执行审计日志测试（学习 memkeeper-warden：每次 allow/deny 可审计）。

验证：
1. 放行执行成功 -> 写 allow/success 审计；
2. guard 拒绝 -> 写 deny/blocked 审计且不执行；
3. 空代码 / 不支持类型 -> deny/bad_request；
4. 审计只存代码指纹（长度+SHA256前12位），绝不落代码全文；
5. 审计写入失败是旁路，绝不阻塞主执行流程。
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dev_exec_core


@pytest.fixture
def audit_file(tmp_path, monkeypatch):
    p = tmp_path / "dev_exec_audit.jsonl"
    monkeypatch.setattr(dev_exec_core, "_AUDIT_PATH", p)
    return p


def _read_records(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _deny_guard(code):
    return {"ok": False, "code": "DEV_EXEC_DISABLED", "error": "disabled"}, 403


def test_allow_success_writes_audit(audit_file):
    resp, status = dev_exec_core.execute_dev_code_safe(
        "result = 1 + 1", "python", guard_func=None, endpoint="/api/config/run-code")
    assert status == 200 and resp["ok"] is True
    recs = _read_records(audit_file)
    assert len(recs) == 1
    rec = recs[0]
    assert rec["decision"] == "allow" and rec["outcome"] == "success"
    assert rec["endpoint"] == "/api/config/run-code"
    assert rec["http_status"] == 200


def test_guard_deny_writes_audit_and_skips_exec(audit_file):
    resp, status = dev_exec_core.execute_dev_code_safe(
        "result=1", "python", guard_func=_deny_guard)
    assert status == 403
    recs = _read_records(audit_file)
    assert len(recs) == 1
    rec = recs[0]
    assert rec["decision"] == "deny" and rec["outcome"] == "blocked"
    assert rec["reason"] == "DEV_EXEC_DISABLED"


def test_empty_code_deny_audit(audit_file):
    _, status = dev_exec_core.execute_dev_code_safe("   ", "python", guard_func=None)
    assert status == 400
    rec = _read_records(audit_file)[0]
    assert rec["decision"] == "deny" and rec["outcome"] == "bad_request"
    assert rec["reason"] == "empty_code"


def test_unsupported_type_audit(audit_file):
    _, status = dev_exec_core.execute_dev_code_safe("1+1", "ruby", guard_func=None)
    assert status == 400
    rec = _read_records(audit_file)[0]
    assert "unsupported_type" in rec["reason"]


def test_audit_stores_fingerprint_never_fulltext(audit_file):
    secret_like = "result = 'TOKEN_ABCDEFG_SECRET_VALUE_1234567890'"
    dev_exec_core.execute_dev_code_safe(secret_like, "python", guard_func=None)
    raw = audit_file.read_text(encoding="utf-8")
    rec = _read_records(audit_file)[0]
    assert rec["code_len"] == len(secret_like)
    assert len(rec["code_fp"]) == 12            # SHA256 前 12 位
    assert "TOKEN_ABCDEFG_SECRET_VALUE" not in raw  # 全文绝不落审计文件


def test_audit_failure_never_blocks_main_flow(monkeypatch, tmp_path):
    # 把审计路径指向一个不可写位置（其“父目录”是文件，mkdir 必失败）
    blocker = tmp_path / "afile"
    blocker.write_text("x", encoding="utf-8")
    monkeypatch.setattr(dev_exec_core, "_AUDIT_PATH", blocker / "sub" / "audit.jsonl")
    # 审计写失败，但主执行照常成功
    resp, status = dev_exec_core.execute_dev_code_safe("result = 2*3", "python", guard_func=None)
    assert status == 200 and resp["ok"] is True
    assert resp["result"] == "6"
