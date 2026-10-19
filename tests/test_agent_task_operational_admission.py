"""Real canonical Permission: task metadata capability is not generic DB_WRITE."""
import json
import sqlite3
from dataclasses import replace

import pytest

from tests.test_skill_http_durable_identity import skill_client


@pytest.fixture
def admission(skill_client, tmp_path):
    api, app, path = skill_client
    from ai_task_engine import TaskEngine
    from lumenis.system.collector.guard.task_queue import TaskQueue
    from lumenis.system.security.permission import admit_task_operational_write
    with sqlite3.connect(path) as con:
        con.execute("INSERT INTO v4_member_authorizations(user_id,product_id,module,action,data_scope) VALUES(1,'CTH','agent_runtime','read',?)", (json.dumps({'global': True}),))
    context = {'actor_id': 1, 'domain_id': 'cth', 'scope': {'global_scope': True, 'subject_id': None, 'brand_focus_id': None},
               'agent_runtime': {'schema_version': 1, 'module': 'agent_runtime'}}
    engine = TaskEngine()
    task = engine.create_task('local metadata', context=context, created_by='agent_runtime')
    queue = TaskQueue(tmp_path / 'existing-queue.sqlite')
    queued = queue.enqueue('agent_runtime', {'task_id': task['task_id'], 'actor_id': 1})
    attempt = queue.dequeue(worker_id='worker', task_id=queued)
    allowed = admit_task_operational_write(task_id=task['task_id'], actor_id=1, queue=queue, attempt=attempt)
    yield allowed, engine, path, context
    queue.close()


def test_actual_permission_commits_task_result_with_checkpoint(admission):
    allowed, engine, path, context = admission
    from agent_runtime.durable_adapter import DurableExecutionAdapter
    owner = DurableExecutionAdapter(task_engine=engine, operational_admission=allowed)
    owner.finalize_task(allowed.task_id, 'completed', result={'local_count': 1},
                        step_index=1, plan_snapshot={'steps': []}, context=context)
    row = engine.get_task(allowed.task_id)
    assert row['status'] == 'succeeded' and row['result'] == {'local_count': 1}
    assert owner.get_checkpoints(allowed.task_id)[0].state == 'completed'


def test_capability_rejects_business_table_ownership_fields_and_forgery(admission):
    allowed, engine, path, context = admission
    assert not allowed.check('notes', fields={'content'}).allowed
    assert not allowed.check('ai_task', fields={'created_by'}).allowed
    assert not allowed.check('ai_task', fields={'context_json'}).allowed
    assert not replace(allowed, _seal=None).check('ai_task', fields={'status'}).allowed
    assert not replace(allowed, actor_id=2).check('ai_task', fields={'status'}).allowed
    assert not replace(allowed, run_id='wrong').check('ai_task', fields={'status'}).allowed


@pytest.mark.parametrize('mutation', ['revoke', 'inactive', 'scope', 'stale'])
def test_late_metadata_commit_denied_after_authority_changes(admission, mutation):
    allowed, engine, path, context = admission
    if mutation == 'stale':
        assert allowed.queue.ack(allowed.queue_task_id, run_id=allowed.run_id,
                                worker_id=allowed.worker_id, lease_owner=allowed.lease_owner)
    else:
        with sqlite3.connect(path) as con:
            if mutation == 'revoke':
                con.execute("DELETE FROM v4_member_authorizations WHERE module='agent_runtime'")
            elif mutation == 'inactive':
                con.execute("UPDATE v4_users SET status='disabled' WHERE id=1")
            else:
                con.execute("UPDATE ai_task SET context_json='{}' WHERE task_id=?", (allowed.task_id,))
    from agent_runtime.durable_adapter import DurableExecutionAdapter
    owner = DurableExecutionAdapter(task_engine=engine, operational_admission=allowed)
    with pytest.raises(PermissionError):
        owner.finalize_task(allowed.task_id, 'completed', result={'must_not_commit': True}, step_index=1)
    assert engine.get_task(allowed.task_id)['status'] == 'pending'


def test_cancellation_cannot_be_overwritten_with_operational_capability(admission):
    allowed, engine, path, context = admission
    with sqlite3.connect(path) as con:
        con.execute("UPDATE ai_task SET status='cancelled',error='user stopped' WHERE task_id=?", (allowed.task_id,))
    from agent_runtime.durable_adapter import DurableExecutionAdapter
    owner = DurableExecutionAdapter(task_engine=engine, operational_admission=allowed)
    with pytest.raises(RuntimeError):
        owner.finalize_task(allowed.task_id, 'completed', result={'late': True}, step_index=1)
    assert engine.get_task(allowed.task_id)['status'] == 'cancelled'
