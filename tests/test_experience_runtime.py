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

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


@pytest.fixture()
def isolated_client(tmp_path, monkeypatch):
    db_file = tmp_path / "isolated_monitor.db"
    monkeypatch.setenv("ZBC_DB_PATH", str(db_file))
    monkeypatch.setenv("ZBC_ACTIVE_BRAND", "guangzhou_taikoo_hui")

    import database
    importlib.reload(database)  # 让 DB_PATH 取到隔离路径
    database.DB_PATH = str(db_file)
    database.init_db()

    import evidence_store
    evidence_store.DB_PATH = str(db_file)
    # account.models resolves db_paths.main_db_path() at call time on current main;
    # the ZBC_DB_PATH fixture above is the canonical isolation contract.

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
        c.execute(
            """CREATE TABLE IF NOT EXISTS app_evidence_records(
               id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, project TEXT, product TEXT,
               feature_id TEXT, level TEXT, result TEXT, account TEXT, env TEXT,
               actual TEXT, created_at TEXT)"""
        )
        c.executemany(
            """INSERT INTO app_evidence_records(source,feature_id,level,result,account,actual,created_at)
               VALUES(?,?,?,?,?,?,datetime('now','localtime'))""",
            [("unit", "FUNC-RISK-01", "feature", "pass", "acc1", "risk computed"),
             ("integration", "EVENT-GRAPH", "feature", "pass", "acc1", "event chain")],
        )

    import experience_runtime
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(experience_runtime.experience_bp)
    return app.test_client(), str(db_file)


def _sections(j):
    return {s.get("type"): s for s in j["sections"]}


def _kpis(j):
    return {m["id"]: m for m in _sections(j)["kpis"]["items"]}


# --------------------------- 外壳托管 ---------------------------
def test_shell_serves_and_injects_runtime(isolated_client):
    cli, _ = isolated_client
    r = cli.get("/experience/")
    assert r.status_code == 200
    assert b"assets/runtime.js" in r.data
    assert "<title>序境 LUMENIS · Production</title>".encode() in r.data
    r2 = cli.get("/experience/assets/runtime.js")
    assert r2.status_code == 200 and r2.content_length and r2.content_length > 1000
    assert b"lum-production-truth-fence" in r2.data
    assert b"/api/auth/config" in r2.data
    assert b"async function apiFetch" in r2.data
    assert b"const initialId" in r2.data
    assert b'.lum-qa-bar{display:none!important}' in r2.data
    assert b'.lum-page[data-source="prototype"]' in r2.data
    assert b"RUNTIME_UNAVAILABLE" in r2.data
    r3 = cli.get("/experience/assets/components.css")
    assert r3.status_code == 200
    assert b".lum-drawer.is-open" in r3.data
    assert b"pointer-events:none" in r3.data
    r4 = cli.get("/experience/assets/components.js")
    assert r4.status_code == 200
    assert b"const host = $('.lum-app') || document.body" in r4.data
    assert b"host.appendChild(d)" in r4.data
    r5 = cli.get("/experience/assets/app.js")
    assert r5.status_code == 200
    assert b"const routeDomain = id.startsWith('BMP-')" in r5.data
    assert b"global.LumShell.renderSubject()" in r5.data
    r6 = cli.get("/experience/assets/sections.js")
    assert r6.status_code == 200
    assert b"${m.evidenceId ?" in r6.data


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


def test_cth01_real_metrics_match_isolated_db(isolated_client):
    cli, _ = isolated_client
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
def test_ai01_anchored_evidence_real(isolated_client):
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/AI-01").get_json()
    assert j["bound"] is True
    k = _kpis(j)
    assert k["ai.anchored_evidence"]["value"] == 2
    assert k["ai.anchored_evidence"]["state"] == "ready"


def test_ai01_traceability_not_fabricated(isolated_client):
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/AI-01").get_json()
    k = _kpis(j)
    # 无已完成执行链样本时不得编造可追溯率
    assert k["ai.traceability"]["value"] is None
    assert k["ai.traceability"]["state"] == "notcollected"


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
        j = cli.get(f"/api/experience/screen/{sid}").get_json()
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


def test_cth07_chart_series_are_real_14d(isolated_client):
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/CTH-07").get_json()
    chart = [s for s in j["sections"] if s.get("type") == "chart"][0]
    assert len(chart["labels"]) == 14
    for s in chart["series"]:
        assert len(s["data"]) == 14 and all(isinstance(v, int) for v in s["data"])


