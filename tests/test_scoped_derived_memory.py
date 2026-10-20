"""Derived memory is scoped, persistent, revocable and never external evidence."""
import json
import sqlite3
import pytest
from tests.test_agent_runtime_http_binding import agent_client, submit

@pytest.fixture(autouse=True)
def learning_schema(agent_client):
    from lumenis.shared.database import migrations
    assert migrations.migrate()
    with sqlite3.connect(agent_client[2]) as con:
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(1,'CTH','agent_runtime','write',?)", (json.dumps({'global': True}),))
from tests.test_skill_http_durable_identity import skill_client
from agent_memory.base import BaseMemoryLayer


def test_unknown_filter_is_not_ignored():
    memory = BaseMemoryLayer(enabled=True)
    memory.store('a', {'text': 'private'}, metadata={'actor_id': 1})
    assert memory.query({'missing_scope': 'other'}) == []
    assert memory.query({'actor_id': 2}) == []


def test_derived_restart_correction_forget_and_scope(agent_client):
    api, app, path = agent_client
    task_id = submit(api)
    memory = BaseMemoryLayer(path, enabled=True).bind_task(task_id, 1)
    original = {'text': '完整内容' * 50000}
    assert memory.store('preference', original)
    fresh = BaseMemoryLayer(path, enabled=True).bind_task(task_id, 1)
    assert fresh.retrieve('preference').value == original
    assert fresh.store('preference', {'text': 'corrected'})
    assert memory.retrieve('preference').value == {'text': 'corrected'}
    stale_inflight = memory.retrieve('preference')
    other_task = submit(api)
    assert BaseMemoryLayer(path, enabled=True).bind_task(other_task, 1).retrieve('preference') is None
    with pytest.raises(PermissionError):
        BaseMemoryLayer(path, enabled=True).bind_task(task_id, 2)
    assert memory.forget('preference')
    assert fresh.retrieve('preference') is None
    with pytest.raises(PermissionError, match='MEMORY_FORGET_TOMBSTONE'):
        memory._write_derived(stale_inflight)
    with pytest.raises(PermissionError, match='MEMORY_FORGET_TOMBSTONE'):
        fresh.store('preference', {'text': 'late background write'})
    assert fresh.retrieve('preference') is None
    with sqlite3.connect(path) as con:
        row = con.execute("SELECT content_json,lifecycle_stage FROM agent_learning_records WHERE learning_type='derived_memory_base'").fetchone()
        assert json.loads(row[0])['revision'] == 3
        assert row[1] == 'archived'
        assert con.execute('SELECT COUNT(*) FROM ai_task_evidence').fetchone()[0] == 0
        con.execute("DELETE FROM v4_member_authorizations WHERE module='agent_runtime'")
    with pytest.raises(PermissionError):
        fresh.query()
    with pytest.raises(PermissionError):
        fresh.store('late', {'text': 'denied'})


def test_derived_commit_failure_no_cached_success(agent_client):
    api, app, path = agent_client
    task_id = submit(api)
    memory = BaseMemoryLayer(path, enabled=True).bind_task(task_id, 1)
    with sqlite3.connect(path) as con:
        con.execute("CREATE TRIGGER reject_memory BEFORE INSERT ON agent_learning_records BEGIN SELECT RAISE(ABORT, 'storage failure'); END")
    with pytest.raises(sqlite3.DatabaseError):
        memory.store('key', {'text': 'not committed'})
    assert memory.retrieve('key') is None


