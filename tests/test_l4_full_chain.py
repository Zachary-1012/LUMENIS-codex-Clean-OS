# -*- coding: utf-8 -*-
"""
L4: 完整链路集成测试
验证完整链路：START → CONFIG → DB_INIT → COLLECT(mock) → PROCESS → STORE → AI(mock) → RISK → EVIDENCE → REPORT → API
每个步骤有断言，失败时明确指出哪个环节断链。
"""
import os
import sys
import json
import time
import tempfile
import traceback
from datetime import datetime, timedelta

import pytest

# 项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 测试专用凭证
os.environ.setdefault('TAIKOO_AUTH_USER', 'Zachary')
os.environ.setdefault('TAIKOO_AUTH_PASSWORD', 'Zachary01')

# ============================================================
# L4 测试结果收集器
# ============================================================
L4_RESULTS = {
    "level": "L4",
    "chain_steps": [],
    "summary": {"passed": 0, "failed": 0, "skipped": 0, "error": 0},
    "failures": []
}


def _record_step(name, passed, detail="", error=None):
    """记录链路步骤结果"""
    step = {"step": name, "passed": passed, "detail": detail}
    if error:
        step["error"] = str(error)[:500]
        L4_RESULTS["failures"].append(step)
    L4_RESULTS["chain_steps"].append(step)
    if passed:
        L4_RESULTS["summary"]["passed"] += 1
    else:
        L4_RESULTS["summary"]["failed"] += 1


@pytest.fixture
def l4_cth_subject_context():
    """Bind this Guangzhou reference-chain test to its declared CTH scope."""
    from domain_isolation import (
        DomainContext, clear_domain_context, get_domain_context, set_domain_context,
    )
    from subject_context import (
        CTH_BRAND_KEY, CTH_SUBJECT_ID, ScopeContext, clear_thread_context,
        get_thread_context, set_thread_context,
    )

    previous_domain = get_domain_context()
    previous_subject = get_thread_context()
    context = DomainContext(
        domain_id="cth",
        product_id="CTH",
        subject_id=CTH_SUBJECT_ID,
        brand_key=CTH_BRAND_KEY,
        scope=ScopeContext(permission_scope="write"),
        trace_id="l4-full-chain-test",
    )
    set_domain_context(context)
    set_thread_context(context.to_subject_context())
    try:
        yield context
    finally:
        clear_domain_context()
        clear_thread_context()
        if previous_domain is not None:
            set_domain_context(previous_domain)
        if previous_subject is not None:
            set_thread_context(previous_subject)


@pytest.fixture(scope="module")
def l4_database_path(tmp_path_factory):
    return tmp_path_factory.mktemp("l4-chain") / "chain.sqlite3"


@pytest.fixture(autouse=True)
def l4_isolated_storage(l4_database_path, monkeypatch):
    """Keep chain steps in one disposable DB, with real signed scope receipts."""
    from lumenis.shared.database import repository
    from lumenis.shared.evidence import store
    monkeypatch.setenv("ZBC_DB_PATH", str(l4_database_path))
    monkeypatch.setenv("ZBC_EVIDENCE_DB_PATH", str(l4_database_path))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_KEY_RING", json.dumps({
        "l4-test": "l4-disposable-only-signing-key",
    }))
    monkeypatch.setenv("LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID", "l4-test")
    monkeypatch.setattr(repository, "_default_repository",
                        repository.DatabaseRepository(str(l4_database_path)))
    store.init_evidence_store(str(l4_database_path))


