"""Real local HTTP -> Skill -> Gate -> signed Evidence -> reopened status scope.

Fixture identities/local registry read only; no model or external MCP capability claim.
"""
import json
import sqlite3
from types import SimpleNamespace

import pytest

from tests.test_skill_http_durable_identity import skill_client


@pytest.fixture
def scoped_skill(skill_client, monkeypatch):
    api, app, path = skill_client
    monkeypatch.setenv('LUMENIS_EVIDENCE_HMAC_KEY_RING', json.dumps({'scope-test': 'public-local-fixture-key'}))
    monkeypatch.setenv('LUMENIS_EVIDENCE_HMAC_ACTIVE_KEY_ID', 'scope-test')
    import lumenis_skill_adapter
    monkeypatch.setattr(lumenis_skill_adapter, 'get_skill_adapter', lambda: SimpleNamespace(available=False))
    import subject_registry
    from lumenis.shared.evidence import store
    with sqlite3.connect(path) as con:
        store.ensure_evidence_schema(con)
        subject_registry.ensure_schema(con)
        con.execute("UPDATE v4_member_authorizations SET data_scope=? WHERE user_id=1", (json.dumps({'global': True}),))
        for subject in ('SCOPE-A', 'SCOPE-B'):
            con.execute("""INSERT INTO lumenis_subject_registry(subject_id,domain_id,subject_type,name_en,name_zh,
                name_en_norm,name_zh_norm,industry,keywords_json,status,created_at,updated_at)
                VALUES(?,'CTH','company',?,?,?,?,'retail','[]','configured','2026-10-17','2026-10-17')""",
                (subject, subject, subject, subject.lower(), subject))
    return api, app, path


def execute(api, scope='global', **extra):
    body = {'skill_id': 'zbc.skill_registry_snapshot', 'task': 'Read local registered capabilities',
            'product': 'CTH', 'action_type': 'READ', **extra}
    if scope is not None:
        body['scope'] = {'global_scope': True} if scope == 'global' else scope
    return api.post('/api/ai/tasks', headers={'Authorization': 'Bearer fixture-session-one'}, json=body)


def read_row(identifier):
    from lumenis.shared.agents.skills.execution import query_executions
    return query_executions(execution_id=identifier, strict=True)[0]


@pytest.mark.parametrize('scope', [{'global_scope': True}, {'subject_id': 'SCOPE-A', 'global_scope': False}])
def test_direct_http_scope_receipt_reopens(scoped_skill, scope):
    api, app, path = scoped_skill
    result = execute(api, scope)
    assert result.status_code == 200, result.get_json()
    identifier = result.get_json()['execution_id']
    row = read_row(identifier)
    from lumenis.shared.agents.skills.execution import verified_execution_scope
    admitted = verified_execution_scope(row, {'id': 1})
    assert admitted and admitted['global_scope'] == scope['global_scope']
    assert admitted['subject_id'] == scope.get('subject_id')
    assert verified_execution_scope(row, {'id': 2}) is None
    reopened = app.test_client().get('/api/ai/tasks/' + identifier,
        headers={'Authorization': 'Bearer fixture-session-one'})
    assert reopened.status_code == 200
    assert reopened.get_json()['notification']['external_delivery'] is False
    assert reopened.get_json()['task']['evaluation_json']
    assert json.loads(row['evaluation_json'])['validation_status'] == 'pending_manual_validation'
    with sqlite3.connect(path) as con:
        con.execute("UPDATE v4_member_authorizations SET data_scope=? WHERE user_id=1", (json.dumps({'subject_ids': ['SCOPE-B']}),))
    assert verified_execution_scope(read_row(identifier), {'id': 1}) is None


def test_missing_scope_stays_unknown_even_if_payload_claims_proof(scoped_skill):
    api, app, path = scoped_skill
    result = execute(api, None, input={'global_scope': True, 'scope_receipt': {'version': 1, 'evidence_id': 1}})
    assert result.status_code == 200, result.get_json()
    row = read_row(result.get_json()['execution_id'])
    from lumenis.shared.agents.skills.execution import verified_execution_scope
    assert 'scope_receipt' not in json.loads(row['evidence_json'])
    assert verified_execution_scope(row, {'id': 1}) is None


@pytest.mark.parametrize('scope', [{}, {'subject_id': 'unknown'}, {'global_scope': 'true'},
    {'subject_id': 'SCOPE-A', 'global_scope': True}, {'global_scope': True, 'scope_receipt': 'fake'},
    {'domain_id': 'zbmp', 'global_scope': True}])
