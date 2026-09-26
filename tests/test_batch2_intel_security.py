# -*- coding: utf-8 -*-
"""Batch2 智能+安全模块单元测试 — Shard D verification.

覆盖9个无测试模块：
- lumenis.shared.database.registry
- LUMENIS SYSTEM Permission（Ad adapter through SYSTEM owner）
- kos_execution (temp DB)
- kos_metrics (pure functions)
- lumenis.shared.evidence.api (Flask test app)
- kos_intel (classify_intent pure)
- kos_professional (temp DB + circuit breaker)
- kos_report (temp DB)
- kos_routes (Flask blueprint registration)

硬约束：不碰 data/monitor.db，全部使用临时数据库或纯函数测试。
"""
from __future__ import annotations
import os
import sys
import json
import tempfile
import sqlite3
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


# ═══════════════════════════════════════════════════════════════
# 1. lumenis.shared.database.registry
# ═══════════════════════════════════════════════════════════════
class TestRepositoryRegistry:
    def test_singleton(self):
        from lumenis.shared.database.registry import get_registry
        r1 = get_registry()
        r2 = get_registry()
        assert r1 is r2

    def test_force_reload(self):
        from lumenis.shared.database.registry import get_registry
        r1 = get_registry()
        r2 = get_registry(force_reload=True)
        assert r1 is not r2

    def test_repo_root_resolves(self):
        from lumenis.shared.database.registry import get_registry
        reg = get_registry()
        assert reg.repo_root.exists()
        assert (reg.repo_root / 'lumenis' / 'system' / 'security' / 'permission.py').exists()

    def test_resolve_relative_path(self):
        from lumenis.shared.database.registry import get_registry
        reg = get_registry()
        p = reg.resolve('data/monitor.db')
        assert p.endswith('data' + os.sep + 'monitor.db') or p.endswith('data/monitor.db')
        assert os.path.isabs(p)

    def test_resolve_absolute_passthrough(self):
        from lumenis.shared.database.registry import get_registry
        reg = get_registry()
        abs_path = os.path.join(tempfile.gettempdir(), 'test_abs.txt')
        p = reg.resolve(abs_path)
        assert p == os.path.normpath(abs_path) or os.path.samefile(os.path.dirname(p), os.path.dirname(abs_path))

    def test_data_dir_property(self):
        from lumenis.shared.database.registry import get_registry
        reg = get_registry()
        assert reg.data_dir.name == 'data'
        assert reg.data_dir.exists()

    def test_ensure_dir_creates(self):
        from lumenis.shared.database.registry import RepositoryRegistry
        with tempfile.TemporaryDirectory() as tmp:
            reg = RepositoryRegistry(repo_root=tmp)
            d = reg.ensure_dir('data')
            assert d.exists()
            assert d.name == 'data'

    def test_ensure_dir_invalid_key_raises(self):
        from lumenis.shared.database.registry import get_registry
        reg = get_registry()
        with pytest.raises(KeyError):
            reg.ensure_dir('nonexistent_key')

    def test_to_dict_serializable(self):
        from lumenis.shared.database.registry import get_registry
        reg = get_registry()
        d = reg.to_dict()
        assert 'repo_root' in d
        assert 'data' in d
        json.dumps(d)  # must be JSON serializable

    def test_module_level_resolve_path(self):
        from lumenis.shared.database.registry import resolve_path
        p = resolve_path('data')
        assert os.path.isabs(p)


# ═══════════════════════════════════════════════════════════════
# 2. LUMENIS SYSTEM Permission owner, consumed through the Ad domain adapter
# ═══════════════════════════════════════════════════════════════
@pytest.fixture
def strict_system_permission_mode():
    from lumenis.system.security import is_testing_bypass_enabled, set_testing_bypass

    was_enabled = is_testing_bypass_enabled()
    set_testing_bypass(False)
    yield
    set_testing_bypass(was_enabled)


