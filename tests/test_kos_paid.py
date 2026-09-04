"""KOS P2 投流与奖励执行闭环测试（kos_paid.py）

覆盖：投流计划 HCG 门控、投流执行全路径、效果反馈 ROI、奖励发放 HCG 门控、台账。
使用真实 kos_profiles 数据（不实际投放/发放，仅登记与台账）。
"""
import sys, os, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
# 强制指向生产库：防止其他测试模块级污染 ZBC_DB_PATH 导致连接错库
os.environ["ZBC_DB_PATH"] = str(Path(__file__).parent.parent / "data" / "monitor.db")

import pytest
import pytest


@pytest.fixture(scope="module", autouse=True)
def _fix_kos_db():
    """执行阶段强制重置 ZBC_DB_PATH 到生产库：
    防止 test_workspace_keys/test_cookies_import_api 的模块级/函数级污染跨文件泄漏，
    导致本模块连接错库（no such table: kos_profiles/kos_paid_plans）。"""
    os.environ["ZBC_DB_PATH"] = str(Path(__file__).parent.parent / "data" / "monitor.db")
    yield

import sqlite3

import kos_paid


@pytest.fixture()
def author_id():
    c = sqlite3.connect(os.environ["ZBC_DB_PATH"])
    row = c.execute("SELECT author_id FROM kos_profiles LIMIT 1").fetchone()
    if not row:
        # 表为空时插入测试数据，使测试自洽（不依赖生产数据）
        c.execute("INSERT OR IGNORE INTO kos_profiles (author_id, author_nickname, kos_tier) VALUES (?, ?, ?)",
                  ("test_author_kos_001", "测试KOS作者", "C"))
        c.commit()
        row = ("test_author_kos_001",)
    aid = row[0]
    c.close()
    return aid


def test_create_paid_plan_hcg_gate(author_id):
    """投流计划创建必须走 HCG：AI_GENERATED，不实际投放。"""
    r = kos_paid.create_paid_plan(author_id=author_id, budget=2000, channel="xhs", expected_reach=50000)
    assert r["ok"] is True
    assert r["hcg"]["status"] == "AI_GENERATED"
    assert "需人工审批" in r["hcg"]["note"]


def test_create_paid_plan_requires_budget(author_id):
    """预算为 0 时拒绝。"""
    r = kos_paid.create_paid_plan(author_id=author_id, budget=0)
    assert r["ok"] is False


def test_execute_paid_plan_full_path(author_id):
    """投流执行全路径（HCG 状态机完整流转）。"""
    r = kos_paid.create_paid_plan(author_id=author_id, budget=2000)
    eid = r["hcg"]["execution_id"]
    r2 = kos_paid.execute_paid_plan(eid, actor="zachary")
    assert r2["ok"] is True
    assert r2["plan_id"].startswith("PAID-")


def test_execute_paid_plan_requires_actor(author_id):
    """缺少 actor 时投流执行必须失败（HCG 红线）。"""
    r = kos_paid.create_paid_plan(author_id=author_id, budget=2000)
    eid = r["hcg"]["execution_id"]
    r2 = kos_paid.execute_paid_plan(eid, actor="")
    assert r2["ok"] is False


def test_record_paid_result_roi(author_id):
    """效果反馈应记录真实投放数据并计算 ROI。"""
    r = kos_paid.create_paid_plan(author_id=author_id, budget=2000)
    eid = r["hcg"]["execution_id"]
    r2 = kos_paid.execute_paid_plan(eid, actor="zachary")
    pid = r2["plan_id"]
    r3 = kos_paid.record_paid_result(pid, spend=2000, impressions=50000, clicks=1200, conversions=60)
    assert r3["ok"] is True
    assert r3["roi"] == 0.5  # (60*50 - 2000)/2000
    assert r3["clicks"] == 1200


def test_record_paid_result_nonexistent():
    r = kos_paid.record_paid_result("NONEXISTENT_PLAN", spend=100)
    assert r["ok"] is False


def test_issue_reward_hcg_gate(author_id):
    """奖励发放创建必须走 HCG：AI_GENERATED，不实际发放。"""
    r = kos_paid.issue_reward(author_id, points=500, amount=100, reason="月度优质内容")
    assert r["ok"] is True
    assert r["hcg"]["status"] == "AI_GENERATED"


def test_issue_reward_requires_value(author_id):
    """积分与金额都为 0 时拒绝。"""
    r = kos_paid.issue_reward(author_id, points=0, amount=0)
    assert r["ok"] is False


def test_execute_reward_full_path(author_id):
    """奖励发放全路径（HCG 状态机完整流转）。"""
    r = kos_paid.issue_reward(author_id, points=500, amount=100, reason="测试")
    eid = r["hcg"]["execution_id"]
    r2 = kos_paid.execute_reward(eid, actor="zachary")
    assert r2["ok"] is True
    assert r2["reward_id"].startswith("RWD-")


def test_execute_reward_requires_actor(author_id):
    """缺少 actor 时奖励发放必须失败（HCG 红线）。"""
    r = kos_paid.issue_reward(author_id, points=500, amount=100, reason="测试")
    eid = r["hcg"]["execution_id"]
    r2 = kos_paid.execute_reward(eid, actor="")
    assert r2["ok"] is False


def test_paid_plans_ledger(author_id):
    kos_paid.create_paid_plan(author_id=author_id, budget=1000)
    plans = kos_paid.paid_plans(author_id)
    assert isinstance(plans, list)
    assert all("plan_id" in p for p in plans)


def test_reward_ledger(author_id):
    kos_paid.issue_reward(author_id, points=100, amount=20, reason="测试")
    rewards = kos_paid.reward_ledger(author_id)
    assert isinstance(rewards, list)
    assert all("reward_id" in r for r in rewards)
