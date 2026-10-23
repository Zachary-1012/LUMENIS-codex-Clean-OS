# -*- coding: utf-8 -*-
"""序境 Experience V2 生产运行时挂载层测试（experience_runtime）。

隔离原则（红线）：
  * 每个测试使用 pytest tmp_path 下的独立 SQLite（ZBC_DB_PATH），绝不写仓库 data/ 或生产库；
  * 只挂 experience_bp 蓝图，不启动全量 app.py / 调度线程；
  * 外部无数据源的指标必须 value=None + state=notcollected，禁止伪造 0 或假百分比；
  * 有真实源的指标必须等于隔离库内现算值；identity 不得泄露绝对路径/密钥。
"""
import datetime as dt
import importlib
import os
import sys

import pytest
from tests.test_saved_document_workflow import workspace as owner_workspace
from tests.test_content_scoped_patterns import client as content_client
from tests.test_bmp09_request_binding import client as report_client

import experience_runtime as runtime_owner
REPO_ROOT = os.path.dirname(os.path.abspath(runtime_owner.__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


@pytest.fixture
def workspace(owner_workspace, monkeypatch):
    # Modules imported by earlier fixtures must use this same actual DB.
    import account.models
    import lumenis.auth.models as auth_models
    import lumenis.shared.database as shared_database
    monkeypatch.setattr(account.models, "get_repository", lambda: owner_workspace["repo"])
    monkeypatch.setattr(shared_database, "get_repository", lambda: owner_workspace["repo"])
    monkeypatch.setattr(auth_models, "get_repository", lambda: owner_workspace["repo"])
    return owner_workspace

@pytest.fixture()
def isolated_client(tmp_path, monkeypatch):
    db_file = tmp_path / "isolated_monitor.db"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_file))
    monkeypatch.setenv("ZBC_ACTIVE_BRAND", "guangzhou_taikoo_hui")

    import database
    importlib.reload(database)  # 让 DB_PATH 取到隔离路径
    database.DB_PATH = str(db_file)
    database.init_db()
    import runtime_guardian
    # Each disposable database owns its actual Guardian instance lifecycle.
    monkeypatch.setattr(runtime_guardian, "_instances", {})

    from lumenis.shared.evidence import store as evidence_store
    # Bind real Shared writers/readers to this same disposable SQLite.
    # Imported repository singletons may predate this fixture environment.
    import lumenis.shared.database as shared_database
    repository = shared_database.DatabaseRepository(str(db_file))
    monkeypatch.setattr(shared_database, "get_repository", lambda: repository)
    monkeypatch.setattr(evidence_store, "get_repository", lambda: repository)
    evidence_store.init_evidence_store(str(db_file))
    with repository.transaction() as connection:
        evidence_store.ensure_evidence_schema(connection)
    # Match the app startup owner migration against this disposable path.
    from lumenis.shared.database import migrations
    monkeypatch.setattr(migrations, "DB_PATH", str(db_file))
    assert migrations.migrate(), "disposable canonical startup migration failed"
    # The real app initializes the AI task tables before exposing these screens.
    import ai_task_engine
    ai_task_engine.init_task_engine_db()
    import shared_artifacts
    import content_generation
    from lumenis.shared.reporting import saved_work
    from lumenis.importer import documents
    import kos_engine
    import account.models
    for module in (shared_artifacts, content_generation, saved_work, documents, kos_engine, account.models):
        monkeypatch.setattr(module, "get_repository", lambda: repository)
    monkeypatch.setenv("ZBC_ARTIFACT_DIR", str(tmp_path / "artifacts"))
    shared_artifacts.ensure_artifact_table()
    content_generation.init_db()

    today = dt.date.today().strftime("%Y-%m-%d")
    with database.get_db() as c:
        rows = [
            ("n1", "太古汇 负面投诉 排队", "negative", "high", 8),
            ("n2", "太古汇 差评 服务", "negative", "medium", 3),
            ("n3", "太古汇 正常分享", "neutral", "low", 1),
            ("n4", "太古汇 日常打卡", "neutral", "low", 2),
            ("n5", "太古汇 好评推荐", "positive", "low", 5),
        ]
        for nid, title, sent, risk, eng in rows:
            c.execute(
                """INSERT INTO notes(note_id,title,content,sentiment,risk_level,likes,comments,
                   collects,shares,publish_date,is_taikoo_verified,relevance_status,status)
                   VALUES(?,?,?,?,?,?,?,?,?,?,1,'relevant','active')""",
                (nid, title, title, sent, risk, eng, eng, 0, 0, today),
            )
        c.execute(
            """INSERT INTO events(event_key,title,summary,risk_level,status,mention_count,
               source_count,first_seen,last_seen,event_date)
               VALUES('e1','太古汇 排队投诉事件','多平台提及','high','active',5,3,?,?,?)""",
            (today, today, today),
        )

    evidence_store.record_evidence(
        source="unit", feature_id="FUNC-RISK-01", level="feature",
        result="pass", account="acc1", actual="risk computed",
    )
    evidence_store.record_evidence(
        source="integration", feature_id="EVENT-GRAPH", level="feature",
        result="pass", account="acc1", actual="event chain",
    )

    import experience_runtime
    from flask import Flask
    app = Flask(__name__)
    app.config["LUMENIS_OPEN_WORKSPACE"] = True
    from canonical_data import ensure_canonical_table
    ensure_canonical_table(str(db_file))
    app.register_blueprint(experience_runtime.experience_bp)
    return app.test_client(), str(db_file)


