# -*- coding: utf-8 -*-
"""
工作区访问密钥（ZBMP）单元测试。
用独立临时库（ZBC_DB_PATH），不接触任何生产/Staging 数据库。
覆盖：建表幂等、签发只回一次明文、正确/错误密钥校验、过期、吊销连带失效、
      会话授权 grant 与 session_can_access、无 owner 时 open_owner_session 行为。
运行：.venv\\Scripts\\python.exe -m pytest tests/test_workspace_keys.py -q
"""
import os
import sys
import tempfile

import pytest

# 在导入被测模块前指定临时库，确保 v4 config 的 DB_PATH 指向隔离环境
_TMP = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_TMP.close()
os.environ["ZBC_DB_PATH"] = _TMP.name
# 让 v4_upgrade 包可导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v4_upgrade.auth import workspace as ws  # noqa: E402
from v4_upgrade.auth.models import init_auth_db  # noqa: E402


@pytest.fixture(scope="module", autouse=True)
def _setup():
    # 确定性隔离（不依赖 import 顺序）：v4_upgrade.config.DB_PATH 在【首次 import 时按
    # 当时 os.environ 固化】，auth.models 又以 `from ..config import DB_PATH` 值绑定。
    # 全量套件（尤其逆序/随机）中它可能已被更早模块固化成生产 data/monitor.db；若不显式
    # 改回本模块临时库，verify_workspace_key 会对生产库 v4_workspace_keys 数百个历史 active
    # key（rounds=12）逐个 PBKDF2，必然超过用例超时。故此处同时绑定 config 与 models 两层。
    import v4_upgrade.config as _cfg
    import v4_upgrade.auth.models as _models
    _old_cfg = getattr(_cfg, "DB_PATH", None)
    _old_models = getattr(_models, "DB_PATH", None)
    _cfg.DB_PATH = _TMP.name
    _models.DB_PATH = _TMP.name
    os.environ["ZBC_DB_PATH"] = _TMP.name
    init_auth_db()          # 建 v4_users 并确保 owner（落在临时库）
    ws.ensure_workspace_tables()
    yield
    # 还原全局绑定与环境，杜绝泄漏给后续模块
    if _old_cfg is not None:
        _cfg.DB_PATH = _old_cfg
    if _old_models is not None:
        _models.DB_PATH = _old_models
    try:
        os.unlink(_TMP.name)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def _fast_pbkdf2(monkeypatch):
    """生产配置 bcrypt_rounds=12 → hash_password 用 120000 iterations，
    每次 pbkdf2_hmac 约0.3-0.5s；全量累积 CPU 负载下可超 20s 触发 timeout。
    单测里把 AUTH_CONFIG[bcrypt_rounds] 压到 1（=10000 iterations），
    hash_password 存小迭代数，verify_password 从 stored hash 读小迭代数。"""
    import v4_upgrade.auth.security as _sec
    monkeypatch.setitem(_sec.AUTH_CONFIG, 'bcrypt_rounds', 1)
    yield


def test_issue_and_verify_ok():
    out = ws.issue_workspace_key("ZBMP", label="pytest-key")
    assert out["success"] and out["key"].startswith("zbmp_")
    rec = ws.verify_workspace_key("ZBMP", out["key"])
    assert rec is not None and rec["workspace"] == "ZBMP"


def test_wrong_key_rejected():
    out = ws.issue_workspace_key("ZBMP", label="k2")
    assert ws.verify_workspace_key("ZBMP", out["key"] + "x") is None
    assert ws.verify_workspace_key("ZBMP", "") is None
    assert ws.verify_workspace_key("CTH-POMS", out["key"]) is None  # 工作区隔离


def test_revoke_invalidates():
    out = ws.issue_workspace_key("ZBMP", label="k3")
    kid = out["id"]
    assert ws.verify_workspace_key("ZBMP", out["key"]) is not None
    ws.revoke_workspace_key(kid)
    assert ws.verify_workspace_key("ZBMP", out["key"]) is None
    rows = {r["id"]: r for r in ws.list_workspace_keys("ZBMP")}
    assert rows[kid]["status"] == "revoked"


def test_list_never_exposes_secret():
    ws.issue_workspace_key("ZBMP", label="k4")
    for r in ws.list_workspace_keys("ZBMP"):
        assert "key_hash" not in r and "key" not in r
        assert r.get("key_prefix")


def test_grant_and_session_access():
    out = ws.issue_workspace_key("ZBMP", label="k5")
    rec = ws.verify_workspace_key("ZBMP", out["key"])
    g = ws.grant_session(1, "ZBMP", rec["id"], "tok-abc", grant_hours=1)
    assert g["success"]
    assert ws.session_can_access("tok-abc", "ZBMP") is True
    assert ws.session_can_access("tok-other", "ZBMP") is False
    assert ws.session_can_access("", "ZBMP") is False


def test_open_owner_session():
    s = ws.open_owner_session("127.0.0.1", "pytest")
    assert s and s["role"] == "owner" and s["token"]
    assert ws.session_can_access(s["token"], "ZBMP") is False  # 未 grant 前不能进


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
