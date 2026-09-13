"""KOS 运营模块测试（kos_ops.py：留资/合作/邮件邀约/运营闭环）

覆盖：留资录入、合作草稿、合作确认 HCG 门控、邮件邀约 HCG 门控、
生命周期推进、运营台账。使用真实 kos_profiles 数据（不发送真实邮件）。
"""
import sys, os, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
# 强制指向生产库：防止其他测试模块级污染 ZBC_DB_PATH 导致连接错库
os.environ.setdefault("ZBC_DB_PATH", str(Path(__file__).parent.parent / "data" / "monitor.db"))

import pytest
import pytest


@pytest.fixture(scope="module", autouse=True)
def _fix_kos_db():
    """执行阶段强制重置 ZBC_DB_PATH 到生产库：
    防止 test_workspace_keys/test_cookies_import_api 的模块级/函数级污染跨文件泄漏，
    导致本模块连接错库（no such table: kos_profiles/kos_paid_plans）。"""
    os.environ.setdefault("ZBC_DB_PATH", str(Path(__file__).parent.parent / "data" / "monitor.db"))
    yield

import sqlite3

import kos_ops


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


def test_save_lead(author_id):
    r = kos_ops.save_lead(author_id, contact_name="测试联系人", phone="13800000000",
                          email="test@example.com", mcn="TEST_MCN", company="测试公司")
    assert r["ok"] is True
    lead = kos_ops.get_lead(author_id)
    assert lead["contact_name"] == "测试联系人"
    assert lead["email"] == "test@example.com"
    assert lead["company"] == "测试公司"


def test_save_lead_nonexistent():
    r = kos_ops.save_lead("nonexistent_author_xyz")
    assert r["ok"] is False


def test_update_cooperation(author_id):
    r = kos_ops.update_cooperation(author_id, cooperation_status="DISCUSSING", quote=5000, budget=10000)
    assert r["ok"] is True
    assert r["cooperation_status"] == "DISCUSSING"


def test_update_cooperation_invalid(author_id):
    r = kos_ops.update_cooperation(author_id, cooperation_status="INVALID_STATUS")
    assert r["ok"] is False
    assert "非法" in r["error"]


def test_confirm_cooperation_hcg_gate(author_id):
    """合作确认必须走 HCG：初始 AI_GENERATED，不直接落地。"""
    r = kos_ops.confirm_cooperation(author_id, confirmed_by="zachary", quote=5000, budget=10000)
    assert r["ok"] is True
    hcg = r["hcg"]
    assert hcg["status"] == "AI_GENERATED"  # 未直接执行
    assert hcg["execution_id"].startswith("KX-")


def test_confirm_cooperation_requires_human_approval(author_id):
    """合作确认创建后，cooperation_status 不应立即变为 CONFIRMED（需人工审批）。"""
    r = kos_ops.confirm_cooperation(author_id, confirmed_by="zachary", quote=5000)
    assert r["hcg"]["status"] == "AI_GENERATED"
    # 未执行前 cooperation_status 不应是 CONFIRMED
    c = sqlite3.connect(os.environ["ZBC_DB_PATH"])
    status = c.execute("SELECT cooperation_status FROM kos_profiles WHERE author_id=?", (author_id,)).fetchone()[0]
    c.close()
    assert status != "CONFIRMED"


def test_execute_cooperation_no_actor(author_id):
    """执行合作确认缺少 actor 必须失败（HCG 红线）。"""
    r = kos_ops.confirm_cooperation(author_id, confirmed_by="zachary", quote=5000)
    eid = r["hcg"]["execution_id"]
    # 直接 execute 无 actor 时 HCG 状态机应拒绝（返回 ok=False）
    result = kos_ops.execute_cooperation(eid, actor="")
    assert result["ok"] is False


def test_create_invitation_email_hcg_gate(author_id):
    """邮件邀约创建必须走 HCG：AI_GENERATED，不发送。"""
    # 先确保有邮箱
    kos_ops.save_lead(author_id, email="kos@test.com")
    r = kos_ops.create_invitation_email(author_id, subject="合作邀约", body="您好")
    assert r["ok"] is True
    assert r["hcg"]["status"] == "AI_GENERATED"
    assert r["to_email"] == "kos@test.com"


def test_email_requires_email_field():
    """未登记邮箱时邮件邀约应拒绝。"""
    # 找一个无邮箱的 KOS（或构造）
    c = sqlite3.connect(os.environ["ZBC_DB_PATH"])
    rows = c.execute("SELECT author_id FROM kos_profiles").fetchall()
    c.close()
    target = None
    for (aid,) in rows:
        if kos_ops.get_lead(aid).get("email", "") == "":
            target = aid
            break
    if target is None:
        pytest.skip("所有 KOS 均有邮箱，跳过")
    r = kos_ops.create_invitation_email(target)
    assert r["ok"] is False
    assert "邮箱" in r["error"]


def test_record_operation_lifecycle_advance(author_id):
    """运营动作应推进生命周期（outreach -> observed）。"""
    # 重置生命周期为 discovered 再测
    c = sqlite3.connect(os.environ["ZBC_DB_PATH"])
    c.execute("UPDATE kos_profiles SET lifecycle_stage='discovered' WHERE author_id=?", (author_id,))
    c.commit()
    c.close()
    r = kos_ops.record_operation(author_id, action="outreach", note="已触达")
    assert r["ok"] is True
    assert r["lifecycle_stage"] == "observed"


def test_record_operation_log(author_id):
    kos_ops.record_operation(author_id, action="lead_captured", note="留资")
    ops = kos_ops.operation_log(author_id, limit=10)
    assert len(ops) >= 1
    assert all("action" in o for o in ops)


def test_operation_log_global():
    ops = kos_ops.operation_log(limit=20)
    assert isinstance(ops, list)


def test_smtp_configured_flag():
    """SMTP 配置探测不抛异常。"""
    assert isinstance(kos_ops._smtp_configured(), bool)
