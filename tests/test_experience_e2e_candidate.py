# -*- coding: utf-8 -*-
"""P0-E2E-03 Critical E2E：以真实候选库 data/monitor.db 的**只读副本**跑完整生产蓝图栈。

红线与覆盖：
  * 绝不打开/写入仓库真实库：先复制到 tmp_path，四个隔离环境变量全部指向副本；
  * 44 屏全部 HTTP 200 且绑定 Canonical 只读 ViewModel；字段级缺口仍诚实 notcollected；
  * 任意 ViewModel 文本不得出现独立 token 的 undefined / NaN / [object Object]，
    也不得出现 float NaN（词边界匹配，避免误伤 governance 这类正常词）；
  * AI composer 权限门在挂载 app 内三态可达：ANALYZE granted / WRITE denied / PUSH permanent_deny；
  * 外部无数据源指标必须 value=None + notcollected（CTH-01 footfall/member_sales），绝不填 0；
  * identity 不泄漏绝对路径/密钥；
  * 跑完后**源库文件 sha256 不变、源目录不产生 -wal/-shm 侧车**（只读不变性）。

未通过 LUMENIS_TEST_SEED_DB 提供候选库时本模块整体 skip，不伪造候选库。
"""
import hashlib
import importlib
import io
import json
import os
import re
import shutil
import sys

import pytest
from flask import Flask

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

SRC_DB = os.environ.get("LUMENIS_TEST_SEED_DB", "").strip()
ALL_SCREENS_REGISTRY = os.path.join(
    REPO_ROOT, "experience_v2", "06_CONTRACTS", "actions", "ACTION_REGISTRY.json"
)
# 全部 44 屏均有 Canonical 只读 Runtime ViewModel；外部字段仍可在屏内逐项 notcollected，
# 但不得再让整屏退回 prototype。
EXPECTED_UNBOUND = set()
_BAD_TOKEN = re.compile(r"\bundefined\b|\bNaN\b|\[object object\]", re.IGNORECASE)

pytestmark = pytest.mark.skipif(
    not os.path.exists(SRC_DB),
    reason="未提供 LUMENIS_TEST_SEED_DB 候选库（CI 环境），跳过候选副本 E2E",
)


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def _sidecar_state(path):
    base = os.path.basename(path)
    folder = os.path.dirname(path)
    return {
        name: (_sha256(os.path.join(folder, name)), os.path.getsize(os.path.join(folder, name)))
        for name in os.listdir(folder)
        if name.startswith(base + "-") and os.path.isfile(os.path.join(folder, name))
    }