def _sections(j):
    return {s.get("type"): s for s in j["sections"]}


def _kpis(j):
    return {m["id"]: m for m in _sections(j)["kpis"]["items"]}


def test_legacy_browser_surface_is_not_served(isolated_client):
    cli, _ = isolated_client
    assert cli.get("/experience/").status_code == 404


def test_sys06_is_real_internal_browser_surface(isolated_client):
    """SYS-06 must expose the existing internal browser, not the old fixture view."""
    cli, _ = isolated_client
    payload = cli.get("/api/experience/screen/SYS-06").get_json()
    assert payload["bound"] is True
    raw = "\n".join(
        section.get("html", "")
        for section in payload["sections"]
        if section.get("type") == "raw"
    )
    assert 'data-browser-surface' in raw
    assert 'id="browser-shell"' in raw
    assert 'id="address-input"' in raw
    assert 'id="viewport-img-wrap"' in raw
    assert 'id="panel-ai-agent"' in raw
    assert 'id="hk-auth-state"' in raw
    assert 'id="browser-auth-modal"' in raw
    assert 'BrowserApp.openHKLogin()' in raw
    assert '大陆采集' in raw
    assert '在外部浏览器打开（仅手动）' in raw
    assert 'example.com/subject' not in raw
    assert '原型占位' not in raw


# --------------------------- CTH-01 真实绑定 + 诚实缺失 ---------------------------
def test_cth01_external_metrics_are_not_collected(isolated_client):
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/CTH-01").get_json()
    assert j["bound"] is True
    k = _kpis(j)
    # POS/销售外部源缺失：必须 None + notcollected，绝不是 0
    assert k["cth.footfall"]["value"] is None and k["cth.footfall"]["state"] == "notcollected"
    assert k["cth.member_sales"]["value"] is None and k["cth.member_sales"]["state"] == "notcollected"
    blocked = {b["field"] for b in j["binding"]["blocked"]}
    assert {"cth.footfall", "cth.member_sales"} <= blocked



def _admit_existing_note(db_path, monkeypatch, source_id, *, bmp=False):
    import json
    import sqlite3
    import database
    from canonical_data import CanonicalRecord, persist_canonical
    from lumenis.shared.evidence import store
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_KEY_RING", json.dumps({"consumer-test":"disposable-synthetic-key"}))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "consumer-test")
    product, domain = ("ZBMP", "zbmp") if bmp else ("CTH", "cth")
    subject, brand = (None, "BRAND-TEST") if bmp else ("SUBJECT-TEST", None)
    scope = {"product_id":product, "domain_id":domain, "subject_id":subject, "brand_focus_id":brand, "global_scope":False}
    with sqlite3.connect(db_path) as con:
        title, content, sentiment, risk = con.execute('SELECT title,content,sentiment,risk_level FROM notes WHERE note_id=?',(source_id,)).fetchone()
        evidence = store.record_evidence(connection=con, source="public_http", project="LUMENIS",product=product,domain_id=domain,subject_id=subject,brand_focus_id=brand,feature_id="SYNTHETIC_CONSUMER",test_name="signed-owner-source",result="PASS",status="verified",inputs={"source_ids":[source_id]},outputs={"synthetic":True})
        assert evidence > 0
        con.execute("UPDATE notes SET subject_id=?,brand_focus_id=?,product_id=?,domain_id=?,scope_status='VERIFIED',scope_evidence_ref=? WHERE note_id=?",(subject,brand,product,domain,str(evidence),source_id))
        persist_canonical(con,CanonicalRecord(canonical_id="can-consumer-"+source_id,product_id=product,domain_id=domain,subject_id=subject,brand_focus_id=brand,scope_status="VERIFIED",scope_evidence_ref=str(evidence),source_id=source_id,external_id=source_id,source_type="note",source_table="notes",source_platform="x",title=title,content=content,sentiment=sentiment,risk_level=risk,publish_datetime=dt.date.today().isoformat(),raw_ref=json.dumps({"table":"notes","note_id":source_id})))
    return scope

def test_cth01_real_metrics_match_isolated_db(isolated_client, monkeypatch):
    import database
    cli, db_path = isolated_client
    scope = _admit_existing_note(db_path, monkeypatch, "n1")
    _admit_existing_note(db_path, monkeypatch, "n2")
    event = database.upsert_event({"event_key":database._event_scope_token(scope)+".cth-test", "title":"Signed service disruption", "status":"active"},scope=scope,mentions=[{"source_type":"note","source_id":"n1"}])
    assert event > 0
    j = cli.get("/api/experience/screen/CTH-01").get_json()
    k = _kpis(j)
    assert k["cth.negative_voice"]["value"] == 2
    assert k["cth.negative_voice"]["state"] == "ready"
    assert (k["cth.open_events"]["value"] or 0) >= 1
    # 不得出现原型里的伪造数字
    blob = __import__("json").dumps(j, ensure_ascii=False)
    assert "38214" not in blob and "41.8" not in blob