def test_invalid_explicit_scope_denied_before_handler(scoped_skill, monkeypatch, scope):
    from lumenis.shared.agents.skills import execution
    monkeypatch.setattr(execution, 'execute_skill', lambda *a, **kw: pytest.fail('handler must not run'))
    result = execute(scoped_skill[0], scope)
    assert result.status_code == 409, result.get_json()
    assert result.get_json()['status'] == 'rejected'


@pytest.mark.parametrize('mutation', ['result', 'actor', 'scope', 'evidence_signature', 'source_revoked'])
def test_tampered_receipt_and_source_revocation_rejected(scoped_skill, mutation):
    api, app, path = scoped_skill
    response = execute(api, {'subject_id': 'SCOPE-A'})
    assert response.status_code == 200, response.get_json()
    identifier = response.get_json()['execution_id']
    row = read_row(identifier)
    proof_id = json.loads(row['evidence_json'])['scope_receipt']['evidence_id']
    from lumenis.shared.agents.skills.execution import verified_execution_scope
    assert verified_execution_scope(row, {'id': 1})
    with sqlite3.connect(path) as con:
        if mutation == 'result':
            con.execute("UPDATE skill_executions SET output_json='{}' WHERE execution_id=?", (identifier,))
        elif mutation == 'actor':
            con.execute("UPDATE skill_executions SET user_id=2 WHERE execution_id=?", (identifier,))
        elif mutation == 'scope':
            raw = con.execute('SELECT inputs_json FROM app_evidence_records WHERE id=?', (proof_id,)).fetchone()[0]
            data = json.loads(raw); data['scope_receipt']['subject_id'] = 'SCOPE-B'
            con.execute('UPDATE app_evidence_records SET inputs_json=? WHERE id=?', (json.dumps(data), proof_id))
        elif mutation == 'evidence_signature':
            con.execute("UPDATE app_evidence_records SET integrity_digest='invalid' WHERE id=?", (proof_id,))
        else:
            con.execute("UPDATE lumenis_subject_registry SET status='disabled' WHERE subject_id='SCOPE-A'")
    assert verified_execution_scope(read_row(identifier), {'id': 1}) is None


def test_missing_signing_key_fails_trace_finalization_without_partial_receipt(scoped_skill, monkeypatch):
    monkeypatch.delenv('LUMENIS_EVIDENCE_HMAC_KEY_RING')
    response = execute(scoped_skill[0])
    assert response.status_code == 409
    assert response.get_json()['error'] == 'SKILL_EXECUTION_TRACE_FINALIZATION_FAILED'
    from lumenis.shared.agents.skills.execution import query_executions
    assert query_executions(execution_id=response.get_json()['execution_id'], strict=True) == []


def test_background_scope_recovered_and_finalized(scoped_skill, monkeypatch, tmp_path):
    from lumenis.shared.agents.skills import execution
    from lumenis.system.collector.guard import task_queue
    monkeypatch.setattr(task_queue, 'DEFAULT_PATH', tmp_path / 'scope-queue.sqlite')
    monkeypatch.setattr(execution, 'start_registered_skill_job', lambda identifier: None)
    api, app, path = scoped_skill
    response = execute(api, {'subject_id': 'SCOPE-A'}, background=True)
    assert response.status_code == 202, response.get_json()
    identifier = response.get_json()['execution_id']
    pending = read_row(identifier)
    assert execution._queued_execution_scope(pending)['subject_id'] == 'SCOPE-A'
    assert execution.verified_execution_scope(pending, {'id': 1}) is None
    completed = execution.run_registered_skill_job(identifier)
    assert completed['status'] == 'completed', completed
    assert execution.verified_execution_scope(completed, {'id': 1})['subject_id'] == 'SCOPE-A'
    monkeypatch.setattr(execution, 'execute_skill', lambda *a, **kw: pytest.fail('terminal replay'))
    assert execution.run_registered_skill_job(identifier)['status'] == 'completed'