def test_http_memory_write_permission_revision_and_terminal_archive(agent_client):
    api, app, path = agent_client
    task_id = submit(api)
    url = f'/api/ai/tasks/{task_id}/memory'
    own = {'Authorization': 'Bearer fixture-session-one'}
    body = {'key': 'writing', 'value': {'style': 'brief'}, 'expected_revision': 0}
    created = api.post(url, json=body, headers=own)
    assert created.status_code == 200, created.get_json()
    assert created.get_json()['record']['metadata']['memory_revision'] == 1
    assert api.post(url, json=body, headers=own).status_code == 409
    assert api.post(url, json={**body, 'actor_id': 2}, headers=own).status_code == 400
    assert app.test_client().get(url, headers=own).get_json()['records'][0]['value'] == {'style': 'brief'}
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE module='agent_runtime' AND action='write'")
    assert api.get(url, headers=own).status_code == 200
    assert api.delete(url, json={'key': 'writing', 'expected_revision': 1}, headers=own).status_code == 403
    # Missing Memory-write authority cannot block the normal no-model task.
    ran = api.post(f'/api/ai/tasks/{task_id}/run', headers=own)
    assert ran.get_json()['task']['status'] == 'succeeded'
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(1,'CTH','agent_runtime','write',?)", (json.dumps({'global': True}),))
    second = submit(api)
    assert api.post(f'/api/ai/tasks/{second}/run', headers=own).get_json()['task']['status'] == 'succeeded'
    records = api.get(f'/api/ai/tasks/{second}/memory', headers=own).get_json()['records']
    assert any(row['metadata'].get('type') == 'task_archive' for row in records), records
    from agent_memory.task import TaskMemory
    from agent_memory.skill import SkillMemory
    assert TaskMemory(path, enabled=True).get_task(second) is None
    bound = TaskMemory(path, enabled=True).bind_task(second, 1)
    assert bound.get_task(task_id) is None
    assert len(bound.query_tasks()) == 1
    skills = SkillMemory(path, enabled=True).bind_task(second, 1)
    assert len(skills.get_recent_executions()) == 1
    assert skills.get_skill_stats('zbc.skill_registry_snapshot')['business_success_rate'] is None
    assert skills.record_feedback('zbc.skill_registry_snapshot', True, duration_ms=12)
    reopened_skills = SkillMemory(path, enabled=True).bind_task(second, 1)
    assert reopened_skills.query({'type': 'skill_feedback'})[0].value['reported_success'] is True
    assert reopened_skills.select_best_skill(['not-authorized', 'zbc.skill_registry_snapshot']) == 'zbc.skill_registry_snapshot'
    assert reopened_skills.select_best_skill(['not-authorized']) is None
    assert api.delete(url, json={'key': 'writing', 'expected_revision': 1}, headers=own).status_code == 200
    assert api.get(url, headers=own).get_json()['records'] == []


def test_memory_ttl_filter_precedes_limit_for_api_and_agent(agent_client, monkeypatch):
    """FIX-058: expired rows must not hide valid bound memory from either caller."""
    from datetime import datetime, timedelta, timezone
    from agent_memory.base import MemoryRecord
    from agent_memory.episodic import EpisodicMemory
    from agent_runtime.task_binding import AgentLoop

    api, app, path = agent_client
    task_id = submit(api)
    memory = EpisodicMemory(path, enabled=True).bind_task(task_id, 1)
    now = datetime.now(timezone.utc)
    expired_at = (now - timedelta(seconds=1)).isoformat()
    valid_at = (now - timedelta(seconds=10)).isoformat()
    for index in range(51):
        assert memory._write_derived(MemoryRecord(
            layer='episodic', key=f'expired-{index}', value={'ordinal': index},
            timestamp=expired_at, ttl_seconds=0.1))
    assert memory._write_derived(MemoryRecord(
        layer='episodic', key='valid-older', value={'source': 'still-valid'},
        timestamp=valid_at, ttl_seconds=60))

    headers = {'Authorization': 'Bearer fixture-session-one'}
    api_result = api.get(f'/api/ai/tasks/{task_id}/memory?layer=episodic', headers=headers)
    assert api_result.status_code == 200, api_result.get_json()
    assert [row['key'] for row in api_result.get_json()['records']] == ['valid-older']

    captured_contexts = []
    original_run = AgentLoop.run

    def capture_context(self, goal, context=None, agent_id=None, _resume_state=None,
                        _existing_task_id=None):
        captured_contexts.append(context)
        return original_run(self, goal, context=context, agent_id=agent_id,
                            _resume_state=_resume_state, _existing_task_id=_existing_task_id)

    monkeypatch.setattr(AgentLoop, 'run', capture_context)
    run_result = api.post(f'/api/ai/tasks/{task_id}/run', headers=headers)
    assert run_result.status_code == 200, run_result.get_json()
    assert run_result.get_json()['task']['status'] == 'succeeded'
    assert len(captured_contexts) == 1
    assert [row['key'] for row in captured_contexts[0]['derived_memory']] == ['valid-older']