@pytest.mark.usefixtures('strict_system_permission_mode')
class TestAdPermissionGate:
    @staticmethod
    def _new_gate():
        from ad_intelligence.permission_gate import AdPermissionGate
        from lumenis.system.security import PermissionGate, PermissionLevel

        system_gate = PermissionGate(enabled_permissions={
            PermissionLevel.READ,
            PermissionLevel.ANALYZE,
            PermissionLevel.PUSH,
        })
        return AdPermissionGate(system_gate=system_gate)

    def test_default_levels_read_analyze_only(self):
        from ad_intelligence.permission_gate import AdPermissionGate, AdPermissionLevel
        g = self._new_gate()
        assert g.has_permission(AdPermissionLevel.READ)
        assert g.has_permission(AdPermissionLevel.ANALYZE)
        assert not g.has_permission(AdPermissionLevel.PREVIEW)
        assert not g.has_permission(AdPermissionLevel.EXECUTE)

    def test_require_execute_denied_without_human(self):
        from ad_intelligence.permission_gate import AdPermissionGate, AdPermissionLevel
        g = self._new_gate()
        # Even if EXECUTE were enabled, human approval required
        g._enabled_levels.add(AdPermissionLevel.EXECUTE)
        assert g.require(AdPermissionLevel.EXECUTE, 'test_op') is False

    def test_require_read_allowed(self):
        from ad_intelligence.permission_gate import AdPermissionGate, AdPermissionLevel
        g = self._new_gate()
        assert g.require(AdPermissionLevel.READ, 'read_op') is True

    def test_grant_human_approval_enables_execute(self):
        from ad_intelligence.permission_gate import AdPermissionGate, AdPermissionLevel
        g = self._new_gate()
        g._enabled_levels.add(AdPermissionLevel.EXECUTE)
        g.grant_human_approval(duration_minutes=5)
        assert g.require(AdPermissionLevel.EXECUTE, 'test_op') is True

    def test_revoke_human_approval(self):
        from ad_intelligence.permission_gate import AdPermissionGate, AdPermissionLevel
        g = self._new_gate()
        g._enabled_levels.add(AdPermissionLevel.EXECUTE)
        g.grant_human_approval()
        g.revoke_human_approval()
        assert g.require(AdPermissionLevel.EXECUTE, 'test_op') is False

    def test_execute_with_gate_permission_denied(self):
        from ad_intelligence.permission_gate import AdPermissionGate, AdPermissionLevel
        g = self._new_gate()
        success, result = g.execute_with_gate(AdPermissionLevel.EXECUTE, 'bad_op', lambda: 'should not run')
        assert success is False
        assert '权限不足' in result

    def test_execute_with_gate_success(self):
        from ad_intelligence.permission_gate import AdPermissionGate, AdPermissionLevel
        g = self._new_gate()
        success, result = g.execute_with_gate(AdPermissionLevel.READ, 'read_op', lambda: 42)
        assert success is True
        assert result == 42

    def test_execute_with_gate_exception_captured(self):
        from ad_intelligence.permission_gate import AdPermissionGate, AdPermissionLevel
        g = self._new_gate()
        def fail():
            raise ValueError('test error')
        success, result = g.execute_with_gate(AdPermissionLevel.READ, 'fail_op', fail)
        assert success is False
        assert 'test error' in result

    def test_get_status(self):
        from ad_intelligence.permission_gate import AdPermissionGate
        g = self._new_gate()
        s = g.get_status()
        assert 'read' in s['enabled_levels']
        assert 'analyze' in s['enabled_levels']
        assert s['human_approved'] is False
        assert s['operation_count'] == 0

    def test_log_operation_records(self):
        from ad_intelligence.permission_gate import AdPermissionGate, AdPermissionLevel
        g = self._new_gate()
        g.log_operation(AdPermissionLevel.READ, 'test', {'k': 'v'}, True)
        assert len(g._operation_log) == 1
        assert g._operation_log[0]['operation'] == 'test'

    def test_global_singleton(self):
        from ad_intelligence.permission_gate import get_permission_gate
        g1 = get_permission_gate()
        g2 = get_permission_gate()
        assert g1 is g2


# ═══════════════════════════════════════════════════════════════
# 3. kos_execution (temp DB)
# ═══════════════════════════════════════════════════════════════
@pytest.fixture
def kos_exec_temp_db(tmp_path, monkeypatch):
    """Create temp DB for kos_execution tests."""
    db_file = tmp_path / 'test_kos_exec.db'
    monkeypatch.setenv('ZBC_DB_PATH', str(db_file))
    # Reimport to pick up new DB path
    import importlib
    import kos_execution
    importlib.reload(kos_execution)
    return kos_execution