def test_cth01_risk_level_uses_frontend_enum(isolated_client):
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/CTH-01").get_json()
    sec = _sections(j)
    # 找到 split.side 里的 risks
    risks = None
    for s in sec["split"]["side"]:
        if s.get("type") == "risks":
            risks = s
    levels = {r["level"] for r in risks["items"]}
    assert "medium" not in levels  # 后端 medium 必须映射为前端 med
    assert levels <= {"high", "med", "low", "critical"}


# --------------------------- AI-01 真实绑定 + 诚实缺失 ---------------------------
def test_ai01_withholds_unscoped_evidence_and_execution_data(isolated_client, monkeypatch):
    cli, _ = isolated_client

    def fail_if_read(*_args, **_kwargs):
        raise AssertionError("AI-01 must not query a global Evidence or execution store")

    import experience_runtime
    from lumenis.shared.evidence import store as evidence_store

    monkeypatch.setattr(evidence_store, "get_stats", fail_if_read)
    monkeypatch.setattr(experience_runtime, "_ai_recent_tasks", fail_if_read)
    j = cli.get("/api/experience/screen/AI-01").get_json()

    assert j["bound"] is True
    k = _kpis(j)
    assert k["ai.anchored_evidence"]["value"] is None
    assert k["ai.anchored_evidence"]["state"] == "notcollected"
    assert k["ai.traceability"]["value"] is None
    assert k["ai.traceability"]["state"] == "notcollected"
    assert k["ai.review_queue"]["value"] is None
    assert k["ai.review_queue"]["state"] == "notcollected"
    assert "evidence_stats" not in j.get("truth", {})
    assert any("ai.anchored_evidence" == item["field"] for item in j["binding"]["blocked"])
    timeline = next(
        section
        for section in j["sections"]
        if section.get("type") == "split"
        for section in section.get("main", [])
        if section.get("type") == "timeline"
    )
    assert timeline["items"] == []
    assert not any("execution_id" in item for item in timeline["items"])


def test_ai01_traceability_not_fabricated(isolated_client):
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/AI-01").get_json()
    k = _kpis(j)
    # 无已完成执行链样本时不得编造可追溯率
    assert k["ai.traceability"]["value"] is None
    assert k["ai.traceability"]["state"] == "notcollected"


def test_ai01_provider_kpi_excludes_non_provider_components(isolated_client):
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/AI-01").get_json()
    providers = next(
        section["side"][0]["items"]
        for section in j["sections"]
        if section.get("type") == "split"
        and section.get("side")
        and section["side"][0].get("type") == "runtime"
    )
    assert all(item.get("kind") == "provider" for item in providers)
    assert {item["name"] for item in providers} == {"Owned AI Gateway"}


def test_ai01_composer_present_and_no_cot_leak(isolated_client):
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/AI-01").get_json()
    raw = [s for s in j["sections"] if s.get("type") == "raw"]
    assert raw and "data-ai-send" in raw[0]["html"]
    blob = __import__("json").dumps(j, ensure_ascii=False).lower()
    for leak in ("system prompt", "developer prompt", "chain-of-thought", "private cot"):
        assert leak not in blob


# --------------------------- 未绑定屏诚实回退 ---------------------------
def test_bmp05_is_canonically_bound(isolated_client):
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/BMP-05").get_json()
    assert j["bound"] is True and isinstance(j["sections"], list) and j["sections"]


# --------------------------- 身份不泄密 ---------------------------
def test_identity_has_no_secrets_or_abspath(isolated_client):
    cli, db_file = isolated_client
    j = cli.get("/api/experience/runtime/identity").get_json()
    import json
    blob = json.dumps(j, ensure_ascii=False)
    assert j["database"]["exists"] is True
    assert j["context"]["mode"] == "GLOBAL_ALL"
    assert j["context"]["domain_id"] is None
    assert j["context"]["subject_id"] is None
    assert j["subject"] is None
    assert j["domain"] is None
    assert db_file not in blob and ":\\" not in blob  # 不暴露绝对路径
    low = blob.lower()
    for secret in ("secret", "password", "api_key", "token", "cookie"):
        assert secret not in low


# --------------------------- AI intent 校验 ---------------------------
def test_ai_intent_validation(isolated_client):
    cli, _ = isolated_client
    assert cli.post("/api/experience/ai/intent", json={"task": ""}).status_code == 400
    assert cli.post("/api/experience/ai/intent", json={"task": "x" * 4001}).status_code == 400


# --------------------------- P1 传播层（experience_screens） ---------------------------
PROPAGATED = ["CTH-02", "CTH-03", "CTH-04", "CTH-05", "CTH-06", "CTH-07", "CTH-08",
              "CTH-09", "CTH-10", "AI-02", "AI-03", "AI-04", "AI-05",
              "SYS-01", "SYS-02", "SYS-03", "SYS-04", "SYS-05", "SYS-07", "SYS-08",
              "SH-02", "SH-03", "SH-04", "SH-05", "SH-06",
              "ACC-02", "ACC-03",
              "BMP-01", "BMP-02", "BMP-03", "BMP-04", "BMP-06", "BMP-07", "BMP-08", "BMP-09", "BMP-10"]


def test_all_propagated_screens_bound_with_sections(isolated_client):
    cli, _ = isolated_client
    for sid in PROPAGATED:
        headers = {} if sid == "SH-02" else {"X-Domain-Id": "CTH", "X-Product-Id": "CTH"} if sid.startswith("SH-") else {"X-Domain-Id": "BMP", "X-Product-Id": "ZBMP"} if sid.startswith("BMP-") else {}
        response = cli.get(f"/api/experience/screen/{sid}", headers=headers)
        assert response.status_code == 200, (sid, response.get_json())
        j = response.get_json()
        assert j["bound"] is True, sid
        assert isinstance(j["sections"], list) and j["sections"], sid
        assert j["sections"][0]["type"] == "head", sid


