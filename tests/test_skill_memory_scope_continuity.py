"""Skill Memory follows canonical account execution identity and current proofs."""
import json
import sqlite3

import pytest
from tests.test_skill_http_durable_identity import skill_client
from tests.test_agent_runtime_http_binding import agent_client
from tests.test_skill_scope_receipts import scoped_skill
from tests.test_agent_skill_scope_continuity import bound_agent, run, SKILL


def memory(bound_agent, task_id):
    from agent_memory.skill import SkillMemory
    return SkillMemory(bound_agent[2], enabled=True).bind_task(task_id, 1)


def test_skill_memory_reopens_signed_account_execution(bound_agent):
    task_id, row = run(bound_agent)
    records = memory(bound_agent, task_id).get_recent_executions()
    assert [r['execution_id'] for r in records] == [row['execution_id']]
    assert row['execution_id'].startswith('skillscope_agentstep_')
    other_id, other = run(bound_agent)
    assert [r['execution_id'] for r in memory(bound_agent, other_id).get_recent_executions()] == [other['execution_id']]
    assert [r['execution_id'] for r in memory(bound_agent, task_id).get_recent_executions()] == [row['execution_id']]


@pytest.mark.parametrize('change', ['child_scope', 'receipt', 'actor', 'task_scope', 'legacy_id'])
def test_skill_memory_rejects_withdrawn_or_unproven_execution(bound_agent, change):
    task_id, row = run(bound_agent)
    bound = memory(bound_agent, task_id)
    assert len(bound.get_recent_executions()) == 1
    with sqlite3.connect(bound_agent[2]) as con:
        if change == 'child_scope':
            con.execute("UPDATE v4_member_authorizations SET data_scope='{}' WHERE user_id=1 AND module=?", (SKILL,))
        elif change == 'receipt':
            con.execute("UPDATE skill_executions SET evidence_json='{}' WHERE execution_id=?", (row['execution_id'],))
        elif change == 'actor':
            con.execute("UPDATE v4_users SET status='disabled' WHERE id=1")
        elif change == 'task_scope':
            from ai_task_engine import get_task_engine
            task = get_task_engine().get_task(task_id)
            task['context']['scope']['subject_id'] = 'SCOPE-B'
            con.execute('UPDATE ai_task SET context_json=? WHERE task_id=?', (json.dumps(task['context']), task_id))
        else:
            con.execute("UPDATE skill_executions SET execution_id=?,evidence_json='{}' WHERE execution_id=?",
                        (row['execution_id'].removeprefix('skillscope_'), row['execution_id']))
    assert bound.get_recent_executions() == []


def test_skill_memory_uses_durable_gateway_plan_without_model(bound_agent, monkeypatch):
    from agent_runtime import task_binding
    from agent_memory.skill import SkillMemory
    from tests.test_agent_skill_scope_continuity import OWN, SCOPE
    # Planning alone is deterministic in this test; real HTTP, Task, Skill,
    # Permission, receipt, checkpoint and memory execution stay unmocked.
    monkeypatch.setattr(task_binding, 'Planner', lambda **kwargs: task_binding._RegisteredPlanner(
        {'steps': [{'skill_id': SKILL, 'input': {}}]}))
    api = bound_agent[0]
    created = api.post('/api/ai/tasks', headers=OWN, json={'execution_mode': 'agent',
        'input': 'Read scoped registry metadata', 'domain_id': 'cth', 'scope': SCOPE})
    assert created.status_code == 202
    task_id = created.get_json()['task']['task_id']
    ran = api.post('/api/ai/tasks/' + task_id + '/run', headers=OWN)
    assert ran.status_code == 200 and ran.get_json()['task']['status'] == 'succeeded', ran.get_json()
    records = SkillMemory(bound_agent[2], enabled=True).bind_task(task_id, 1).get_recent_executions()
    assert len(records) == 1 and records[0]['skill_id'] == SKILL


@pytest.mark.parametrize('view', ['task', 'steps', 'evidence', 'summary', 'derived'])
def test_memory_views_cannot_revive_withdrawn_child_result(bound_agent, view):
    from agent_memory.base import BaseMemoryLayer
    from agent_memory.task import TaskMemory
    from lumenis.shared.database import migrations
    assert migrations.migrate()
    with sqlite3.connect(bound_agent[2]) as con:
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(1,'CTH','agent_runtime','write',?)", (json.dumps({'global': True}),))
    task_id, row = run(bound_agent)
    tasks = TaskMemory(bound_agent[2], enabled=True).bind_task(task_id, 1)
    derived = BaseMemoryLayer(bound_agent[2], enabled=True).bind_task(task_id, 1)
    assert derived.store('child-snapshot', {'output': json.loads(row['output_json'])})
    assert tasks.get_task(task_id) and tasks.get_task_steps(task_id)
    with sqlite3.connect(bound_agent[2]) as con:
        con.execute("UPDATE v4_member_authorizations SET data_scope='{}' WHERE user_id=1 AND module=?", (SKILL,))
    if view == 'derived':
        with pytest.raises(PermissionError):
            derived.retrieve('child-snapshot')
        with pytest.raises(PermissionError):
            derived.store('late', {'output': 'not admitted'})
    else:
        result = {'task': tasks.get_task, 'steps': tasks.get_task_steps,
                  'evidence': tasks.get_task_evidence, 'summary': tasks.get_task_summary}[view](task_id)
        assert not result