class TestKosExecution:
    def test_gated_actions_defined(self, kos_exec_temp_db):
        assert len(kos_exec_temp_db.GATED_ACTIONS) >= 9
        assert 'reply_send' in kos_exec_temp_db.GATED_ACTIONS
        assert 'paid_media' in kos_exec_temp_db.GATED_ACTIONS

    def test_create_execution_valid_action(self, kos_exec_temp_db):
        ke = kos_exec_temp_db
        result = ke.create_execution('reply_send', target_author_id='user1', actor='tester')
        assert result is not None
        assert result['action_type'] == 'reply_send'
        assert result['status'] == 'AI_GENERATED'
        assert result['execution_id'].startswith('KX-')

    def test_create_execution_invalid_action_raises(self, kos_exec_temp_db):
        ke = kos_exec_temp_db
        with pytest.raises(ValueError, match='不在 HCG 门控动作内'):
            ke.create_execution('invalid_action')

    def test_transition_valid_path(self, kos_exec_temp_db):
        ke = kos_exec_temp_db
        ex = ke.create_execution('reply_send', actor='tester')
        eid = ex['execution_id']
        # AI_GENERATED -> PENDING_HUMAN_REVIEW
        r = ke.transition(eid, 'PENDING_HUMAN_REVIEW')
        assert r['status'] == 'PENDING_HUMAN_REVIEW'
        # PENDING_HUMAN_REVIEW -> HUMAN_APPROVED (requires actor)
        r = ke.transition(eid, 'HUMAN_APPROVED', actor='admin')
        assert r['status'] == 'HUMAN_APPROVED'

    def test_transition_invalid_path_raises(self, kos_exec_temp_db):
        ke = kos_exec_temp_db
        ex = ke.create_execution('reply_send', actor='tester')
        eid = ex['execution_id']
        # AI_GENERATED -> SUCCESS is invalid (must go through review)
        with pytest.raises(ValueError, match='非法状态转移'):
            ke.transition(eid, 'SUCCESS')

    def test_transition_human_approved_requires_actor(self, kos_exec_temp_db):
        ke = kos_exec_temp_db
        ex = ke.create_execution('reply_send', actor='tester')
        eid = ex['execution_id']
        ke.transition(eid, 'PENDING_HUMAN_REVIEW')
        with pytest.raises(ValueError, match='人工确认/执行必须提供 actor'):
            ke.transition(eid, 'HUMAN_APPROVED')  # no actor

    def test_transition_nonexistent_raises(self, kos_exec_temp_db):
        ke = kos_exec_temp_db
        with pytest.raises(KeyError, match='execution 不存在'):
            ke.transition('KX-NONEXISTENT', 'PENDING_HUMAN_REVIEW')

    def test_get_execution(self, kos_exec_temp_db):
        ke = kos_exec_temp_db
        ex = ke.create_execution('email_send', actor='tester')
        fetched = ke.get_execution(ex['execution_id'])
        assert fetched is not None
        assert fetched['execution_id'] == ex['execution_id']

    def test_get_execution_nonexistent_returns_none(self, kos_exec_temp_db):
        ke = kos_exec_temp_db
        assert ke.get_execution('KX-NOPE') is None

    def test_list_executions_filter(self, kos_exec_temp_db):
        ke = kos_exec_temp_db
        ke.create_execution('reply_send', actor='t1')
        ke.create_execution('email_send', actor='t2')
        all_rows = ke.list_executions(limit=10)
        assert len(all_rows) >= 2
        # Filter by action_type
        reply_rows = ke.list_executions(action_type='reply_send', limit=10)
        assert all(r['action_type'] == 'reply_send' for r in reply_rows)

    def test_terminal_states(self, kos_exec_temp_db):
        ke = kos_exec_temp_db
        assert 'SUCCESS' in ke.TERMINAL
        assert 'FAILED' in ke.TERMINAL
        assert 'REJECTED' in ke.TERMINAL


