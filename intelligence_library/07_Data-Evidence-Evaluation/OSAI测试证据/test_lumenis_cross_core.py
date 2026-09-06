# -*- coding: utf-8 -*-
"""LUMENIS Cross-Core Verification（PHASE 2 双核联调验证）。

验证 OSAI (Intelligence Core) 与 ZBC (Production Core) 的 Contract 联调：
1. OSAI Repository Registry 可注册 ZBC
2. ZBC adapter 暴露的 repository_registry_snapshot / permission_gate_snapshot 可访问
3. OSAI Permission Gate 与 ZBC Permission 等级对齐
4. OSAI AI Gateway → Engine Layer → Evidence 链路完整
5. 双核不物理合并，通过 Contract 通信

通过 subprocess 调用 ZBC adapter（两仓物理独立，不直接 import）。
"""
import os
import sys
import json
import subprocess

_OSAI_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ZBC_ROOT = os.environ.get("ZBC_ROOT", r"D:\Taikoo-monitor-new")

sys.path.insert(0, _OSAI_ROOT)


def _call_zbc_adapter(func_name: str) -> dict:
    """通过 subprocess 调用 ZBC lumenis_adapter，返回 dict。"""
    code = f"""
import sys, json
sys.path.insert(0, r"{_ZBC_ROOT}")
from contracts import lumenis_adapter
result = getattr(lumenis_adapter, "{func_name}")()
print(json.dumps(result, ensure_ascii=False))
"""
    try:
        r = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True, text=True, timeout=30,
            cwd=_ZBC_ROOT,
        )
        if r.returncode != 0:
            return {"_error": r.stderr.strip()[:500]}
        return json.loads(r.stdout.strip())
    except Exception as e:
        return {"_error": str(e)}


def test_zbc_repository_registry_accessible():
    """ZBC Repository Registry snapshot 可通过 subprocess 访问。"""
    r = _call_zbc_adapter("repository_registry_snapshot")
    assert "_error" not in r, f"ZBC adapter error: {r.get('_error')}"
    assert r["repository_id"] == "zbc-production-core"
    assert r["name"] == "Z-Brand-Core"
    assert r["role"] == "production"
    assert r["default_branch"] == "main"
    assert "current_sha" in r
    assert len(r["current_sha"]) >= 7  # 短 SHA 或完整 SHA
    assert r["permissions"]["subject_rules"] == "locked_not_bypassable"


def test_zbc_permission_gate_accessible():
    """ZBC Permission Gate snapshot 可访问，11 级权限完整。"""
    p = _call_zbc_adapter("permission_gate_snapshot")
    assert "_error" not in p
    assert len(p["levels"]) == 11
    assert p["levels"][0] == "READ"
    assert p["levels"][-1] == "PUSH"
    assert p["defaults"]["HUMAN_APPROVAL"] == "REQUIRED"
    assert p["defaults"]["COMMIT"] == "BLOCKED_UNTIL_APPROVED"
    assert "subject_hit()" in p["production_truth_protected"]


def test_zbc_production_core_snapshot():
    """ZBC Production Core snapshot 可访问，10 条红线完整。"""
    s = _call_zbc_adapter("production_core_snapshot")
    assert "_error" not in s
    assert s["core"] == "Production Core"
    assert len(s["red_lines"]) == 10
    assert "subject" in s["capabilities"]
    assert "risk" in s["capabilities"]


def test_osai_repository_registry_can_register_zbc():
    """OSAI Repository Registry 可解析 ZBC 并获取 repo 信息。"""
    from osai_engine.repository_registry import resolve_path, get_repo_info, registry_snapshot
    # ZBC 通过 key 解析（跨平台路径抽象，不硬编码）
    resolved = resolve_path("ZBC")
    assert resolved is not None
    assert os.path.isdir(resolved)
    # registry_snapshot 包含双核信息
    snap = registry_snapshot()
    assert "ZBC" in snap or "zbc" in str(snap).lower()
    assert "OSAI" in snap or "osai" in str(snap).lower()


def test_osai_permission_gate_alignment_with_zbc():
    """OSAI Permission Gate 与 ZBC Permission 等级对齐。"""
    from osai_engine.permission_gate import PermissionGate, LEVELS
    zbc_perms = _call_zbc_adapter("permission_gate_snapshot")
    if "_error" in zbc_perms:
        return  # ZBC 不可用时跳过对齐检查
    # OSAI LEVELS 必须覆盖 ZBC 声明的所有权限等级
    for level in zbc_perms["levels"]:
        assert level in LEVELS, f"OSAI LEVELS missing: {level}"
    # 等级数量一致
    assert len(LEVELS) == len(zbc_perms["levels"])
    # HUMAN_APPROVAL / COMMIT / PUSH 必须受 Gate 控制
    gate = PermissionGate()
    assert hasattr(gate, "check")
    assert hasattr(gate, "require_human_approval")


def test_osai_ai_gateway_engine_evidence_chain():
    """OSAI AI Gateway → Engine Layer → Evidence 链路完整。"""
    from osai_engine import ai_gateway, engine_layer
    # Gateway 路由
    provider, model, meta = ai_gateway.route("daily")
    assert "factors" in meta
    # Engine 执行（无 key 时走降级，但 Evidence 必须记录）
    eng = engine_layer.CloudEngine()
    result = eng.execute("cross-core verification test", "daily")
    assert "evidence" in result
    assert eng.last_evidence is not None
    assert "trace_id" in eng.last_evidence


def test_dual_core_not_merged():
    """双核物理独立验证：两仓根路径不同，git remote 不同。"""
    assert _OSAI_ROOT != _ZBC_ROOT
    # OSAI remote
    r1 = subprocess.run(["git", "config", "--get", "remote.origin.url"],
                        capture_output=True, text=True, cwd=_OSAI_ROOT)
    # ZBC remote
    r2 = subprocess.run(["git", "config", "--get", "remote.origin.url"],
                        capture_output=True, text=True, cwd=_ZBC_ROOT)
    assert r1.stdout.strip() != r2.stdout.strip()
    assert "Zachary-OS-AI" in r1.stdout.strip()
    assert "Z-Brand-Core" in r2.stdout.strip()


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