def test_memory_local_workspace_keeps_existing_execution_identity(agent_client):
    from agent_memory.skill import SkillMemory
    api, app, path = agent_client
    app.config['LUMENIS_OPEN_WORKSPACE'] = True
    created = api.post('/api/ai/tasks', json={'execution_mode': 'agent', 'input': 'Read local tools',
        'domain_id': 'cth', 'scope': {'global_scope': True, 'subject_id': None, 'brand_focus_id': None},
        'steps': [{'skill_id': SKILL, 'input': {}}]})
    assert created.status_code == 202, created.get_json()
    task_id = created.get_json()['task']['task_id']
    ran = api.post('/api/ai/tasks/' + task_id + '/run')
    assert ran.status_code == 200 and ran.get_json()['task']['status'] == 'succeeded', ran.get_json()
    with app.test_request_context('/', environ_overrides={'REMOTE_ADDR': '127.0.0.1'}, headers={'Host': 'localhost'}):
        records = SkillMemory(path, enabled=True).bind_task(task_id, None).get_recent_executions()
        assert len(records) == 1 and records[0]['execution_id'].startswith('agentstep_')


def test_unexecuted_task_memory_remains_usable_without_model_or_child_output(agent_client):
    from tests.test_agent_runtime_http_binding import submit
    from agent_memory.task import TaskMemory
    task_id = submit(agent_client[0])
    task = TaskMemory(agent_client[2], enabled=True).bind_task(task_id, 1).get_task(task_id)
    assert task and task['status'] == 'pending'


@pytest.mark.parametrize('read_method', ['retrieve', 'query'])
def test_learning_cached_reads_recheck_child_scope(bound_agent, read_method):
    from lumenis.shared.learning.memory import LearningMemory
    from lumenis.shared.database import migrations
    assert migrations.migrate()
    with sqlite3.connect(bound_agent[2]) as con:
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(1,'CTH','agent_runtime','write',?)", (json.dumps({'global': True}),))
    task_id, row = run(bound_agent)
    learning = LearningMemory(bound_agent[2], enabled=True).bind_source_task(task_id, 1)
    record = learning.record_feedback('Synthetic child-derived note')
    assert record and learning.retrieve(record.key) and learning.query()
    with sqlite3.connect(bound_agent[2]) as con:
        con.execute("UPDATE v4_member_authorizations SET data_scope='{}' WHERE user_id=1 AND module=?", (SKILL,))
    with pytest.raises(PermissionError):
        getattr(learning, read_method)(record.key) if read_method == 'retrieve' else learning.query()
    with pytest.raises(PermissionError):
        learning.store('late', {'value': 'not admitted'})


def test_learning_rebinding_never_relabels_previous_cache(bound_agent):
    from lumenis.shared.learning.memory import LearningMemory
    from lumenis.shared.database import migrations
    assert migrations.migrate()
    with sqlite3.connect(bound_agent[2]) as con:
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(1,'CTH','agent_runtime','write',?)", (json.dumps({'global': True}),))
    first, _ = run(bound_agent)
    second, _ = run(bound_agent)
    learning = LearningMemory(bound_agent[2], enabled=True).bind_source_task(first, 1)
    record = learning.record_feedback('Previous task synthetic note')
    assert record and learning.retrieve(record.key)
    learning.bind_source_task(second, 1)
    assert learning.retrieve(record.key) is None and learning.query() == []


@pytest.mark.parametrize('method', ['get_task_steps', 'get_task_evidence', 'get_task_summary'])
def test_task_memory_rechecks_after_reading_payload(bound_agent, monkeypatch, method):
    from agent_memory.task import TaskMemory
    import agent_memory.task as task_module
    task_id, _ = run(bound_agent)
    memory = TaskMemory(bound_agent[2], enabled=True).bind_task(task_id, 1)
    assert memory.get_task_summary(task_id)
    observed = []
    original_connect = task_module.get_db_connection
    target = 'ai_task_step' if method == 'get_task_steps' else 'ai_task_evidence'
    def connect_with_race(*args, **kwargs):
        connection = original_connect(*args, **kwargs)
        def before_payload(sql):
            if 'SELECT * FROM ' + target + ' ' in ' '.join(sql.split()):
                observed.append(target)
                with sqlite3.connect(bound_agent[2]) as con:
                    con.execute("UPDATE v4_member_authorizations SET data_scope='{}' WHERE user_id=1 AND module=?", (SKILL,))
        # Retain the real canonical sqlite3.Connection. The trace hook only
        # schedules a concurrent withdrawal after precheck, at the payload read.
        connection.set_trace_callback(before_payload)
        return connection
    monkeypatch.setattr(task_module, 'get_db_connection', connect_with_race)
    result = getattr(memory, method)(task_id)
    assert observed == [target], 'The real payload read and withdrawal must execute'
    assert result == (None if method == 'get_task_summary' else [])