def test_authorized_memory_methods_use_real_signed_sources_and_task_owner(agent_client, monkeypatch):
    api, app, path = agent_client
    task_id = submit(api)
    from lumenis.shared.evidence import store as evidence_store
    from canonical_data import ensure_canonical_table, CanonicalRecord, persist_canonical
    from agent_memory.semantic import SemanticMemory
    from agent_memory.episodic import EpisodicMemory
    from agent_memory.working import WorkingMemory
    from agent_memory.task import TaskMemory
    monkeypatch.setenv('LUMENIS_EVIDENCE_HMAC_KEY_RING', json.dumps({'memory-fixture': 'disposable-memory-fixture-signing-material'}))
    monkeypatch.setenv('LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID', 'memory-fixture')
    with sqlite3.connect(path) as con:
        evidence_store.ensure_evidence_schema(con)
        existing = {row[1] for row in con.execute('PRAGMA table_info(app_evidence_records)')}
        for column, kind, default in evidence_store.EVIDENCE_CHAIN_NEW_COLUMNS:
            if column not in existing:
                suffix = f" DEFAULT {default}" if default != "NULL" else ""
                con.execute(f"ALTER TABLE app_evidence_records ADD COLUMN {column} {kind}{suffix}")
        ensure_canonical_table(connection=con)
        con.execute('CREATE TABLE IF NOT EXISTS note_review_history(id INTEGER PRIMARY KEY,note_id TEXT,old_risk TEXT,new_risk TEXT,old_sentiment TEXT,new_sentiment TEXT)')
        con.execute("INSERT INTO note_review_history(note_id,old_risk,new_risk) VALUES('memory-note','high','low')")
        con.execute("INSERT INTO note_review_history(note_id,old_risk,new_risk) VALUES('unbound-note','high','low')")
        con.execute("CREATE TABLE IF NOT EXISTS rule_version_registry(version TEXT PRIMARY KEY,description TEXT,is_active INTEGER,applied_at TEXT)")
        con.execute("INSERT INTO rule_version_registry(version,description,is_active,applied_at) VALUES('memory-version','current scoped rules',1,'2026-10-17')")
    with sqlite3.connect(path) as con:
        evidence_id = evidence_store.record_evidence(connection=con, source='unit_fixture',project='LUMENIS', product='CTH',
            feature_id='SCOPED_MEMORY',test_name='signed-source-fixture',result='PASS',status='verified',
            inputs={'source_ids': ['memory-note']},outputs={'fixture': True},domain_id='cth',subject_id='MEMORY-SUBJECT')
        persist_canonical(con, CanonicalRecord(canonical_id='memory-canonical',product_id='CTH',domain_id='cth',
            source_id='memory-note',external_id='memory-note',subject_id='MEMORY-SUBJECT',source_table='notes', title='memory research',content='scoped source',
            scope_status='VERIFIED',scope_evidence_ref=str(evidence_id)))
    sm = SemanticMemory(path, enabled=True).bind_task(task_id, 1)
    assert sm.search_assets('memory')[0]['canonical_id'] == 'memory-canonical'
    assert sm.get_asset('memory-canonical')['source_id'] == 'memory-note'
    assert 'memory research' in sm.get_knowledge_context('memory')
    assert sm.get_active_rule_version()['version'] == 'memory-version'
    assert len(sm.get_rule_history()) == 1
    # Missing library metadata never invents membership.
    assert sm.get_assets_by_library('unknown') == []
    assert sm.store_knowledge('draft', {'text': 'derived thought'}).metadata['truth_kind'] == 'derived_memory'
    em = EpisodicMemory(path, enabled=True).bind_task(task_id, 1)
    assert [r['note_id'] for r in em.get_review_experience()] == ['memory-note']
    assert len(em.get_correction_patterns()) == 1
    assert em.get_review_experience('unbound-note') == []
    em.store_case('success', {'execution_only': True}, outcome='success', persist=True)
    em.store_case('failure', {'execution_only': True}, outcome='failure', persist=True)
    assert len(em.get_success_patterns()) == len(em.get_failure_patterns()) == 1
    wm = WorkingMemory(path, enabled=True).bind_task(task_id, 1)
    wm.begin_task(task_id, 'Original task', {'api_key': 'sk-fake-fixture-only'})
    content = 'full local result ' * 20000
    step = wm.add_step('read', output_data={'content': content})
    assert step['persistence']['state'] == 'PERSISTED'
    reopened = WorkingMemory(path, enabled=True).bind_task(task_id, 1)
    assert reopened.retrieve('step:' + step['step_id']).value['output']['content'] == content
    assert wm.archive_to_episodic(em)
    own = {'Authorization': 'Bearer fixture-session-one'}
    assert api.post(f'/api/ai/tasks/{task_id}/run', headers=own).get_json()['task']['status'] == 'succeeded'
    tm = TaskMemory(path, enabled=True).bind_task(task_id, 1)
    assert tm.get_task(task_id)['status'] == 'succeeded'
    assert tm.get_task_steps(task_id)
    assert tm.get_task_summary(task_id)['steps']
    assert tm.query_tasks(status='succeeded')