@pytest.mark.parametrize('mutation', ['input', 'proof', 'scope_revoke'])
def test_background_scope_tamper_fails_before_handler(scoped_skill, monkeypatch, mutation):
    from lumenis.shared.agents.skills import execution
    monkeypatch.setattr(execution, 'start_registered_skill_job', lambda identifier: None)
    api, app, path = scoped_skill
    response = execute(api, {'subject_id': 'SCOPE-A'}, background=True)
    assert response.status_code == 202, response.get_json()
    identifier = response.get_json()['execution_id']
    with sqlite3.connect(path) as con:
        if mutation == 'input':
            con.execute("UPDATE skill_executions SET input_json='{} ' WHERE execution_id=?", (identifier,))
        elif mutation == 'proof':
            con.execute("UPDATE skill_executions SET evidence_json='{}' WHERE execution_id=?", (identifier,))
        else:
            con.execute("UPDATE v4_member_authorizations SET data_scope=? WHERE user_id=1", (json.dumps({'subject_ids': ['SCOPE-B']}),))
    monkeypatch.setattr(execution, 'execute_skill', lambda *a, **kw: pytest.fail('unauthorized handler'))
    assert execution.run_registered_skill_job(identifier)['status'] == 'rejected'


def test_restart_http_sh06_uses_signed_scope_and_hides_other_focus(scoped_skill):
    import os
    import subprocess
    import sys
    api, app, path = scoped_skill
    response = execute(api, {'subject_id': 'SCOPE-A'})
    assert response.status_code == 200, response.get_json()
    identifier = response.get_json()['execution_id']
    with sqlite3.connect(path) as con:
        con.executemany("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) "
                    "VALUES(1,'CTH',?,'read',?)", [(module, json.dumps({'global': True}))
                        for module in ('operational_inbox', 'subject_registry')])
    # New Python interpreter, fresh Flask app, fresh Gate and account/session read.
    code = r'''
import json, sys
from flask import Flask
from ai_api import bp
from experience_runtime import experience_bp
from lumenis.system.security import permission
permission._TESTING_BYPASS_ENABLED = False
app = Flask(__name__); app.register_blueprint(bp); app.register_blueprint(experience_bp)
client = app.test_client()
headers = {'Authorization': 'Bearer fixture-session-one', 'X-Lumenis-Context-Mode': 'FOCUS',
           'X-Domain-Id': 'CTH', 'X-Subject-ID': 'SCOPE-A'}
matched = client.get('/api/experience/screen/SH-06', headers=headers)
headers['X-Subject-ID'] = 'SCOPE-B'
other = client.get('/api/experience/screen/SH-06', headers=headers)
headers['Authorization'] = 'Bearer fixture-session-two'
foreign = client.get('/api/experience/screen/SH-06', headers=headers)
print('SCOPE_RESULT=' + json.dumps({'matching': matched.get_json(), 'other': other.get_json(),
                                  'foreign': foreign.get_json()}))
'''
    env = dict(os.environ)
    env.pop('PERMISSION_GATE_TESTING', None)
    done = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, done.stderr
    output = json.loads(next(line[len('SCOPE_RESULT='):] for line in done.stdout.splitlines() if line.startswith('SCOPE_RESULT=')))
    path.parent.joinpath('restart_sh06_response.json').write_text(json.dumps(output, indent=2))
    notifications = output['matching'].get('data', {}).get('notifications', [])
    assert len(notifications) == 1, output
    assert notifications[0]['return_ref'] == '/api/ai/tasks/' + identifier
    assert notifications[0]['scope_evidence']['stored_scope']['id'] == 'SCOPE-A'
    assert notifications[0]['external_delivery'] is False
    assert not output['other'].get('data', {}).get('notifications')
    assert not output['foreign'].get('data', {}).get('notifications')


def test_background_scoped_request_survives_process_restart(scoped_skill, monkeypatch, tmp_path):
    import os
    import subprocess
    import sys
    from lumenis.shared.agents.skills import execution
    monkeypatch.setattr(execution, 'start_registered_skill_job', lambda identifier: None)
    response = execute(scoped_skill[0], {'subject_id': 'SCOPE-A'}, background=True)
    assert response.status_code == 202, response.get_json()
    identifier = response.get_json()['execution_id']
    code = r'''
import sys
from lumenis.system.collector.guard import task_queue
from lumenis.shared.agents.skills.execution import run_registered_skill_job, verified_execution_scope
from lumenis.system.security import permission
permission._TESTING_BYPASS_ENABLED = False
task_queue.DEFAULT_PATH = sys.argv[2]
row = run_registered_skill_job(sys.argv[1])
assert row['status'] == 'completed', row
assert verified_execution_scope(row, {'id': 1})['subject_id'] == 'SCOPE-A'
print('RESTARTED_SCOPE_COMPLETE')
'''
    done = subprocess.run([sys.executable, '-c', code, identifier, str(tmp_path / 'restarted-queue.db')],
                          env=dict(os.environ), capture_output=True, text=True, timeout=30)
    assert done.returncode == 0, done.stdout + done.stderr
    tmp_path.joinpath('background_restart.txt').write_text(done.stdout + done.stderr)
    assert 'RESTARTED_SCOPE_COMPLETE' in done.stdout
    assert execution.verified_execution_scope(read_row(identifier), {'id': 1})['subject_id'] == 'SCOPE-A'