def test_sys01_status_is_not_a_numeric_kpi(isolated_client):
    """状态串不得进入数值 KPI（回归 NaN bug）：SYS-01 KPI 必须是真实整数。"""
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/SYS-01").get_json()
    for m in _sections(j)["kpis"]["items"]:
        assert isinstance(m["value"], int) and not isinstance(m["value"], bool), m["id"]
    # 总体状态字符串应在 runtime 状态条里
    rt = [s for s in j["sections"] if s.get("type") == "runtime"][0]
    overall = next(i for i in rt["items"] if i["name"] == "总体状态")
    assert overall["detail"] in ("healthy", "ok", "degraded", "unhealthy", "unknown")


def test_sys01_unavailable_health_counts_are_not_reported_as_zero(
    isolated_client, monkeypatch
):
    import runtime_guardian

    cli, _ = isolated_client
    monkeypatch.setattr(runtime_guardian, "legacy_health_check", lambda: {})

    response = cli.get("/api/experience/screen/SYS-01").get_json()

    kpis = _sections(response)["kpis"]["items"]
    assert [item["value"] for item in kpis] == [None, None, None]
    assert all(item["state"] == "offline" for item in kpis)
    assert _sections(response)["kpis"]["state"] == "offline"
    runtime = next(section for section in response["sections"] if section["type"] == "runtime")
    overall = next(item for item in runtime["items"] if item["name"] == "总体状态")
    assert overall["state"] == "offline"
    assert overall["detail"] == "unknown"


def test_sys01_returns_stable_read_only_runtime_observation_without_internal_values(
    isolated_client, monkeypatch
):
    import json
    import runtime_guardian

    cli, _ = isolated_client
    monkeypatch.setattr(
        runtime_guardian,
        "legacy_health_check",
        lambda: {
            "overall": "degraded",
            "workers": {"total": 2, "failed": 1},
            "dlq": {"total": 3},
            "circuit_breakers": {"worker": {"state": "open"}},
            "guardian_name": r"C:\\private\\runtime-token-should-not-leak",
            "timestamp": "2026-09-21T10:11:12Z",
        },
    )

    first = cli.get("/api/experience/screen/SYS-01").get_json()
    second = cli.get("/api/experience/screen/SYS-01").get_json()
    observation = first["runtime_observation"]

    assert observation == {
        "state": "ready",
        "source": "runtime_guardian.legacy_health_check",
        "captured_at": "2026-09-21T10:11:12+00:00",
        "trace_id": observation["trace_id"],
        "boundary": "read_only",
    }
    assert observation["trace_id"].startswith("sys01rt-")
    assert observation["trace_id"] == second["runtime_observation"]["trace_id"]
    assert observation["trace_id"] != ""
    assert "runtime-token-should-not-leak" not in json.dumps(first)
    assert "C:\\\\private" not in json.dumps(first)


def test_sys01_missing_runtime_observation_stays_unavailable(isolated_client, monkeypatch):
    import runtime_guardian

    cli, _ = isolated_client
    monkeypatch.setattr(runtime_guardian, "legacy_health_check", lambda: {})

    response = cli.get("/api/experience/screen/SYS-01").get_json()
    observation = response["runtime_observation"]

    assert observation["state"] == "unavailable"
    assert observation["source"] == "runtime_guardian.legacy_health_check"
    assert observation["captured_at"] is None
    assert observation["trace_id"] is None
    assert observation["boundary"] == "read_only"


def test_sys01_rejects_untrusted_observation_time_and_state_without_path_leaks(
    isolated_client, monkeypatch
):
    import json
    import runtime_guardian

    cli, _ = isolated_client
    private_value = r"D:\private\secret-value"
    monkeypatch.setattr(
        runtime_guardian,
        "legacy_health_check",
        lambda: {
            "overall": private_value,
            "timestamp": private_value,
            "guardian_name": private_value,
        },
    )

    response = cli.get("/api/experience/screen/SYS-01").get_json()
    observation = response["runtime_observation"]

    assert observation["state"] == "unavailable"
    assert observation["captured_at"] is None
    assert observation["trace_id"] is None
    assert private_value not in json.dumps(response)


def test_sys01_circuit_breaker_summary_counts_open_state(isolated_client, monkeypatch):
    import runtime_guardian

    cli, _ = isolated_client
    monkeypatch.setattr(
        runtime_guardian,
        "legacy_health_check",
        lambda: {
            "overall": "degraded",
            "workers": {"total": 1, "failed": 0},
            "dlq": {"total": 0},
            "circuit_breakers": {
                "open-worker": {"state": "open"},
                "closed-worker": {"state": "closed"},
            },
            "reaper_running": True,
            "guardian_name": "test-guardian",
            "timestamp": "2026-09-20T00:00:00",
        },
    )

    response = cli.get("/api/experience/screen/SYS-01").get_json()

    runtime = next(section for section in response["sections"] if section["type"] == "runtime")
    breaker = next(item for item in runtime["items"] if item["name"] == "熔断器")
    assert breaker["state"] == "bad"
    assert breaker["detail"] == "open=1 · registered=2"