def test_learning_http_scoped_review_qualification_restart_and_inactive_apply(agent_client):
    api, app, path = agent_client
    task_id = submit(api)
    url = f'/api/ai/tasks/{task_id}/learning'
    own = {'Authorization': 'Bearer fixture-session-one'}
    feedback = api.post(url, json={'operation': 'feedback', 'text': 'Prefer precise caveats'}, headers=own)
    assert feedback.status_code == 200, feedback.get_json()
    made = api.post(url, json={'operation': 'suggest', 'content': {'instruction': 'Keep unknown values unknown'}}, headers=own)
    assert made.status_code == 200, made.get_json()
    item = made.get_json()['suggestion']
    review = {'operation': 'review', 'suggestion_id': item['suggestion_id'], 'expected_revision': 1, 'approved': True}
    assert api.post(url, json=review, headers=own).status_code == 403
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(1,'CTH','learning_review','write',?)", (json.dumps({'global': True}),))
    assert app.test_client().post(url, json=review, headers=own).status_code == 200
    assert api.post(url, json=review, headers=own).status_code == 409
    applied = api.post(url, json={'operation': 'apply', 'suggestion_id': item['suggestion_id'], 'expected_revision': 2}, headers=own)
    assert applied.status_code == 200, applied.get_json()
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT is_active FROM rule_version_registry WHERE version=?", ('learning_' + item['suggestion_id'],)).fetchone()[0] == 0
    from lumenis.shared.learning.loop import LearningLoop
    bound = LearningLoop(path, enabled=True).bind_source_task(task_id, 1)
    assert bound.build_prompt_context() == ''  # Inactive candidates cannot steer planning.
    # New owner reads current committed revision and can revoke an inactive candidate.
    revoked = app.test_client().post(url, json={**review, 'approved': False, 'expected_revision': 3}, headers=own)
    assert revoked.status_code == 200, revoked.get_json()
    assert revoked.get_json()['suggestions'][0]['status'] == 'rejected'
    other_task = submit(api)
    assert api.get(f'/api/ai/tasks/{other_task}/learning', headers=own).get_json()['suggestions'] == []
    with sqlite3.connect(path) as con:
        con.execute("DELETE FROM v4_member_authorizations WHERE module='learning_review'")
    assert api.post(url, json={**review, 'expected_revision': 4}, headers=own).status_code == 403