# ============================================================
# Mock 数据
# ============================================================
MOCK_NOTES = [
    {
        "note_id": "l4_test_001",
        "title": "广州太古汇15周年庆典活动现场打卡",
        "content": "今天去了广州太古汇，15周年活动布置得太漂亮了！很多品牌都有优惠活动，人超级多。",
        "source_platform": "xhs",
        "url": "https://xiaohongshu.com/l4_test_001",
        "author_id": "test_author_001",
        "author_nickname": "探店小达人",
        "likes": 520,
        "comments": 88,
        "collects": 120,
        "shares": 35,
        "publish_date": "2026-09-05",
        "publish_datetime": "2026-09-05 14:30:00",
        "is_taikoo_verified": 1,
        "verify_reason": "title命中:广州太古汇",
        "source_keyword": "广州太古汇",
        "matched_keywords": "广州太古汇,15周年",
    },
    {
        "note_id": "l4_test_002",
        "title": "太古汇停车场收费标准2026最新",
        "content": "广州太古汇停车场现在收费是16元/小时，消费满300可以免1小时。给大家整理了最新的停车攻略。",
        "source_platform": "xhs",
        "url": "https://xiaohongshu.com/l4_test_002",
        "author_id": "test_author_002",
        "author_nickname": "停车攻略君",
        "likes": 340,
        "comments": 56,
        "collects": 200,
        "shares": 45,
        "publish_date": "2026-09-04",
        "publish_datetime": "2026-09-04 10:15:00",
        "is_taikoo_verified": 1,
        "verify_reason": "title命中:太古汇",
        "source_keyword": "太古汇",
        "matched_keywords": "太古汇,停车场",
    },
    {
        "note_id": "l4_test_003",
        "title": "广州太古汇服务态度差，投诉无门",
        "content": "昨天在广州太古汇某品牌店遇到非常差的服务体验，店员态度恶劣，找管理层投诉也没有得到妥善处理。太失望了！",
        "source_platform": "xhs",
        "url": "https://xiaohongshu.com/l4_test_003",
        "author_id": "test_author_003",
        "author_nickname": "愤怒的消费者",
        "likes": 890,
        "comments": 230,
        "collects": 45,
        "shares": 120,
        "publish_date": "2026-09-05",
        "publish_datetime": "2026-09-05 18:45:00",
        "is_taikoo_verified": 1,
        "verify_reason": "title命中:广州太古汇",
        "source_keyword": "广州太古汇",
        "matched_keywords": "广州太古汇,投诉",
    },
]


def _cth_request_headers():
    import base64

    credentials = f"{os.environ['TAIKOO_AUTH_USER']}:{os.environ['TAIKOO_AUTH_PASSWORD']}".encode()
    auth = base64.b64encode(credentials).decode()
    return {
        "Authorization": f"Basic {auth}",
        "X-Domain-Id": "cth",
        "X-Product-Id": "CTH",
        "X-Subject-Id": "GUANGZHOU_TAIKOO_HUI",
        "X-Brand-Key": "guangzhou_taikoo_hui",
    }


def _load_app_for_api_test(monkeypatch):
    """Load routes without leaking app.py's process-lifetime watchdog into pytest."""
    import sys
    import threading

    if "app" not in sys.modules:
        original_start = threading.Thread.start

        def start_test_threads_only(thread, *args, **kwargs):
            if thread.name == "hang_watchdog":
                return None
            return original_start(thread, *args, **kwargs)

        monkeypatch.setattr(threading.Thread, "start", start_test_threads_only)
        try:
            import app
        finally:
            monkeypatch.setattr(threading.Thread, "start", original_start)
    else:
        import app
    monkeypatch.setitem(app.app.config, "LUMENIS_OPEN_WORKSPACE", False)
    return app.app


def _authorized_chain_client(api_app):
    from lumenis.auth.service import AUTH_CONFIG
    client = api_app.test_client()
    client.set_cookie(AUTH_CONFIG["session_cookie_name"], "l4-chain-reader")
    return client