def test_cth07_chart_series_are_real_14d(isolated_client):
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/CTH-07").get_json()
    chart = [s for s in j["sections"] if s.get("type") == "chart"][0]
    assert len(chart["labels"]) == 14
    # This fixture contains only legacy rows, not admitted signed Canonical observations.
    # A calendar day without an eligible observation is unknown, never a fabricated zero.
    for series in chart["series"]:
        assert len(series["data"]) == 14
        assert series["data"] == [None] * 14
    assert j["temporal_metrics"]["contributions"] == []


def test_cth07_signed_observations_keep_missing_null_and_observed_zero(isolated_client, monkeypatch):
    import json
    import sqlite3
    from tests.test_cth_temporal_metrics import _persist_signed_record
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_KEY_RING", json.dumps({"cth-screen-fixture": "synthetic-disposable-only"}))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "cth-screen-fixture")
    cli, db_path = isolated_client
    today = dt.date.today().isoformat()
    with sqlite3.connect(db_path) as con:
        _persist_signed_record(con, source_id="screen-signed-positive", subject_id="SUBJ-A",
                               publish_datetime=today, sentiment="positive", risk_level="low")
        before_read = list(con.iterdump())
    response = cli.get("/api/experience/screen/CTH-07")
    assert response.status_code == 200
    payload = response.get_json()
    chart = next(s for s in payload["sections"] if s.get("type") == "chart")
    assert len(chart["labels"]) == 14
    by_metric = {s["metric"]: s["data"] for s in chart["series"]}
    assert by_metric["total"] == [None] * 13 + [1]
    assert by_metric["negative"] == [None] * 13 + [0]
    assert by_metric["high"] == [None] * 13 + [0]
    contributions = payload["temporal_metrics"]["contributions"]
    assert len(contributions) == 1
    assert contributions[0]["source_id"] == "screen-signed-positive"
    assert contributions[0]["scope_evidence"]["integrity"]["verified"] is True
    assert contributions[0]["scope_evidence"]["integrity"]["lineage_verified"] is True
    with sqlite3.connect(db_path) as con:
        assert list(con.iterdump()) == before_read, "read-only screen must not mutate stored evidence"


def test_ready_kpis_have_value_nonready_are_none(isolated_client):
    """状态契约：ready 必有标量值；非 ready 必须 value=None（不造假）。"""
    cli, _ = isolated_client
    import json
    for sid in ["CTH-01", "AI-01"] + PROPAGATED:
        headers = {} if sid == "SH-02" else {"X-Domain-Id": "CTH", "X-Product-Id": "CTH"} if sid.startswith("SH-") else {"X-Domain-Id": "BMP", "X-Product-Id": "ZBMP"} if sid.startswith("BMP-") else {}
        response = cli.get(f"/api/experience/screen/{sid}", headers=headers)
        assert response.status_code == 200, (sid, response.get_json())
        j = response.get_json()
        for sec in j["sections"]:
            if sec.get("type") != "kpis":
                continue
            for m in sec["items"]:
                if m["state"] == "ready":
                    assert m["value"] is not None, (sid, m["id"])
                    assert not isinstance(m["value"], (dict, list)), (sid, m["id"])
                elif m["state"] == "empty":
                    assert m["value"] == 0, (sid, m["id"])
                else:
                    assert m["value"] is None, (sid, m["id"])
        # 任何已绑定屏都不得泄漏原型伪造大数字
        assert "38214" not in json.dumps(j, ensure_ascii=False), sid


def test_bmp11_is_canonically_bound(isolated_client):
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/BMP-11").get_json()
    assert j["bound"] is True and isinstance(j["sections"], list) and j["sections"]


# --------------------------- 第二批传播：真实只读源回归 ---------------------------
def test_sys02_collector_status_real_platforms(isolated_client):
    """SYS-02 采集器：17 平台真实状态表；KPI 为整数；未连通如实 MISSING，不伪造 ACTIVE。"""
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/SYS-02").get_json()
    assert j["bound"] is True
    sec = {s["type"]: s for s in j["sections"]}
    tbl = sec["table"]
    assert len(tbl["rows"]) == 16  # collector_status_api.PLATFORMS
    for m in sec["kpis"]["items"]:
        assert isinstance(m["value"], int) and not isinstance(m["value"], bool)
    # 隔离环境无 cookie：ACTIVE 必须为 0，绝不造假
    active = next(m for m in sec["kpis"]["items"] if "ACTIVE" in m["label"])
    assert active["value"] == 0


def test_sys08_logs_hide_absolute_path(isolated_client):
    """SYS-08 日志：只显文件名，不暴露 log_dir 绝对路径。"""
    import json
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/SYS-08").get_json()
    assert j["bound"] is True
    blob = json.dumps(j, ensure_ascii=False)
    assert ":\\" not in blob and "/logs" not in blob


def test_sh04_report_catalog_real(isolated_client):
    """SH-04 报告目录：cth/zbmp 真实报告类型行，且标注导出 EFFECT 未造假下载。"""
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/SH-04").get_json()
    sec = {s["type"]: s for s in j["sections"]}
    rows = sec["table"]["rows"]
    assert len(rows) >= 10
    assert {r["领域"] for r in rows} >= {"cth", "zbmp"}