def test_local_learning_exact_prepare_confirm_and_idempotent_receipt(agent_client):
    from tests.test_agent_runtime_http_binding import _submit_local
    from lumenis.system.security import permission as p
    api, app, path = agent_client
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    task_id = _submit_local(api)
    url = f'/api/ai/tasks/{task_id}/learning'
    made = api.post(url, json={'operation': 'suggest', 'content': {'instruction': 'Keep references'}})
    assert made.status_code == 200, made.get_json()
    item = made.get_json()['suggestion']
    original = {'suggestion_id': item['suggestion_id'], 'expected_revision': 1, 'approved': True}
    assert api.post(url, json={**original, 'operation': 'review'}).status_code == 403
    prepared = api.post(url, json={**original, 'operation': 'prepare_review'})
    assert prepared.status_code == 200, prepared.get_json()
    reference = prepared.get_json()['candidate_ref']
    confirm = {**original, 'operation': 'confirm_review', 'candidate_ref': reference, 'confirm': True}
    # Explicit COMMIT capability is separate from ordinary local scope write.
    assert api.post(url, json=confirm).status_code == 403
    gate = p.get_permission_gate()
    gate.grant_permission(p.PermissionLevel.COMMIT)
    gate.grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    assert api.post(url, json={**confirm, 'candidate_ref': reference + 'bad'}).status_code == 403
    assert api.post(url, json=confirm, headers={'Origin': 'https://external.example'}).status_code == 403
    reviewed = api.post(url, json=confirm)
    assert reviewed.status_code == 200, reviewed.get_json()
    assert 'token' not in json.dumps(reviewed.get_json()).lower()
    repeated = app.test_client().post(url, json=confirm)
    assert repeated.status_code == 200 and repeated.get_json()['idempotent_hit'] is True
    apply = {'suggestion_id': item['suggestion_id'], 'expected_revision': 2}
    prepared = api.post(url, json={**apply, 'operation': 'prepare_apply'}).get_json()
    committed = api.post(url, json={**apply, 'operation': 'confirm_apply', 'candidate_ref': prepared['candidate_ref'], 'confirm': True})
    assert committed.status_code == 200, committed.get_json()
    with sqlite3.connect(path) as con:
        assert con.execute('SELECT is_active FROM rule_version_registry WHERE version=?', ('learning_' + item['suggestion_id'],)).fetchone()[0] == 0
        metadata = json.loads(con.execute("SELECT metadata_json FROM agent_learning_records WHERE learning_type='rule_suggestion'").fetchone()[0])
        assert len(metadata['transitions']) == 2
        assert all('token' not in json.dumps(t).lower() for t in metadata['transitions'])


def test_local_learning_revocation_and_storage_failure_rollback(agent_client, monkeypatch):
    from tests.test_agent_runtime_http_binding import _submit_local
    from lumenis.system.security import permission as p
    from lumenis.shared.learning.loop import LearningLoop
    api, app, path = agent_client
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    task_id = _submit_local(api)
    url = f'/api/ai/tasks/{task_id}/learning'
    item = api.post(url, json={'operation': 'suggest', 'content': {'instruction': 'Verified only'}}).get_json()['suggestion']
    base = {'suggestion_id': item['suggestion_id'], 'expected_revision': 1, 'approved': True}
    ref = api.post(url, json={**base, 'operation': 'prepare_review'}).get_json()['candidate_ref']
    confirm = {**base, 'operation': 'confirm_review', 'candidate_ref': ref, 'confirm': True}
    gate = p.get_permission_gate(); gate.grant_permission(p.PermissionLevel.COMMIT)
    gate.grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    original = LearningLoop._save_suggestion
    def save_then_revoke(self, *args, **kwargs):
        original(self, *args, **kwargs)
        gate.revoke_approval(self.learning_memory._review_admission.token)
    with monkeypatch.context() as patch:
        patch.setattr(LearningLoop, '_save_suggestion', save_then_revoke)
        denied = api.post(url, json=confirm)
        assert denied.status_code == 403, denied.get_json()
    assert api.get(url).get_json()['suggestions'][0]['revision'] == 1
    assert gate._approval_lock.acquire(timeout=0.1)
    gate._approval_lock.release()
    with sqlite3.connect(path) as con:
        con.execute("CREATE TRIGGER reject_learning BEFORE UPDATE ON agent_learning_records BEGIN SELECT RAISE(ABORT, 'storage unavailable'); END")
    assert api.post(url, json=confirm).status_code == 503
    assert api.get(url).get_json()['suggestions'][0]['revision'] == 1
    with sqlite3.connect(path) as con:
        con.execute('DROP TRIGGER reject_learning')
    assert api.post(url, json=confirm).status_code == 200
    apply = {'suggestion_id': item['suggestion_id'], 'expected_revision': 2}
    ref = api.post(url, json={**apply, 'operation': 'prepare_apply'}).get_json()['candidate_ref']
    with sqlite3.connect(path) as con:
        con.execute("CREATE TRIGGER reject_learning BEFORE UPDATE ON agent_learning_records BEGIN SELECT RAISE(ABORT, 'storage unavailable'); END")
    response = api.post(url, json={**apply, 'operation': 'confirm_apply', 'candidate_ref': ref, 'confirm': True})
    assert response.status_code == 503, response.get_json()
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT COUNT(*) FROM rule_version_registry WHERE version=?", ('learning_' + item['suggestion_id'],)).fetchone()[0] == 0


