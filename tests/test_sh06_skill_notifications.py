"""Projection boundaries; receipt cryptography belongs to the Skill Owner suite."""
import pytest
from tests.test_saved_document_workflow import workspace

import experience_screens as screens


@pytest.fixture
def owner(monkeypatch):
    from lumenis.auth import service
    from lumenis.shared.agents.skills import execution
    import ai_api
    row = {'execution_id': 'skill-1', 'status': 'completed', 'user_id': 4,
           'task': 'Reviewed local result', 'output_json': '{}'}
    state = {'actor': {'id': 4}, 'allowed': True, 'proof': {
        'domain_id': 'cth', 'subject_id': 'site-a', 'brand_focus_id': None,
        'global_scope': False, 'evidence_id': 19, 'digest': 'a' * 64}}
    monkeypatch.setattr(service, 'get_current_user', lambda **kw: state['actor'])
    monkeypatch.setattr(execution, 'query_executions', lambda **kw: [row])
    monkeypatch.setattr(execution, 'verified_execution_scope', lambda row, actor: state['proof'])
    monkeypatch.setattr(ai_api, '_task_row_read_allowed', lambda row, **kw: state['allowed'])
    return state


def test_matching_signed_scope_has_typed_notification(owner):
    binding = {'canonical_scope': 'FOCUS', 'domain_id': 'CTH', 'subject_id': 'site-a'}
    [notice] = screens._sh06_skill_notifications(binding)
    assert notice['task_kind'] == 'SKILL_EXECUTION'
    assert notice['external_delivery'] is False
    assert notice['scope_evidence']['contract'] == 'skill-execution-scope-v1'
    assert 'chain_length' not in notice['scope_evidence']
    assert notice['return_ref'] == '/api/ai/tasks/skill-1'


@pytest.mark.parametrize('mutation', ['missing', 'actor', 'denied', 'foreign', 'global'])
def test_unknown_or_foreign_scope_is_not_projected(owner, mutation):
    binding = {'canonical_scope': 'FOCUS', 'domain_id': 'CTH', 'subject_id': 'site-a'}
    if mutation == 'missing':
        owner['proof'] = None
    elif mutation == 'actor':
        owner['actor'] = None
    elif mutation == 'denied':
        owner['allowed'] = False
    elif mutation == 'foreign':
        owner['proof']['subject_id'] = 'site-b'
    else:
        owner['proof']['global_scope'] = True
    assert screens._sh06_skill_notifications(binding) == []


def test_explicit_global_receipt_matches_global_view(owner):
    owner['proof'].update(global_scope=True, subject_id=None)
    assert len(screens._sh06_skill_notifications({'canonical_scope': 'GLOBAL_ALL'})) == 1


def test_activity_timeline_uses_only_authorized_projection():
    inbox = {'data': {'notifications': [{
        'event': {'timestamp': '2026-10-17T05:00:00Z', 'title': 'Allowed', 'message': 'completed'},
        'terminal': True, 'return_ref': '/api/ai/tasks/allowed',
    }]}}
    value = screens._task_timeline(inbox=inbox)
    assert 'Allowed' in str(value)
    assert '/api/ai/tasks/allowed' in str(value)
    assert screens._task_timeline(inbox={})['items'] == []


def test_local_agent_activity_binding_uses_original_scope_gate(workspace):
    from experience_runtime import _sh06_read_scope
    binding, error = _sh06_read_scope(module='skills')
    assert error is None
    assert binding['actor_scope'] == 'sealed_local'
    assert binding['canonical_scope'] == 'GLOBAL_ALL'
    workspace['app'].config['LUMENIS_OPEN_WORKSPACE'] = False
    binding, error = _sh06_read_scope(module='skills')
    assert binding is None and error == 'AUTH_REQUIRED'