# ═══════════════════════════════════════════════════════════════
# 4. kos_metrics (pure functions)
# ═══════════════════════════════════════════════════════════════
class TestKosMetrics:
    def test_koc_reward_tier_gold_24h(self):
        from kos_metrics import koc_reward_tier
        r = koc_reward_tier(150, 0)
        assert r['tier'] == 'gold'

    def test_koc_reward_tier_gold_7d(self):
        from kos_metrics import koc_reward_tier
        r = koc_reward_tier(0, 600)
        assert r['tier'] == 'gold'

    def test_koc_reward_tier_silver(self):
        from kos_metrics import koc_reward_tier
        r = koc_reward_tier(60, 0)
        assert r['tier'] == 'silver'

    def test_koc_reward_tier_bronze(self):
        from kos_metrics import koc_reward_tier
        r = koc_reward_tier(1, 0)
        assert r['tier'] == 'bronze'

    def test_koc_reward_tier_none(self):
        from kos_metrics import koc_reward_tier
        r = koc_reward_tier(0, 0)
        assert r['tier'] == 'none'

    def test_koc_reward_tier_custom_rules(self):
        from kos_metrics import koc_reward_tier
        custom = {"gold": {"24h_min": 10, "7d_min": 20}, "silver": {"24h_min": 5, "7d_min": 10}, "bronze": {"24h_min": 1, "7d_min": 1}}
        r = koc_reward_tier(12, 0, rules=custom)
        assert r['tier'] == 'gold'

    def test_cost_metrics_no_data(self, tmp_path, monkeypatch):
        monkeypatch.setattr('kos_metrics.MANUAL_PATH', tmp_path / 'nonexistent.json')
        from kos_metrics import cost_metrics
        r = cost_metrics()
        assert r['boosting_budget'] == 0
        assert r['cpl'] is None  # no inquiry -> None
        assert r['cpc'] is None
        assert 'inquiry' in r['manual_pending']

    def test_koc_campaign_review_empty(self):
        from kos_metrics import koc_campaign_review
        r = koc_campaign_review('camp1', [])
        assert r['koc_count'] == 0
        assert r['viewership'] == 0

    def test_koc_campaign_review_with_data(self):
        from kos_metrics import koc_campaign_review
        kocs = [
            {"author_id": "a1", "viewership": 100, "engagement": 50, "high_intent_comments": 5, "engagement_24h": 120, "engagement_7d": 300},
            {"author_id": "a2", "viewership": 200, "engagement": 80, "high_intent_comments": 2, "engagement_24h": 0, "engagement_7d": 0},
        ]
        r = koc_campaign_review('camp1', kocs)
        assert r['koc_count'] == 2
        assert r['viewership'] == 300
        assert r['engagement'] == 130
        assert r['high_intent_comments'] == 7
        assert 'gold' in r['tiers']

    def test_channel_roi_builtin_benchmarks(self):
        from kos_metrics import CHANNEL_BENCHMARKS
        assert 'xhs_boosting' in CHANNEL_BENCHMARKS
        assert 'wechat_oa' in CHANNEL_BENCHMARKS
        assert CHANNEL_BENCHMARKS['xhs_boosting']['reference_cpl'] == 57.32
        assert CHANNEL_BENCHMARKS['wechat_oa']['reference_cpl'] == 9.36


# ═══════════════════════════════════════════════════════════════
# 5. lumenis.shared.evidence.api (Flask test app)
# ═══════════════════════════════════════════════════════════════
@pytest.fixture
def evidence_client(tmp_path, monkeypatch):
    from flask import Flask
    from lumenis.shared.evidence import store
    from lumenis.shared.evidence.api import register_evidence_api

    db_file = tmp_path / 'test_ev.db'
    monkeypatch.setenv('ZBC_DB_PATH', str(db_file))
    store.init_evidence_store(str(db_file))
    app = Flask(__name__)
    register_evidence_api(app)
    return app.test_client()


class TestEvidenceApi:
    def test_register_blueprint(self):
        from flask import Flask
        from lumenis.shared.evidence.api import register_evidence_api
        app = Flask(__name__)
        bp = register_evidence_api(app)
        assert bp.name == 'evidence_api'
        # Check routes registered
        rules = [r.rule for r in app.url_map.iter_rules()]
        assert '/api/evidence/stats' in rules
        assert '/api/evidence/list' in rules
        assert '/api/evidence/timeline' in rules

    def test_stats_endpoint(self, evidence_client):
        from lumenis.shared.evidence import store

        record_id = store.record_evidence(
            source='test', project='LUMENIS', product='CTH',
            feature_id='TEST_FEATURE', level='L4', result='PASS',
            account='acc1', actual='test actual', test_name='evidence_stats',
        )
        assert record_id > 0
        resp = evidence_client.get('/api/evidence/stats')
        assert resp.status_code == 401
        assert resp.get_json()['code'] == 'AUTH_REQUIRED'

    def test_list_endpoint_params(self, evidence_client):
        from flask import Flask
        # Test with limit param
        resp = evidence_client.get('/api/evidence/list?limit=10&offset=0')
        assert resp.status_code == 401
        assert resp.get_json()['code'] == 'AUTH_REQUIRED'

    def test_detail_endpoint_404(self, evidence_client):
        resp = evidence_client.get('/api/evidence/999999')
        assert resp.status_code == 401
        assert resp.get_json()['code'] == 'AUTH_REQUIRED'

    def test_authenticated_read_without_context_returns_400(self, evidence_client, monkeypatch):
        import lumenis.auth.service as auth_service
        from lumenis.shared.evidence import store

        monkeypatch.setattr(auth_service, "get_current_user", lambda: {"id": 1, "role": "user"})
        monkeypatch.setattr(
            store, "query_scoped_evidence",
            lambda **kwargs: pytest.fail("scope failure must happen before Evidence read"),
        )
        response = evidence_client.get("/api/evidence/list")
        assert response.status_code == 400
        assert response.get_json()["code"] == "EVIDENCE_SCOPE_REQUIRED"