def test_full_app_basic_perimeter_local_agent_memory_and_learning(agent_client, monkeypatch):
    import app as core
    from tests.test_agent_runtime_http_binding import _submit_local
    monkeypatch.setattr(core, 'AUTH_USER', 'synthetic-basic-user')
    monkeypatch.setattr(core, 'AUTH_PASSWORD', 'synthetic-basic-pass')
    monkeypatch.setitem(core.app.config, 'LUMENIS_OPEN_WORKSPACE', True)
    api = core.app.test_client()
    task_id = _submit_local(api)
    root = f'/api/ai/tasks/{task_id}'
    assert api.get(root).status_code == 200
    assert api.get('/api/ai/tasks').status_code == 200
    run = api.post(root + '/run')
    assert run.status_code == 200, run.get_json()
    assert run.get_json()['task']['status'] == 'succeeded', run.get_json()
    assert api.get(root + '/steps').status_code == 200
    assert api.get(root + '/evidence').status_code == 200
    memory = api.post(root + '/memory', json={'key': 'style', 'value': {'text': 'brief'}, 'expected_revision': 0})
    assert memory.status_code == 200, memory.get_json()
    assert api.get(root + '/memory?key=style').get_json()['records'][0]['value'] == {'text': 'brief'}
    assert api.delete(root + '/memory', json={'key': 'style', 'expected_revision': 1}).status_code == 200
    made = api.post(root + '/learning', json={'operation': 'suggest', 'content': {'instruction': 'Use sources'}})
    assert made.status_code == 200, made.get_json()
    assert api.get(root + '/learning').status_code == 200
    assert api.get(root, headers={'Origin': 'https://external.example'}).status_code in (401,403)
    assert api.post('/api/ai/tasks', json={'input': 'unscoped generic'}).status_code in (401,403)
    pending = _submit_local(api)
    assert api.post(f'/api/ai/tasks/{pending}/cancel').get_json()['task']['status'] == 'cancelled'
    monkeypatch.setitem(core.app.config, 'LUMENIS_OPEN_WORKSPACE', False)
    assert api.get(root).status_code in (401,403)


def test_learning_commit_lease_serializes_same_gate_revoke_and_confirm(agent_client, monkeypatch):
    from contextlib import contextmanager
    from threading import Event, Thread
    from tests.test_agent_runtime_http_binding import _submit_local
    from lumenis.system.security import permission as p
    api, app, path = agent_client
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    task_id = _submit_local(api)
    url = f'/api/ai/tasks/{task_id}/learning'
    item = api.post(url, json={'operation': 'suggest', 'content': {'instruction': 'Sources'}}).get_json()['suggestion']
    base = {'suggestion_id': item['suggestion_id'], 'expected_revision': 1, 'approved': True}
    ref = api.post(url, json={**base, 'operation': 'prepare_review'}).get_json()['candidate_ref']
    confirm = {**base, 'operation': 'confirm_review', 'candidate_ref': ref, 'confirm': True}
    gate = p.get_permission_gate(); gate.grant_permission(p.PermissionLevel.COMMIT)
    gate.grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    entered, release, revoked, revoking = Event(), Event(), Event(), Event()
    original = gate.learning_candidate_commit_lease
    @contextmanager
    def held_lease(admission, *, connection):
        with original(admission, connection=connection):
            entered.set()
            assert release.wait(5)
            yield
    monkeypatch.setattr(gate, 'learning_candidate_commit_lease', held_lease)
    responses = []
    worker = Thread(target=lambda: responses.append(app.test_client().post(url, json=confirm)))
    worker.start(); assert entered.wait(5)
    def revoke():
        revoking.set(); gate.revoke_permission(p.PermissionLevel.COMMIT); revoked.set()
    revoker = Thread(target=revoke); revoker.start(); assert revoking.wait(2)
    assert not revoked.wait(0.1)  # Exact same-process lock excludes withdrawal mid-commit.
    release.set(); worker.join(5); revoker.join(5)
    assert not worker.is_alive() and not revoker.is_alive()
    assert responses[0].status_code == 200, responses[0].get_json()
    assert revoked.is_set() and not gate.has_permission(p.PermissionLevel.COMMIT)
    assert api.get(url).get_json()['suggestions'][0]['revision'] == 2
    assert api.post(url, json=confirm).get_json()['idempotent_hit'] is True
    assert gate._approval_lock.acquire(timeout=0.1); gate._approval_lock.release()