def test_sh01_content_evidence_detail_is_real_and_sanitized(content_client):
    import json
    import experience_runtime
    from tests.test_content_scoped_patterns import create, HEADERS
    cli, ws = content_client
    ws['app'].register_blueprint(experience_runtime.experience_bp)
    source, made = create(content_client)
    response = cli.get('/api/experience/screen/SH-01', headers=HEADERS)
    assert response.status_code == 200, response.get_json()
    table = next(s for s in response.get_json()['sections'] if s['type'] == 'table')
    assert table['action']['id'] == 'open-content-evidence'
    assert table['action']['target'] == made['evidence_id']
    detail = cli.get('/api/experience/content/evidence/' + made['evidence_id'], headers=HEADERS)
    assert detail.status_code == 200, detail.get_json()
    payload = detail.get_json()
    assert payload['source'] == 'runtime' and payload['ai_is_derivative'] is True
    assert payload['evidence']['output'] == made['candidate']
    text = json.dumps(payload)
    assert 'input_json' not in text and 'prompt' not in text.lower()
    assert cli.get('/api/experience/content/evidence/' + made['evidence_id'], headers={'X-Domain-Id':'BMP','X-Product-Id':'ZBMP'}).status_code >= 400
    assert cli.get('/api/experience/content/evidence/not-valid', headers=HEADERS).status_code == 400



def test_bmp10_uses_curated_events_dict(isolated_client, monkeypatch):
    """BMP-10 必须正确解包 get_events_curated 的 {'featured':[...]}（回归把 dict 当 list 的缺陷）。"""
    cli, _ = isolated_client
    import database
    _, db_path = isolated_client
    scope = _admit_existing_note(db_path, monkeypatch, "n1", bmp=True)
    assert database.upsert_event({"event_key":database._event_scope_token(scope)+".bmp-test", "title":"Signed brand event", "status":"active"},scope=scope,mentions=[{"source_type":"note","source_id":"n1"}]) > 0
    j = cli.get("/api/experience/screen/BMP-10").get_json()
    sec = {s["type"]: s for s in j["sections"]}
    ev = sec["events"]
    assert len(ev["items"]) == 1
    with database.get_db() as connection:
        reference = connection.execute("SELECT scope_evidence_ref FROM events WHERE id=?", (ev["items"][0]["event_id"],)).fetchone()[0]
    assert ev["items"][0]["evidence"] == "EV-" + str(reference)
    assert ev["items"][0]["evidence_state"] == "REFERENCED"


def test_sys07_owasp_checks_real(isolated_client):
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/SYS-07").get_json()
    sec = {s["type"]: s for s in j["sections"]}
    assert len(sec["table"]["rows"]) == 5  # ai_governance 启用 5 项 OWASP 防护


# --------------------------- 第三批传播：总览/目录/配额/评估/学习/本地设置 ---------------------------
def test_bmp02_brand_directory_real(isolated_client):
    """BMP-02 多品牌目录：真实策展零售目录（194 品牌 / 13 业态），非伪造。"""
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/BMP-02").get_json()
    assert j["bound"] is True and j["truth"]["total_brands"] == 194
    sec = {s["type"]: s for s in j["sections"]}
    assert len(sec["table"]["rows"]) == 13


def test_bmp07_campaign_quota_integer(isolated_client):
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/BMP-07").get_json()
    sec = {s["type"]: s for s in j["sections"]}
    for m in sec["kpis"]["items"]:
        assert isinstance(m["value"], int) and not isinstance(m["value"], bool)


def test_bmp09_evaluation_status_distribution(isolated_client):
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/BMP-09").get_json()
    sec = {s["type"]: s for s in j["sections"]}
    tables = sec.get("table") if isinstance(sec.get("table"), list) else [sec["table"]]
    # 第一张表为 pass/warn/fail/unknown 四态
    first = [t for t in j["sections"] if t["type"] == "table"][0]
    assert len(first["rows"]) == 4


def test_sys05_is_frontend_local_only(isolated_client):
    """SYS-05 设置为纯前端本地偏好：无外部依赖、显式 backend_required=False。"""
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/SYS-05").get_json()
    assert j["bound"] is True and j["truth"]["backend_required"] is False
    form = [s for s in j["sections"] if s["type"] == "form"][0]
    assert len(form["fields"]) == 4


def test_acc02_subject_profiles_real(isolated_client):
    import subject_rules
    import subject_context
    from subject_registry import list_subjects
    cli, _ = isolated_client
    subject_context.clear_thread_context()
    payload = cli.get("/api/experience/screen/ACC-02").get_json()
    assert payload["bound"] is True and payload["truth"]["active_brand"] == ""
    rows = next(section["rows"] for section in payload["sections"] if section["type"] == "table")
    assert len(rows) == len(subject_rules.BRAND_PROFILES) + len(list_subjects())
    context = subject_context.SubjectContext(subject_id="FOCUS-TEST", brand_key="guangzhou_taikoo_hui", product_id="CTH")
    subject_context.set_thread_context(context)
    try:
        focused = cli.get("/api/experience/screen/ACC-02").get_json()
        assert focused["truth"]["active_brand"] == "guangzhou_taikoo_hui"
    finally:
        subject_context.clear_thread_context()