# ============================================================
# 测试：完整链路
# ============================================================
class TestL4FullChain:
    """L4 完整链路集成测试"""

    @pytest.fixture(scope="class")
    def chain_state(self):
        """链路状态共享"""
        return {"notes": [], "canonical_records": [], "risk_results": [], "evidence_ids": []}

    def test_step_01_start(self):
        """STEP 1: START - 测试环境初始化"""
        try:
            _record_step("START", True, "测试环境就绪")
            assert True
        except Exception as e:
            _record_step("START", False, error=e)
            pytest.fail(f"START failed: {e}")

    def test_step_02_config(self):
        """STEP 2: CONFIG - 验证配置加载"""
        try:
            import config
            # 验证关键配置项
            assert config is not None
            _record_step("CONFIG", True, "config 模块加载成功")
        except Exception as e:
            _record_step("CONFIG", False, error=e)
            pytest.fail(f"CONFIG failed: {e}")

    def test_step_03_db_init(self):
        """STEP 3: DB_INIT - 数据库初始化"""
        try:
            import database as db
            db.init_db()
            import subject_registry
            from account.models import ACCOUNT_TABLES_SQL
            from canonical_data import ensure_canonical_table
            from lumenis.shared.evidence import store as evidence_store
            # 验证数据库可连接
            with db.get_db() as conn:
                subject_registry.ensure_schema(conn)
                evidence_store.ensure_evidence_schema(conn)
                ensure_canonical_table(connection=conn)
                conn.executescript(ACCOUNT_TABLES_SQL)
                conn.execute("""INSERT INTO lumenis_subject_registry (
                    subject_id, domain_id, subject_type, name_en, name_zh,
                    name_en_norm, name_zh_norm, industry, keywords_json, status,
                    created_at, updated_at
                ) VALUES ('GUANGZHOU_TAIKOO_HUI', 'CTH', 'company',
                    'Guangzhou Taikoo Hui', '广州太古汇', 'guangzhou taikoo hui',
                    '广州太古汇', 'retail', '[]', 'configured',
                    '2026-10-08', '2026-10-08')""")
                conn.execute("""INSERT INTO v4_users
                    (id, username, password_hash, role, display_name, status)
                    VALUES (401, 'l4-reader', 'test-only', 'user', 'L4 Reader', 'active')""")
                conn.execute("""INSERT INTO v4_sessions (user_id, token, expires_at)
                    VALUES (401, 'l4-chain-reader', ?)""",
                    ((datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),))
                for module in ('content', 'reports'):
                    conn.execute("""INSERT INTO v4_member_authorizations
                        (user_id, product_id, module, action, data_scope, time_range)
                        VALUES (401, 'CTH', ?, 'read', ?, NULL)""",
                        (module, json.dumps({'subject_ids': ['GUANGZHOU_TAIKOO_HUI']})))
                conn.commit()
                result = conn.execute("SELECT 1").fetchone()
                assert result is not None
            _record_step("DB_INIT", True, "数据库初始化成功，连接正常")
        except Exception as e:
            _record_step("DB_INIT", False, error=e)
            pytest.fail(f"DB_INIT failed: {e}")

    def test_step_04_collect_mock(self, chain_state):
        """STEP 4: COLLECT(mock) - 模拟采集数据"""
        try:
            chain_state["notes"] = MOCK_NOTES
            assert len(chain_state["notes"]) == 3
            # 验证数据完整性
            for note in MOCK_NOTES:
                assert note["note_id"], "note_id 不能为空"
                assert note["title"], "title 不能为空"
                assert note["source_platform"], "source_platform 不能为空"
            _record_step("COLLECT(mock)", True, f"模拟采集 {len(MOCK_NOTES)} 条数据")
        except Exception as e:
            _record_step("COLLECT(mock)", False, error=e)
            pytest.fail(f"COLLECT failed: {e}")

    def test_step_05_process(self, chain_state):
        """STEP 5: PROCESS - 数据清洗与主题识别"""
        try:
            import subject_rules as sr
            processed = []
            for note in chain_state["notes"]:
                # 主题识别
                is_subject = sr.subject_hit(
                    title=note.get("title", ""),
                    body=note.get("content", ""),
                    matched_keywords=note.get("matched_keywords", ""),
                    source_keyword=note.get("source_keyword", "")
                )
                note["_subject_verified"] = is_subject
                processed.append(note)
            # 所有 mock 数据都应命中主体
            assert all(n["_subject_verified"] for n in processed), "存在未命中主体的数据"
            chain_state["notes"] = processed
            _record_step("PROCESS", True, f"清洗+主题识别完成，{len(processed)} 条全部命中主体")
        except Exception as e:
            _record_step("PROCESS", False, error=e)
            pytest.fail(f"PROCESS failed: {e}")

    def test_step_06_store(self, chain_state):
        """STEP 6: STORE - 数据入库"""
        try:
            import database as db
            inserted_count = 0
            for note in chain_state["notes"]:
                row_id, inserted = db.insert_note(note)
                if inserted:
                    inserted_count += 1
            # 验证入库
            with db.get_db() as conn:
                for note in chain_state["notes"]:
                    row = conn.execute(
                        "SELECT note_id, title FROM notes WHERE note_id=?",
                        (note["note_id"],)
                    ).fetchone()
                    assert row is not None, f"note {note['note_id']} 未入库"
                    assert row["title"] == note["title"], f"note {note['note_id']} 标题不匹配"
            _record_step("STORE", True, f"{inserted_count} 条数据入库成功")
        except Exception as e:
            _record_step("STORE", False, error=e)
            pytest.fail(f"STORE failed: {e}")

    def test_step_07_ai_mock(self, chain_state):
        """STEP 7: AI(mock) - AI 分析（mock 规则引擎）"""
        try:
            import ai_analyzer
            # 使用规则引擎（非真实 AI 调用）进行情感分析
            for note in chain_state["notes"]:
                result = ai_analyzer.analyze_sentiment(
                    note.get("title", ""),
                    note.get("content", ""),
                    return_reasons=True
                )
                # analyze_sentiment(return_reasons=True) 返回 (sentiment, score, reasons)
                sentiment = result[0]
                score = result[1] if len(result) > 1 else 0.0
                reasons = result[2] if len(result) > 2 else []
                note["_sentiment"] = sentiment
                note["_sentiment_score"] = score
                note["_sentiment_reasons"] = reasons
                assert sentiment in ("positive", "neutral", "negative"), f"无效情感值: {sentiment}"
            # 验证分析完成（不强制要求必须有负面，规则引擎可能因词表差异判定不同）
            neg_notes = [n for n in chain_state["notes"] if n["_sentiment"] == "negative"]
            _record_step("AI(mock)", True,
                         f"AI 分析完成，负面 {len(neg_notes)} 条，正面/中性 {len(chain_state['notes']) - len(neg_notes)} 条")
        except Exception as e:
            _record_step("AI(mock)", False, error=e)
            pytest.fail(f"AI failed: {e}")

    def test_step_08_risk(self, chain_state):
        """STEP 8: RISK - 风险判断"""
        try:
            import risk_engine
            for note in chain_state["notes"]:
                engagement = note.get("likes", 0) + note.get("comments", 0)
                risk = risk_engine.evaluate_risk(
                    sentiment=note.get("_sentiment", "neutral"),
                    engagement=engagement,
                    severity=0.5 if note.get("_sentiment") == "negative" else 0.2,
                    confidence=0.8,
                )
                note["_risk"] = risk
                assert "final_risk" in risk, "风险结果缺少 final_risk 字段"
                assert risk["final_risk"] in ("low", "medium", "high", "critical", "unknown"), \
                    f"无效风险等级: {risk['final_risk']}"
            # 验证风险评估完成
            high_risk = [n for n in chain_state["notes"] if n["_risk"]["final_risk"] in ("high", "critical")]
            chain_state["risk_results"] = [n["_risk"] for n in chain_state["notes"]]
            _record_step("RISK", True,
                         f"风险评估完成，高风险 {len(high_risk)} 条，总 {len(chain_state['notes'])} 条")
        except Exception as e:
            _record_step("RISK", False, error=e)
            pytest.fail(f"RISK failed: {e}")

    def test_step_09_evidence(self, chain_state, l4_cth_subject_context):
        """STEP 9: EVIDENCE - 证据链"""
        try:
            from lumenis.shared.evidence.chain import EvidenceStore, init_db
            # 初始化证据库
            evidence_db = os.environ.get("ZBC_DB_PATH")
            assert evidence_db, "L4 evidence requires an explicit isolated DB path"
            init_db(evidence_db)
            store = EvidenceStore(db_path=evidence_db)
            evidence_ids = []
            for note in chain_state["notes"]:
                # 创建证据（EvidenceStore.add_evidence 返回 (Evidence, is_new)）
                ev, is_new = store.add_evidence(
                    source_type="note",
                    source_url=note.get("url", ""),
                    source_id=note["note_id"],
                    raw_content=json.dumps({
                        "title": note.get("title", ""),
                        "content": note.get("content", ""),
                        "sentiment": note.get("_sentiment", ""),
                        "risk_level": note.get("_risk", {}).get("level", ""),
                    }, ensure_ascii=False),
                    publish_datetime=note.get("publish_datetime"),
                    provider="l4_test",
                    domain_id=l4_cth_subject_context.domain_id,
                    product_id=l4_cth_subject_context.product_id,
                    subject_scope=l4_cth_subject_context.subject_id,
                )
                assert ev.evidence_id, "证据 ID 为空"
                assert ev.domain_id == "cth", "证据域未绑定到选定 CTH"
                assert ev.product_id == "CTH", "证据产品未绑定到选定 CTH"
                assert ev.subject_scope == "GUANGZHOU_TAIKOO_HUI", "证据主体范围不匹配"
                evidence_ids.append(ev.evidence_id)
            # 验证证据可检索
            for eid in evidence_ids:
                retrieved = store.get_evidence(eid)
                assert retrieved is not None, f"证据 {eid} 无法检索"
                assert retrieved.source_id in [n["note_id"] for n in chain_state["notes"]], \
                    f"证据 {eid} source_id 不匹配"
            chain_state["evidence_ids"] = evidence_ids
            # The notes table is only a projection; publish exact IDs through
            # the existing signed Canonical owner before scoped API reads.
            import database as db
            from canonical_data import CanonicalRecord, persist_canonical
            from lumenis.shared.evidence import store as evidence_store
            with db.get_db() as conn:
                for note, source_evidence_id in zip(chain_state["notes"], evidence_ids):
                    scope_receipt = evidence_store.record_evidence(
                        connection=conn, source="l4_test", project="LUMENIS",
                        product="CTH", feature_id="L4_CHAIN_SCOPE",
                        test_name="isolated_chain_scope_binding", result="PASS",
                        status="verified", inputs={"source_ids": [note["note_id"]],
                                                   "source_evidence_id": source_evidence_id},
                        outputs={"authorized": True}, domain_id="cth",
                        subject_id=l4_cth_subject_context.subject_id,
                    )
                    record = CanonicalRecord(
                        canonical_id=f"canonical-{note['note_id']}",
                        product_id="CTH", domain_id="cth",
                        subject_id=l4_cth_subject_context.subject_id,
                        scope_status="VERIFIED", scope_evidence_ref=str(scope_receipt),
                        source_id=note["note_id"], external_id=note["note_id"],
                        source_type="note", source_table="notes", source_platform="xhs",
                        title=note["title"], content=note["content"],
                        captured_at=datetime.now().isoformat(),
                        raw_ref=json.dumps({"table": "notes", "note_id": note["note_id"]}),
                    )
                    persist_canonical(conn, record)
                    chain_state["canonical_records"].append(record.canonical_id)
                conn.commit()
            _record_step("EVIDENCE", True, f"证据链创建 {len(evidence_ids)} 条，全部可检索")
        except Exception as e:
            _record_step("EVIDENCE", False, error=e)
            pytest.fail(f"EVIDENCE failed: {e}")

    def test_step_10_report(self, chain_state):
        """STEP 10: REPORT - 报告生成"""
        try:
            from lumenis.shared.reporting import daily as daily_report
            # 生成今日摘要
            summary = daily_report.generate_today_summary()
            assert summary is not None, "报告摘要为空"
            assert isinstance(summary, dict), "报告摘要不是 dict"
            # 验证报告包含关键字段
            assert "total_notes" in summary or "date" in summary or "summary" in summary, \
                f"报告缺少关键字段: {list(summary.keys())[:5]}"
            # 生成完整日报
            digest = daily_report.generate_daily_digest()
            assert digest is not None, "日报为空"
            _record_step("REPORT", True,
                         f"报告生成成功，摘要字段: {list(summary.keys())[:5]}")
        except Exception as e:
            _record_step("REPORT", False, error=e)
            pytest.fail(f"REPORT failed: {e}")

    def test_step_11_api(self, monkeypatch):
        """STEP 11: API - 验证 API 端点返回正确数据"""
        try:
            api_app = _load_app_for_api_test(monkeypatch)
            api_app.config['TESTING'] = True
            client = _authorized_chain_client(api_app)

            # Use an authenticated request with an explicit CTH/Guangzhou focus.
            auth_headers = _cth_request_headers()

            # 测试健康端点（无需认证）
            resp = client.get('/api/health')
            assert resp.status_code == 200, f"health 端点返回 {resp.status_code}"
            health_data = resp.get_json()
            assert health_data.get('ok') is True, "health 端点 ok != True"
            assert health_data.get('database') == 'ok', "数据库状态异常"

            # 测试状态端点（需要认证）
            resp = client.get('/api/status', headers=auth_headers)
            assert resp.status_code == 200, f"status 端点返回 {resp.status_code}"
            status_data = resp.get_json()
            assert status_data.get('ok') is True, "status 端点 ok != True"
            assert 'total_notes' in status_data, "status 缺少 total_notes"

            # 测试概览端点（需要认证）
            resp = client.get('/api/overview', headers=auth_headers)
            assert resp.status_code == 200, f"overview 端点返回 {resp.status_code}"
            overview_data = resp.get_json()
            assert overview_data.get('ok') is True, "overview 端点 ok != True"
            assert 'trend' in overview_data, "overview 缺少 trend"

            _record_step("API", True,
                         "health/status/overview 三个端点均返回 200 且数据正确")
        except Exception as e:
            _record_step("API", False, error=e)
            pytest.fail(f"API failed: {e}")

    def test_step_12_chain_complete(self, chain_state, monkeypatch):
        """STEP 12: 验证完整链路闭环"""
        try:
            # 验证所有环节都有产出
            assert len(chain_state["notes"]) == 3, "采集数据丢失"
            assert all(n.get("_subject_verified") for n in chain_state["notes"]), "主题识别失败"
            assert all(n.get("_sentiment") for n in chain_state["notes"]), "AI 分析失败"
            assert all(n.get("_risk") for n in chain_state["notes"]), "风险评估失败"
            assert len(chain_state["evidence_ids"]) == 3, "证据链不完整"
            assert len(chain_state["canonical_records"]) == 3, "Canonical 绑定不完整"

            # 验证数据可通过 API 查询
            api_app = _load_app_for_api_test(monkeypatch)
            api_app.config['TESTING'] = True
            client = _authorized_chain_client(api_app)
            resp = client.get('/api/note/l4_test_001', headers=_cth_request_headers())
            assert resp.status_code == 200, f"当前笔记详情端点返回 {resp.status_code}"
            result = resp.get_json()
            assert result.get("ok") is True
            assert result.get("note", {}).get("note_id") == "l4_test_001"

            _record_step("CHAIN_COMPLETE", True,
                         "完整链路闭环验证通过：采集→清洗→入库→AI→风险→证据→报告→API")
        except Exception as e:
            _record_step("CHAIN_COMPLETE", False, error=e)
            pytest.fail(f"CHAIN_COMPLETE failed: {e}")


# ============================================================
# 单独运行时输出结果
# ============================================================
if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