def test_full_app_real_loopback_http_learning_and_result_restart(agent_client, monkeypatch):
    """Actual TCP loopback, full app hooks, real Gate and canonical SQLite."""
    import app as core
    import urllib.request
    import urllib.error
    from threading import Thread
    from werkzeug.serving import make_server
    from lumenis.system.security import permission as p
    from ai_task_engine import reset_task_engine
    monkeypatch.setattr(core, 'AUTH_USER', 'local-http-fixture')
    monkeypatch.setattr(core, 'AUTH_PASSWORD', 'local-http-fixture-password')
    monkeypatch.setitem(core.app.config, 'LUMENIS_OPEN_WORKSPACE', True)
    gate = p.get_permission_gate()
    gate.grant_permission(p.PermissionLevel.COMMIT)
    gate.grant_permission(p.PermissionLevel.HUMAN_APPROVAL)
    server = make_server('127.0.0.1', 0, core.app)
    thread = Thread(target=server.serve_forever)
    thread.start()
    def call(path, body=None):
        request = urllib.request.Request(f'http://127.0.0.1:{server.server_port}' + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as response:
            return response.code, json.load(response)
    try:
        status, result = call('/api/ai/tasks', {'execution_mode': 'agent', 'input': 'Local HTTP closure',
            'domain_id': 'cth', 'scope': {'global_scope': True, 'subject_id': None, 'brand_focus_id': None},
            'steps': [{'skill_id': 'zbc.skill_registry_snapshot', 'input': {}}]})
        assert status == 202, result
        root = '/api/ai/tasks/' + result['task']['task_id']
        status, ran = call(root + '/run', {})
        assert status == 200 and ran['task']['status'] == 'succeeded', ran
        reset_task_engine()
        assert call(root)[1]['task']['result'] == ran['task']['result']
        status, made = call(root + '/learning', {'operation': 'suggest', 'content': {'instruction': 'Preserve provenance'}})
        assert status == 200, made
        item = made['suggestion']
        review = {'suggestion_id': item['suggestion_id'], 'expected_revision': 1, 'approved': True}
        prepared = call(root + '/learning', {**review, 'operation': 'prepare_review'})[1]
        status, reviewed = call(root + '/learning', {**review, 'operation': 'confirm_review',
            'candidate_ref': prepared['candidate_ref'], 'confirm': True})
        assert status == 200, reviewed
        apply = {'suggestion_id': item['suggestion_id'], 'expected_revision': 2}
        prepared = call(root + '/learning', {**apply, 'operation': 'prepare_apply'})[1]
        status, applied = call(root + '/learning', {**apply, 'operation': 'confirm_apply',
            'candidate_ref': prepared['candidate_ref'], 'confirm': True})
        assert status == 200 and applied['active_policy_changed'] is False, applied
        assert call(root + '/learning')[1]['suggestions'][0]['status'] == 'applied'
        with sqlite3.connect(agent_client[2]) as con:
            assert con.execute('SELECT is_active FROM rule_version_registry WHERE version=?',
                ('learning_' + item['suggestion_id'],)).fetchone()[0] == 0
    finally:
        server.shutdown(); thread.join(5); server.server_close()
        assert not thread.is_alive()