def test_bmp03_missing_table_honest_not_fake(isolated_client, monkeypatch):
    cli, _ = isolated_client
    import kos_engine
    result = cli.get("/api/experience/screen/BMP-03").get_json()
    assert result["bound"] is True
    assert result["truth"]["data_state"] == "EMPTY"
    assert result["truth"]["source_count"] == 0
    assert result["truth"]["insight_state"] == "NOT_COMPUTED"
    assert result["truth"]["legacy_asset_scope"] == "UNKNOWN_NOT_ASSIGNED"
    def unavailable(binding):
        raise OSError("isolated source storage unavailable")
    monkeypatch.setattr(kos_engine, "_read_scoped_canonical_material", unavailable)
    response = cli.get("/api/experience/screen/BMP-03")
    assert response.status_code == 503
    assert response.get_json()["bound"] is False
    assert "source_count" not in response.get_json()


def test_platform_collection_is_cth_owned_and_bmp_read_only(isolated_client, monkeypatch):
    """CTH owns the actionable form; BMP receives only the shared read-only surface."""
    cli, _ = isolated_client
    from lumenis.system.collector.adapters import secondary_collection as collection

    monkeypatch.setattr(collection, "get_collection_surface", lambda: {
        "ok": True,
        "paused_platforms": ["xiaohongshu_cn"],
        "out_of_scope_platforms": [],
        "primary_collection": {
            "platform": "xiaohongshu", "name": "小红书（香港账号）",
            "status": "READY", "entry_label": "既有主采集链路 · 此表只读展示",
            "manual_collection_enabled": True, "form_selectable": False,
            "health": {"ready": True, "can_attempt": True},
            "runtime": {"status": "READY", "observed": True},
            "last_run": {
                "state": "SUCCESS", "fetched": 4, "accepted": None,
                "started_at": "2026-09-15 08:55:00", "finished_at": "2026-09-15 09:00:00",
            },
        },
        "platforms": [
            {
                "platform": "web_rss", "name": "Web RSS",
                "manual_collection_enabled": True, "status": "SUCCESS",
                "health": {"ready": True, "can_attempt": True}, "last_run": None,
            },
            {
                "platform": "douyin", "name": "抖音",
                "manual_collection_enabled": True, "status": "NOT_CONFIGURED",
                "health": {"ready": False, "can_attempt": False}, "last_run": None,
            },
            {
                "platform": "kuaishou", "name": "快手",
                "manual_collection_enabled": False, "status": "NOT_SUPPORTED",
                "health": {"ready": False, "can_attempt": False}, "last_run": None,
            },
        ],
    })

    cth = cli.get("/api/experience/screen/CTH-03").get_json()
    cth_surface = next(s for s in cth["sections"] if s["type"] == "platforms")
    cth_rows = {row["platform_id"]: row for row in cth_surface["items"]}
    assert cth_surface["consumer"] == "CTH"
    assert cth_surface["can_trigger"] is True
    assert cth_surface["endpoint"].endswith("/cth/platform-collection/search")
    assert cth_rows["web_rss"]["can_attempt"] is True
    assert cth_rows["web_rss"]["schedule"] == "可人工触发"
    assert cth_rows["xhs_hk_primary"]["status"] == "驻场状态已验证"
    assert cth_rows["xhs_hk_primary"]["schedule"] == "既有主采集链路 · 此表只读展示"
    assert cth_rows["xhs_hk_primary"]["can_attempt"] is True
    assert cth_rows["xhs_hk_primary"]["form_selectable"] is False
    assert cth_rows["xhs_hk_primary"]["counts"] == "4 / —"
    assert cth_rows["xhs_hk_primary"]["evidence"] == "既有采集日志"
    assert cth_rows["douyin"]["can_attempt"] is False
    assert cth_rows["douyin"]["schedule"] == "需配置 / 验证"
    assert cth_rows["douyin"]["status"] == "未配置运行方式"
    assert cth_rows["kuaishou"]["manual_collection_enabled"] is False

    bmp = cli.get("/api/experience/screen/BMP-03").get_json()
    bmp_surface = next(s for s in bmp["sections"] if s["type"] == "platforms")
    assert bmp_surface["consumer"] == "BMP"
    assert bmp_surface["can_trigger"] is False
    assert bmp_surface["endpoint"] == ""
    assert bmp_surface["items"] == []  # Legacy CTH rows are not authorized BMP observations.
    assert bmp_surface["collection_runtime"]["state"] == "UNKNOWN"
    assert bmp_surface["source_count"] == 0
    assert bmp_surface["collection_owner"] == "CTH"
    _, db_path = isolated_client
    _admit_existing_note(db_path, monkeypatch, "n1", bmp=True)
    observed = cli.get("/api/experience/screen/BMP-03").get_json()
    positive = next(s for s in observed["sections"] if s["type"] == "platforms")
    assert positive["source_count"] == 1
    assert positive["items"][0]["source_references"][0]["source_id"] == "n1"
    assert positive["items"][0]["can_attempt"] is False
    assert positive["collection_runtime"]["state"] == "UNKNOWN"


def test_bmp04_propagation_three_dashboards(isolated_client):
    """BMP-04 传播分析：品牌/产品/行业三类看板真实只读（空库 0 诚实）。"""
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/BMP-04").get_json()
    assert j["bound"] is True and j["truth"]["total_events"] == 0
    tbl = [s for s in j["sections"] if s["type"] == "table"][0]
    assert len(tbl["rows"]) == 3