def test_ready_kpis_have_value_nonready_are_none(isolated_client):
    """状态契约：ready 必有标量值；非 ready 必须 value=None（不造假）。"""
    cli, _ = isolated_client
    import json
    for sid in ["CTH-01", "AI-01"] + PROPAGATED:
        j = cli.get(f"/api/experience/screen/{sid}").get_json()
        for sec in j["sections"]:
            if sec.get("type") != "kpis":
                continue
            for m in sec["items"]:
                if m["state"] == "ready":
                    assert m["value"] is not None, (sid, m["id"])
                    assert not isinstance(m["value"], (dict, list)), (sid, m["id"])
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
    assert len(tbl["rows"]) == 17  # collector_status_api.PLATFORMS
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


def test_sh01_content_evidence_detail_is_real_and_sanitized(isolated_client):
    """SH-01 用户动作读取真实 Evidence，同时不把 prompt/input 上送到浏览器。"""
    import content_generation
    import json
    cli, _ = isolated_client
    content_generation.init_db()
    with content_generation._get_conn() as conn:
        conn.execute(
            """INSERT INTO content_generation_evidence
               (evidence_id,content_type,input_json,prompt,output_json,provider,model,status,confidence,iteration,created_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,datetime('now','localtime'))""",
            ("CGE-TEST-SH01", "social_post", json.dumps({"prompt": "SECRET BRIEF"}),
             "SECRET SYSTEM PROMPT", json.dumps({"headline": "真实草稿"}, ensure_ascii=False),
             "ollama", "local", "generated", 0.91, 1),
        )
        conn.commit()

    screen = cli.get("/api/experience/screen/SH-01").get_json()
    table = next(s for s in screen["sections"] if s["type"] == "table")
    assert table["action"]["id"] == "open-content-evidence"
    assert table["action"]["target"] == "CGE-TEST-SH01"

    response = cli.get("/api/experience/content/evidence/CGE-TEST-SH01")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["source"] == "runtime" and payload["ai_is_derivative"] is True
    assert payload["evidence"]["output"]["headline"] == "真实草稿"
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "SECRET BRIEF" not in serialized and "input_json" not in serialized and "prompt" not in serialized.lower()

    assert cli.get("/api/experience/content/evidence/not-valid").status_code == 400


def test_bmp10_uses_curated_events_dict(isolated_client):
    """BMP-10 必须正确解包 get_events_curated 的 {'featured':[...]}（回归把 dict 当 list 的缺陷）。"""
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/BMP-10").get_json()
    sec = {s["type"]: s for s in j["sections"]}
    ev = sec["events"]
    assert len(ev["items"]) == 1 and ev["items"][0]["evidence"].startswith("EV:")


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
    """ACC-02 主体选择：真实配置主体（6 个 BRAND_PROFILES）。"""
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/ACC-02").get_json()
    assert j["bound"] is True and j["truth"]["active_brand"]
    tbl = [s for s in j["sections"] if s["type"] == "table"][0]
    assert len(tbl["rows"]) == 6


def test_bmp03_missing_table_honest_not_fake(isolated_client):
    """BMP-03 情报表缺失时显式未采集，total=None，不造假 0。"""
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/BMP-03").get_json()
    assert j["bound"] is True and j["truth"]["table_exists"] is False
    kpi = [s for s in j["sections"] if s["type"] == "kpis"][0]["items"][0]
    assert kpi["value"] is None and kpi["state"] == "notcollected"


def test_bmp04_propagation_three_dashboards(isolated_client):
    """BMP-04 传播分析：品牌/产品/行业三类看板真实只读（空库 0 诚实）。"""
    cli, _ = isolated_client
    j = cli.get("/api/experience/screen/BMP-04").get_json()
    assert j["bound"] is True and j["truth"]["total_events"] == 0
    tbl = [s for s in j["sections"] if s["type"] == "table"][0]
    assert len(tbl["rows"]) == 3


def test_screen_meta_covers_44_screens():
    import json
    path = os.path.join(REPO_ROOT, "experience_v2", "10_prototype", "data", "screen_meta.json")
    meta = json.load(open(path, encoding="utf-8"))
    assert len(meta) == 44
    for sid in ["AI-01", "CTH-01", "SH-01"]:
        assert meta[sid]["title"]