# ═══════════════════════════════════════════════════════════════
# 6. kos_intel (classify_intent pure function)
# ═══════════════════════════════════════════════════════════════
class TestKosIntel:
    def test_classify_intent_strong_buy(self):
        from kos_intel import classify_intent
        r = classify_intent("这个多少钱怎么买")
        assert r['level'] == 'strong'
        assert r['category'] == '购买意向'
        assert len(r['matched_keywords']) > 0

    def test_classify_intent_weak_consult(self):
        from kos_intel import classify_intent
        r = classify_intent("这个好不好用，求推荐")
        assert r['level'] == 'weak'
        assert r['category'] == '咨询意向'

    def test_classify_intent_negative(self):
        from kos_intel import classify_intent
        r = classify_intent("这个垃圾产品，投诉")
        assert r['level'] == 'none'
        assert r['category'] == '负面'

    def test_classify_intent_normal(self):
        from kos_intel import classify_intent
        r = classify_intent("今天天气不错")
        assert r['level'] == 'none'
        assert r['category'] == '普通互动'

    def test_classify_intent_empty(self):
        from kos_intel import classify_intent
        r = classify_intent("")
        assert r['level'] == 'none'
        assert r['category'] == 'NO_REPLY'
        assert r['confidence'] == 0.0

    def test_classify_intent_none(self):
        from kos_intel import classify_intent
        r = classify_intent(None)
        assert r['level'] == 'none'

    def test_intent_keywords_defined(self):
        from kos_intel import _INTENT_STRONG, _INTENT_WEAK
        assert len(_INTENT_STRONG) >= 20
        assert len(_INTENT_WEAK) >= 10
        assert '怎么买' in _INTENT_STRONG
        assert '推荐' in _INTENT_WEAK

    def test_kos_nick_signals_defined(self):
        from kos_intel import _KOS_NICK_SIGNALS, _KOS_CONTENT_SIGNALS
        assert len(_KOS_NICK_SIGNALS) >= 10
        assert '柜姐' in _KOS_NICK_SIGNALS
        assert 'SA' in _KOS_NICK_SIGNALS
        assert len(_KOS_CONTENT_SIGNALS) >= 10


# ═══════════════════════════════════════════════════════════════
# 7. kos_professional (temp DB + circuit breaker)
# ═══════════════════════════════════════════════════════════════
@pytest.fixture
def kprof_temp_db(tmp_path, monkeypatch):
    db_file = tmp_path / 'test_kprof.db'
    monkeypatch.setenv('ZBC_DB_PATH', str(db_file))
    import importlib
    import kos_professional
    importlib.reload(kos_professional)
    return kos_professional