def test_screen_meta_covers_44_screens():
    import json
    path = os.path.join(REPO_ROOT, "contracts", "experience", "screen_meta.json")
    meta = json.load(open(path, encoding="utf-8"))
    assert len(meta) == 44
    for sid in ["AI-01", "CTH-01", "SH-01"]:
        assert meta[sid]["title"]


def _cth01_trend_section(payload):
    split = next(section for section in payload["sections"]
                 if section.get("type") == "split")
    chart = next(section for section in split.get("main", [])
                 if section.get("type") == "chart")
    assert chart.get("title") == "近 14 日负面声量 / 高风险"
    return chart


def test_cth01_complete_empty_sample_days_are_zero(isolated_client, monkeypatch):
    import database

    monkeypatch.setattr(
        database, "get_scoped_event_source_rows",
        lambda *_args, **_kwargs: {
            "sources": [], "truncated": False, "rejected_count": 0,
        },
    )
    cli, _ = isolated_client
    payload = cli.get("/api/experience/screen/CTH-01").get_json()
    chart = _cth01_trend_section(payload)

    assert chart["series"][0]["data"] == [0] * 14
    assert chart["series"][1]["data"] == [0] * 14
    assert "已核验样本" in chart["sub"] and "完整读取且无样本为0" in chart["sub"]


def test_cth01_unknown_classification_stays_unknown(isolated_client, monkeypatch):
    import database

    unknown_row = {
        "source_id": "unknown-classification", "source_type": "note",
        "publish_date": (dt.datetime.now(dt.timezone.utc).astimezone().date() - dt.timedelta(days=1)).isoformat(),
        "sentiment": None, "risk_level": None,
    }
    monkeypatch.setattr(
        database, "get_scoped_event_source_rows",
        lambda *_args, **_kwargs: {
            "sources": [unknown_row], "truncated": False, "rejected_count": 0,
        },
    )
    cli, _ = isolated_client
    payload = cli.get("/api/experience/screen/CTH-01").get_json()
    chart = _cth01_trend_section(payload)

    assert chart["series"][0]["data"][-2] is None
    assert chart["series"][1]["data"][-2] is None
    assert chart["series"][0]["data"][-1] == 0
    assert chart["series"][1]["data"][-1] == 0


def test_cth01_incomplete_trend_coverage_stays_unknown(isolated_client, monkeypatch):
    import database

    monkeypatch.setattr(
        database, "get_scoped_event_source_rows",
        lambda *_args, **_kwargs: {
            "sources": [], "truncated": True, "rejected_count": 0,
        },
    )
    cli, _ = isolated_client
    payload = cli.get("/api/experience/screen/CTH-01").get_json()
    chart = _cth01_trend_section(payload)

    assert chart["series"][0]["data"] == [None] * 14
    assert chart["series"][1]["data"] == [None] * 14


def test_disposable_fixture_has_current_owner_migration(isolated_client):
    import sqlite3
    from lumenis.shared.database import migrations
    _, db_path = isolated_client
    with sqlite3.connect(db_path) as con:
        assert migrations.get_current_version(con) == migrations.CURRENT_VERSION
        assert 'scope_status' in {row[1] for row in con.execute('PRAGMA table_info(events)')}
        assert {'integrity_version', 'integrity_algorithm', 'integrity_key_id', 'integrity_digest'} <= {
            row[1] for row in con.execute('PRAGMA table_info(app_evidence_records)')}
        assert con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='lumenis_subject_registry'").fetchone()


def test_bmp03_legacy_cth_rows_do_not_become_market_observations(isolated_client):
    import sqlite3
    cli, db_path = isolated_client
    with sqlite3.connect(db_path) as con:
        assert con.execute('SELECT COUNT(*) FROM notes').fetchone()[0] == 5
        before = list(con.iterdump())
    response = cli.get('/api/experience/screen/BMP-03')
    assert response.status_code == 200, response.get_json()
    result = response.get_json()
    assert result['source_observation_contract'] == 'lumenis.bmp03-source-observations.v1'
    assert result['source_observations'] == []
    assert result['truth']['insight_state'] == 'NOT_COMPUTED'
    assert result['truth']['legacy_asset_scope'] == 'UNKNOWN_NOT_ASSIGNED'
    surface = next(section for section in result['sections'] if section['type'] == 'platforms')
    assert surface['items'] == []
    assert surface['can_trigger'] is False
    assert surface['collection_runtime']['state'] == 'UNKNOWN'
    with sqlite3.connect(db_path) as con:
        assert list(con.iterdump()) == before


def test_bmp09_actual_report_version_and_wrong_actor_denial(report_client):
    from tests.test_bmp09_request_binding import save, accounts, ids, PATH
    http, ws = report_client
    one, two = accounts(ws)
    made = save(ws, actor={'id':1,'role':'owner'}, key='consumer-report')
    response = http.get(PATH, headers=one)
    assert ids(response) == [made['artifact']['artifact_id']]
    row = response.get_json()['saved_artifacts'][0]
    assert row['version'] == made['document']['version']
    assert row['assessment'] == 'NOT_ESTABLISHED_BY_STORAGE'
    assert ids(http.get(PATH, headers=two)) == []
    ws['repo'].execute("UPDATE v4_users SET status='disabled' WHERE id=1")
    assert http.get(PATH, headers=one).status_code >= 400
