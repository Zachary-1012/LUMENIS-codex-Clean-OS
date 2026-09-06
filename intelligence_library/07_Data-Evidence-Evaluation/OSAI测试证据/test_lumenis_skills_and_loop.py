# -*- coding: utf-8 -*-
"""S01-S12 Source Skills 可运行实现测试 + Engineering Loop 预算边界测试。
确定性、离线、只读（S10/S11 指向临时 DB，不碰生产库）。
"""
import os
import sys
import tempfile
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from osai_engine import engineering_loop
from osai_engine.skills import source_skills

OSAI_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------- S01-S12 Executor 基本契约 ----------
def test_all_12_executors_present():
    for sid in ["S%02d" % i for i in range(1, 13)]:
        assert sid in source_skills.SKILL_EXECUTORS, "缺 executor %s" % sid
    assert callable(source_skills.run_skill)


def test_s01_source_fact_scanner():
    r = source_skills.s01_source_fact_scanner(OSAI_ROOT)
    assert r["status"] == "ok"
    assert r["data"]["file_count"] > 0
    assert "python_version" in r["data"]


def test_s01_bad_path():
    r = source_skills.s01_source_fact_scanner("Z:/nonexistent-path-xyz")
    assert r["status"] == "error"


def test_s02_sha_verifier():
    r = source_skills.s02_sha_verifier(OSAI_ROOT)
    assert r["status"] == "ok"
    assert len(r["data"]["head_sha"]) >= 7
    assert "branch" in r["data"]


def test_s03_git_state_auditor():
    r = source_skills.s03_git_state_auditor(OSAI_ROOT)
    assert r["status"] == "ok"
    for k in ("branch", "staged", "unstaged", "untracked"):
        assert k in r["data"]


def test_s04_file_inventory():
    r = source_skills.s04_file_inventory(OSAI_ROOT)
    assert r["status"] == "ok"
    assert r["data"]["total"] > 0
    assert ".py" in r["data"]["by_extension"]


def test_s05_module_mapper():
    r = source_skills.s05_module_mapper(OSAI_ROOT)
    assert r["status"] == "ok"
    assert r["data"]["module_count"] >= 10


def test_s06_function_mapper():
    r = source_skills.s06_function_mapper(OSAI_ROOT)
    assert r["status"] == "ok"
    assert r["data"]["total_definitions"] > 0


def test_s07_api_mapper_runs():
    # OSAI 本身可能无 Flask 路由，验证不报错且结构完整
    r = source_skills.s07_api_mapper(OSAI_ROOT)
    assert r["status"] == "ok"
    assert "route_count" in r["data"]


def test_s08_dependency_auditor():
    r = source_skills.s08_dependency_auditor(OSAI_ROOT)
    assert r["status"] == "ok"
    assert "third_party_imports" in r["data"]


def test_s09_config_auditor_readonly():
    r = source_skills.s09_config_auditor(OSAI_ROOT)
    assert r["status"] == "ok"
    # 只报告文件名/行号，不回显任何密钥值
    for item in r["data"]["secret_suspects"]:
        assert "value" not in item


def test_s10_s11_temp_db():
    with tempfile.TemporaryDirectory() as td:
        db = os.path.join(td, "data", "monitor.db")
        os.makedirs(os.path.dirname(db), exist_ok=True)
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, body TEXT)")
        con.execute("INSERT INTO notes(body) VALUES('x')")
        con.commit()
        con.close()
        r10 = source_skills.s10_db_schema_auditor(td, db_rel=os.path.join("data", "monitor.db"))
        assert r10["status"] == "ok"
        assert "notes" in r10["data"]["schema"]
        assert r10["data"]["schema"]["notes"]["row_count"] == 1
        r11 = source_skills.s11_db_integrity_checker(td, db_rel=os.path.join("data", "monitor.db"))
        assert r11["status"] == "ok"
        assert r11["data"]["healthy"] is True


def test_s12_runtime_health():
    r = source_skills.s12_runtime_health()
    assert r["status"] == "ok"
    assert "python_version" in r["data"]
    assert "modules" in r["data"]


def test_run_skill_dispatch_and_unknown():
    r = source_skills.run_skill("S12")
    assert r["status"] == "ok"
    bad = source_skills.run_skill("S99", OSAI_ROOT)
    assert bad["status"] == "error"


# ---------- Engineering Loop 预算/阻断边界 ----------
def test_loop_max_iterations_budget():
    loop = engineering_loop.EngineeringLoop("预算测试", repo="OSAI",
                                            max_iterations=3, max_seconds=999)
    loop.step("INSPECT", "ok")
    loop.step("PLAN", "ok")
    loop.step("EXECUTE", "ok")
    assert loop.budget_exceeded()
    # 预算超限后 step 拒绝推进并标记 failed
    rec = loop.step("VERIFY", "ok")
    assert rec["status"] == "failed"
    assert "BUDGET" in rec["detail"]
    assert loop.allowed_next() == []


def test_loop_blocked_stops_progress():
    loop = engineering_loop.EngineeringLoop("阻断测试", repo="OSAI")
    loop.step("INSPECT", "ok")
    loop.block("等待人工提供数据库路径")
    assert loop.allowed_next() == []
    rec = loop.step("PLAN", "ok")
    assert rec["status"] == "blocked"


def test_loop_checkpoint_records_state():
    loop = engineering_loop.EngineeringLoop("检查点测试", repo="OSAI")
    loop.step("INSPECT", "ok")
    cp = loop.checkpoint()
    assert cp["iteration"] == 1
    assert cp["last_stage"]["stage"] == "INSPECT"
    assert "elapsed_seconds" in cp
    assert len(loop._checkpoints) == 1


def test_loop_evidence_contains_budget():
    loop = engineering_loop.EngineeringLoop("证据测试", repo="OSAI", max_seconds=60)
    loop.step("INSPECT", "ok")
    ev = loop.to_evidence_dict()
    for k in ("iteration", "max_iterations", "elapsed_seconds", "max_seconds",
              "budget_exceeded", "blocked", "checkpoints"):
        assert k in ev