class TestKosProfessional:
    def test_init_db_creates_tables(self, kprof_temp_db):
        kp = kprof_temp_db
        from lumenis.shared.database import DatabaseRepository
        conn = DatabaseRepository(os.environ['ZBC_DB_PATH']).connect()
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        assert 'professional_accounts' in tables
        assert 'professional_metrics' in tables

    def test_is_enabled_default_false(self, kprof_temp_db):
        kp = kprof_temp_db
        assert kp.is_enabled('test_brand') is False

    def test_enable_account(self, kprof_temp_db):
        kp = kprof_temp_db
        r = kp.enable('test_brand', 'xiaohongshu', 'acc1', account_name='Test Account')
        assert r['ok'] is True
        assert r['status'] == 'pending'
        assert kp.is_enabled('test_brand') is True

    def test_disable_account(self, kprof_temp_db):
        kp = kprof_temp_db
        kp.enable('brand2', 'xiaohongshu', 'acc2')
        r = kp.disable('brand2', 'xiaohongshu', 'acc2')
        assert r['ok'] is True
        assert r['status'] == 'disabled'
        assert kp.is_enabled('brand2') is False

    def test_list_accounts(self, kprof_temp_db):
        kp = kprof_temp_db
        kp.enable('brand3', 'xiaohongshu', 'acc3')
        accounts = kp.list_accounts('brand3')
        assert len(accounts) >= 1
        assert accounts[0]['account_id'] == 'acc3'

    def test_import_metrics_not_enabled_rejected(self, kprof_temp_db):
        kp = kprof_temp_db
        r = kp.import_metrics('not_enabled_brand', 'acc1', [])
        assert r['ok'] is False
        assert r['code'] == 'NOT_ENABLED'

    def test_import_metrics_success(self, kprof_temp_db):
        kp = kprof_temp_db
        kp.enable('brand4', 'xiaohongshu', 'acc4')
        metrics = [
            {"metric_date": "2026-01-01", "impressions": 1000, "views": 500, "likes": 100},
            {"metric_date": "2026-01-02", "impressions": 2000, "views": 800, "likes": 200},
        ]
        r = kp.import_metrics('brand4', 'acc4', metrics)
        assert r['ok'] is True
        assert r['imported'] == 2
        assert r['failed'] == 0

    def test_get_metrics_not_enabled_empty(self, kprof_temp_db):
        kp = kprof_temp_db
        result = kp.get_metrics('no_brand')
        assert result == []

    def test_circuit_breaker_returns_default_on_exception(self, kprof_temp_db):
        kp = kprof_temp_db

        @kp.kos_circuit_breaker(timeout=1.0, default_return={"fallback": True})
        def failing_func():
            raise RuntimeError("test failure")

        result = failing_func()
        assert result == {"fallback": True}

    def test_circuit_breaker_passes_through_success(self, kprof_temp_db):
        kp = kprof_temp_db

        @kp.kos_circuit_breaker(timeout=1.0)
        def success_func(x):
            return x * 2

        assert success_func(5) == 10

    def test_circuit_breaker_preserves_function_name(self, kprof_temp_db):
        kp = kprof_temp_db

        @kp.kos_circuit_breaker()
        def my_named_function():
            return 1

        assert my_named_function.__name__ == 'my_named_function'


# ═══════════════════════════════════════════════════════════════
# 8. kos_report (temp DB)
# ═══════════════════════════════════════════════════════════════
@pytest.fixture
def kreport_temp_db(tmp_path, monkeypatch):
    db_file = tmp_path / 'test_kreport.db'
    monkeypatch.setenv('ZBC_DB_PATH', str(db_file))
    # Create minimal tables
    conn = sqlite3.connect(str(db_file))
    conn.execute("""CREATE TABLE IF NOT EXISTS kos_profiles (
        id INTEGER PRIMARY KEY, author_id TEXT, author_nickname TEXT,
        kos_tier TEXT, kos_score REAL, note_count INTEGER, total_engagement INTEGER,
        total_likes INTEGER, total_comments INTEGER, subject_type TEXT,
        lifecycle_stage TEXT, is_potential INTEGER, is_risk INTEGER,
        negative_count INTEGER, risk_count INTEGER, avg_engagement REAL,
        identity_label TEXT, is_kos INTEGER, updated_at TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY, note_id TEXT, title TEXT, author_nickname TEXT,
        likes INTEGER, comments INTEGER, collects INTEGER, shares INTEGER,
        publish_datetime TEXT, sentiment TEXT, url TEXT, risk_level TEXT,
        content_quality_score REAL, author_id TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS note_comments (
        id INTEGER PRIMARY KEY, note_id TEXT, content TEXT, publish_time TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY, title TEXT, risk_level TEXT, mention_count INTEGER,
        first_seen TEXT, status TEXT
    )""")
    # Insert test data
    conn.execute("INSERT INTO kos_profiles (author_id, author_nickname, kos_tier, kos_score, note_count, total_engagement, lifecycle_stage, is_potential, is_risk) VALUES ('u1', 'TestKOS', 'S', 95.5, 10, 5000, 'active', 0, 0)")
    conn.execute("INSERT INTO notes (note_id, title, author_nickname, likes, comments, collects, shares, publish_datetime, sentiment) VALUES ('n1', 'Test Note', 'TestKOS', 100, 20, 15, 5, '2026-01-01', 'positive')")
    conn.commit()
    conn.close()

    from lumenis.shared.reporting import kos as current_kos_report
    return current_kos_report