def test_scope_revoked_during_handler_cannot_finalize(scoped_skill, monkeypatch):
    from lumenis.shared.agents.skills import execution
    original = execution._execute_builtin_local
    def revoke(ctx, meta):
        result = original(ctx, meta)
        with sqlite3.connect(scoped_skill[2]) as con:
            con.execute("UPDATE v4_member_authorizations SET data_scope='{}' WHERE user_id=1")
        return result
    monkeypatch.setattr(execution, '_execute_builtin_local', revoke)
    response = execute(scoped_skill[0], {'subject_id': 'SCOPE-A'})
    assert response.status_code == 409
    assert response.get_json()['error'] == 'SKILL_EXECUTION_TRACE_FINALIZATION_FAILED'
    assert execution.query_executions(execution_id=response.get_json()['execution_id']) == []


def test_bmp_focus_has_same_signed_scope_contract(scoped_skill):
    api, app, path = scoped_skill
    with sqlite3.connect(path) as con:
        con.execute("UPDATE skills_registry SET product='SHARED' WHERE skill_id='zbc.skill_registry_snapshot'")
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) "
                    "VALUES(1,'ZBMP','zbc.skill_registry_snapshot','read',?)", (json.dumps({'brand_focus_ids': ['BRAND-A']}),))
        con.execute("""INSERT INTO lumenis_subject_registry(subject_id,brand_focus_id,domain_id,subject_type,
            name_en,name_zh,name_en_norm,name_zh_norm,industry,keywords_json,status,created_at,updated_at)
            VALUES('BMP-A','BRAND-A','BMP','brand','Brand A','Brand A','brand a','Brand A',
                   'retail','[]','configured','2026-10-17','2026-10-17')""")
    response = execute(api, {'brand_focus_id': 'BRAND-A'}, product='BMP')
    assert response.status_code == 200, response.get_json()
    from lumenis.shared.agents.skills.execution import verified_execution_scope
    scope = verified_execution_scope(read_row(response.get_json()['execution_id']), {'id': 1})
    assert scope['domain_id'] == 'zbmp' and scope['brand_focus_id'] == 'BRAND-A'
    assert scope['subject_id'] is None and scope['global_scope'] is False


@pytest.mark.parametrize('background', [False, True])
def test_http_result_and_pending_detail_recheck_current_scope(scoped_skill, monkeypatch, background):
    from lumenis.shared.agents.skills import execution
    monkeypatch.setattr(execution, 'start_registered_skill_job', lambda identifier: None)
    api, app, path = scoped_skill
    response = execute(api, {'subject_id': 'SCOPE-A'}, background=background)
    assert response.status_code == (202 if background else 200), response.get_json()
    identifier = response.get_json()['execution_id']
    headers = {'Authorization': 'Bearer fixture-session-one'}
    assert api.get('/api/ai/tasks/' + identifier, headers=headers).status_code == 200
    with sqlite3.connect(path) as con:
        con.execute("UPDATE v4_member_authorizations SET data_scope=? WHERE user_id=1", (json.dumps({'subject_ids': ['SCOPE-B']}),))
    assert api.get('/api/ai/tasks/' + identifier, headers=headers).status_code == 404
    assert not api.get('/api/ai/tasks', headers=headers).get_json()['notifications']


def test_deleted_direct_scope_receipt_does_not_downgrade_to_legacy_access(scoped_skill):
    api, app, path = scoped_skill
    response = execute(api, {'subject_id': 'SCOPE-A'})
    assert response.status_code == 200, response.get_json()
    identifier = response.get_json()['execution_id']
    with sqlite3.connect(path) as con:
        con.execute("UPDATE skill_executions SET evidence_json='{}' WHERE execution_id=?", (identifier,))
    assert api.get('/api/ai/tasks/' + identifier,
                   headers={'Authorization': 'Bearer fixture-session-one'}).status_code == 404