def _scan_bad_tokens(o, path="$"):
    hits = []
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(k, str) and _BAD_TOKEN.search(k):
                hits.append(f"{path}.<badkey {k}>")
            hits += _scan_bad_tokens(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            hits += _scan_bad_tokens(v, f"{path}[{i}]")
    elif isinstance(o, float):
        if o != o:
            hits.append(f"{path}.<float NaN>")
    elif isinstance(o, str):
        if _BAD_TOKEN.search(o):
            hits.append(f"{path}={o[:40]!r}")
    return hits


@pytest.fixture()
def candidate_client(tmp_path, monkeypatch):
    src_before = _sha256(SRC_DB)
    sidecars_before = _sidecar_state(SRC_DB)
    copy_db = tmp_path / "candidate_copy.db"
    shutil.copy2(SRC_DB, copy_db)
    for k in ("ZBC_DB_PATH", "ZBC_EVIDENCE_DB_PATH",
              "ZBC_RUNTIME_GUARDIAN_DB", "ZBC_TOKEN_DB_PATH"):
        monkeypatch.setenv(k, str(copy_db))
    monkeypatch.delenv("PERMISSION_GATE_TESTING", raising=False)
    import permission_gate
    # The suite's session fixture enables this independent in-memory bypass.
    # Removing the environment variable alone does not restore real authorization.
    monkeypatch.setattr(permission_gate, "_TESTING_BYPASS_ENABLED", False)

    import database
    importlib.reload(database)
    database.DB_PATH = str(copy_db)

    import experience_runtime
    # 懒加载合并全部 44 屏 builder（P0-E2E-03 破循环导入），必须无传播错误且全量绑定
    builders = experience_runtime._all_builders()
    assert experience_runtime._PROPAGATION_IMPORT_ERROR == ""
    assert len(builders) == 44

    app = Flask(__name__)
    experience_runtime.register_experience_runtime(app)
    return app.test_client(), src_before, sidecars_before


def _all_screen_ids():
    with io.open(ALL_SCREENS_REGISTRY, encoding="utf-8") as f:
        return sorted(json.load(f)["screens"].keys())


def test_all_44_screens_200_and_binding_is_honest(candidate_client):
    cli, _, _ = candidate_client
    bound, unbound = [], []
    for sid in _all_screen_ids():
        r = cli.get(f"/api/experience/screen/{sid}")
        assert r.status_code == 200, sid
        j = r.get_json()
        assert _scan_bad_tokens(j) == [], (sid, _scan_bad_tokens(j))
        if j.get("bound"):
            assert j.get("source") == "runtime", sid
            bound.append(sid)
        else:
            # 未绑定必须诚实标注外部依赖，且不返回伪造 sections 数据
            assert j.get("classification") == "BLOCKED_BY_EXTERNAL_DEPENDENCY", sid
            unbound.append(sid)
    assert set(unbound) == EXPECTED_UNBOUND
    assert len(bound) == 44


def test_cth01_external_sources_not_faked_as_zero(candidate_client):
    cli, _, _ = candidate_client
    j = cli.get("/api/experience/screen/CTH-01").get_json()
    metrics = {m["id"]: m for s in j["sections"] if s.get("type") == "kpis"
               for m in s.get("items", [])}
    for fid in ("cth.footfall", "cth.member_sales"):
        assert metrics[fid]["value"] is None
        assert metrics[fid]["state"] == "notcollected"


def test_ai_intent_gate_three_states_in_mounted_app(candidate_client):
    cli, _, _ = candidate_client

    def post(action):
        return cli.post("/api/experience/ai/intent",
                        json={"task": f"e2e {action}", "action_type": action})

    a = post("ANALYZE")
    assert a.status_code == 200 and a.get_json()["permission_status"] == "granted"
    w = post("WRITE")
    assert w.status_code == 403 and w.get_json()["status"] == "denied"
    p = post("PUSH")
    assert p.status_code == 403 and p.get_json()["status"] == "permanent_deny"


def test_identity_does_not_leak_absolute_path(candidate_client):
    cli, _, _ = candidate_client
    j = cli.get("/api/experience/runtime/identity").get_json()
    assert j["ok"] is True
    blob = json.dumps(j, ensure_ascii=False)
    assert REPO_ROOT.replace("\\", "/") not in blob.replace("\\", "/")
    assert j["database"]["name"] == "candidate_copy.db"
    assert j["database"]["resolved"] is True

    canonical = cli.get("/api/runtime/identity")
    assert canonical.status_code == 200
    assert canonical.get_json()["api"] == j["api"]


def test_source_db_immutable_after_full_run(candidate_client):
    cli, src_before, sidecars_before = candidate_client
    # 跑一遍全部屏幕 + 外壳 + runtime.js，制造完整读负载
    for sid in _all_screen_ids():
        cli.get(f"/api/experience/screen/{sid}")
    cli.get("/experience/")
    cli.get("/experience/assets/runtime.js")
    # 源库字节必须逐位不变
    assert _sha256(SRC_DB) == src_before
    # 已有 WAL/SHM 属候选库既有状态；完整读负载不得新增或改变它们。
    assert _sidecar_state(SRC_DB) == sidecars_before