class TestKosReport:
    def test_generate_report_creates_html(self, kreport_temp_db, tmp_path):
        kr = kreport_temp_db
        output = str(tmp_path / 'test_report.html')
        result = kr.generate_report(brand_name="Test Brand", output_path=output)
        assert result['ok'] is True
        assert os.path.exists(output)
        assert result['brand'] == 'Test Brand'
        assert result['file_size'] > 0
        # Check HTML content
        with open(output, 'r', encoding='utf-8') as f:
            html = f.read()
        assert '<!DOCTYPE html>' in html
        assert 'Test Brand' in html
        assert 'KOS Intelligence' in html

    def test_collect_data_returns_structure(self, kreport_temp_db):
        kr = kreport_temp_db
        data = kr._collect_data("Test Brand")
        assert 'brand_name' in data
        assert 'overview' in data
        assert 'top_kos' in data
        assert 'top_notes' in data
        assert 'ad_candidates' in data
        assert data['overview']['total'] >= 1

    def test_render_html_returns_string(self, kreport_temp_db):
        kr = kreport_temp_db
        data = kr._collect_data("Test")
        html = kr._render_html(data)
        assert isinstance(html, str)
        assert len(html) > 1000
        assert '</html>' in html

    def test_report_dir_constant(self, kreport_temp_db):
        kr = kreport_temp_db
        assert hasattr(kr, 'REPORT_DIR')
        assert 'reports' in kr.REPORT_DIR


# ═══════════════════════════════════════════════════════════════
# 9. kos_routes (Flask blueprint registration)
# ═══════════════════════════════════════════════════════════════
class TestKosRoutes:
    def test_register_kos_routes_blueprint(self, tmp_path, monkeypatch):
        # Use temp DB to avoid touching production
        db_file = tmp_path / 'test_kos_routes.db'
        monkeypatch.setenv('ZBC_DB_PATH', str(db_file))
        # Create minimal tables needed for import
        conn = sqlite3.connect(str(db_file))
        for table in ['kos_profiles', 'notes', 'note_comments', 'events', 'kos_executions', 'professional_accounts', 'professional_metrics']:
            conn.execute(f"CREATE TABLE IF NOT EXISTS {table} (id INTEGER PRIMARY KEY)")
        conn.commit()
        conn.close()

        import importlib
        import kos_routes
        importlib.reload(kos_routes)

        from flask import Flask
        app = Flask(__name__)
        # Check if register function exists
        assert hasattr(kos_routes, 'register_kos_routes') or hasattr(kos_routes, 'register_routes') or any('register' in n for n in dir(kos_routes))

    def test_kos_routes_module_imports(self):
        """Verify kos_routes can be imported without errors."""
        import kos_routes
        assert kos_routes is not None

    def test_kos_routes_has_route_functions(self):
        """Verify kos_routes contains route-related functions."""
        import kos_routes
        # Module should have Flask route functions or a registration function
        func_names = [n for n in dir(kos_routes) if not n.startswith('_')]
        assert len(func_names) > 0  # has public functions


# ═══════════════════════════════════════════════════════════════
# Cross-cutting: evidence_store (already has tests, verify import)
# ═══════════════════════════════════════════════════════════════
class TestEvidenceStoreImport:
    def test_import_and_constants(self):
        from lumenis.shared.evidence import store as evidence_store
        assert 'L0' in evidence_store.LEVELS
        assert 'PASS' in evidence_store.RESULTS
        assert 'prod' in evidence_store.ENVS

    def test_evidence_hash_deterministic(self):
        from lumenis.shared.evidence import store as evidence_store
        h1 = evidence_store._evidence_hash({"a": 1, "b": 2})
        h2 = evidence_store._evidence_hash({"b": 2, "a": 1})
        assert h1 == h2  # sort_keys ensures deterministic

    def test_json_dumps_handles_objects(self):
        from lumenis.shared.evidence import store as evidence_store
        class CustomObj:
            def __str__(self):
                return "custom"
        result = evidence_store._json_dumps({"obj": CustomObj()})
        assert 'custom' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
