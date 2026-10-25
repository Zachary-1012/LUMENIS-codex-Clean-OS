"""Production binding for the existing TaskEngine, AgentLoop and leased queue.

No second task store, scheduler, conversation, permission owner or provider.
Only explicitly registered, bounded local read/draft tools are admitted here.
"""
from __future__ import annotations

import hashlib
import json
import threading
import os
from functools import partial
from dataclasses import replace

from .planner import Plan, PlanStep, Planner
from .loop import AgentConfig, AgentLoop
from .durable_adapter import DurableExecutionAdapter


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def _workspace_binding():
    from lumenis.shared.database import main_db_path
    return _digest({'database': os.path.realpath(main_db_path()), 'principal': 'workspace:local'})


def _conversation_snapshot(task, current):
    """Read explicit same-owner task links; a conversation never grants a tool."""
    from lumenis.ai_hub import conversations
    from lumenis.shared.database import get_repository
    ref = ('actor:' + str(current['actor_id']) if current['actor_id'] is not None else 'workspace:local')
    workspace = _workspace_binding()
    with get_repository().connection(read_only=True, wal=False) as con:
        if not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='ai_conversation_turns'").fetchone():
            return None
        links = con.execute('''SELECT t.turn_id,t.conversation_id,t.content_json FROM ai_conversation_turns t
            JOIN ai_conversations c ON c.conversation_id=t.conversation_id
            WHERE t.task_id=? AND t.origin_kind='task_projection' AND c.actor_ref=? AND c.workspace_binding=?
            ORDER BY t.conversation_id,t.sequence''', (task['task_id'], ref, workspace)).fetchall()
        if not links:
            return None
        states, seen = [], set()
        try:
            for link in links:
                row = conversations._authorize(con, link['conversation_id'], current['actor'])
                if row['conversation_id'] in seen:
                    continue
                seen.add(row['conversation_id'])
                working = conversations.task_working_context(con, row['conversation_id'], current['actor'])
                states.append({**working,
                    'link_turn_id': link['turn_id'], 'link_sha256': _digest(json.loads(link['content_json'])),
                })
            for state in states:
                conversations._authorize(con, state['conversation_id'], current['actor'])
        except PermissionError as exc:
            raise PermissionError('AGENT_CONVERSATION_CONTEXT_ACCESS_DENIED') from exc
    snapshot = {'schema': 'agent-conversation-context/v1', 'task_id': task['task_id'],
                'actor_ref': ref, 'workspace_binding': workspace, 'conversations': states,
                'truth_kind': 'explicit_human_task_input', 'permission_grant': False,
                'external_source_content': 'NOT_READ'}
    snapshot['sha256'] = _digest(snapshot)
    return snapshot


def _assert_conversation_snapshot(task_id, expected_sha256):
    from agent_capability.formation import FormationError
    from ai_task_engine import get_task_engine
    task = get_task_engine().get_task(task_id)
    if task is None:
        raise PermissionError('AGENT_TASK_NOT_FOUND')
    if task.get('status') == 'cancelled':
        raise FormationError('USER_CANCELLED', changed_fields=('task_status',))
    current = authorized_context(task)
    snapshot = _conversation_snapshot(task, current)
    if (snapshot['sha256'] if snapshot else None) != expected_sha256:
        raise FormationError('AGENT_CONVERSATION_CONTEXT_CHANGED', changed_fields=('conversation_context',))
    return snapshot


def _committed_step_receipts(task, current):
    """Only references to verified committed outputs, never instructions to replay."""
    from ai_task_engine import get_task_engine
    authorize_task_result_read(task, current['actor'])
    checkpoints = DurableExecutionAdapter._db_checkpoints(get_task_engine().get_steps(task['task_id']))
    receipts = {}
    for checkpoint in checkpoints:
        for step in checkpoint.plan_snapshot.get('steps', []):
            if step.get('status') != 'completed':
                continue
            result = step.get('result') or {}
            inner = result if 'skill_execution_id' in result else result.get('result') or {}
            identifier = inner.get('skill_execution_id') if isinstance(inner, dict) else None
            if identifier:
                receipts[identifier] = {'execution_id': identifier, 'tool': step.get('tool'),
                    'input_sha256': _digest(step.get('params', {})), 'result_sha256': _digest(result),
                    'state': 'COMMITTED_ALREADY_EXECUTED', 'replay_allowed': False}
    return [receipts[key] for key in sorted(receipts)]


def authorized_context(task, actor=None, *, connection=None):
    """Re-open original account or current server-sealed workspace identity."""
    from account.models import get_db
    from lumenis.system.security.permission import (check_actor_scope_permission,
        resolve_local_workspace_principal, _is_server_local_workspace_principal,
        check_local_workspace_scope_permission)
    context = task.get('context') or {}
    contract = context.get('agent_runtime') or {}
    if task.get('created_by') != 'agent_runtime' or contract.get('schema_version') != 1:
        raise PermissionError('AGENT_TASK_OWNER_INVALID')
    scope = context.get('scope') or {}
    if not AgentLoop._valid_typed_scope(context.get('domain_id'), scope):
        raise PermissionError('AGENT_TASK_SCOPE_INVALID')
    actor_id = context.get('actor_id')
    if contract.get('principal_kind') == 'local_workspace':
        principal = resolve_local_workspace_principal(module='skills', action='read')
        if (actor_id is not None or principal is None
                or (actor is not None and not _is_server_local_workspace_principal(actor))
                or contract.get('principal_ref') != 'workspace:local'
                or contract.get('workspace_binding') != _workspace_binding()):
            raise PermissionError('AGENT_WORKSPACE_IDENTITY_DENIED')
        actor = principal
        decision = check_local_workspace_scope_permission(principal, domain_id=context['domain_id'],
            action='read', module='skills', connection=connection, **scope)
    else:
        if type(actor_id) is not int or (actor is not None and (not isinstance(actor, dict) or actor.get('id') != actor_id)):
            raise PermissionError('AGENT_TASK_ACTOR_MISMATCH')
        con = connection or get_db()
        try:
            row = con.execute('SELECT id,role,status FROM v4_users WHERE id=?', (actor_id,)).fetchone()
        finally:
            if connection is None:
                con.close()
        if not row or row['status'] != 'active':
            raise PermissionError('AGENT_TASK_ACTOR_INACTIVE')
        actor = dict(row)
        decision = check_actor_scope_permission(actor, domain_id=context['domain_id'], action='read',
            module='agent_runtime', connection=connection, **scope)
    if not decision.allowed:
        raise PermissionError('AGENT_TASK_SCOPE_DENIED')
    domain = context['domain_id']
    return {**context, 'actor': actor, 'module': 'agent_runtime', 'domain': domain,
            'product': 'CTH' if domain == 'cth' else 'ZBMP',
            'role': 'cth_analyst' if domain == 'cth' else 'zbmp_analyst'}


def authorize_task_result_read(task, actor=None):
    """Revalidate saved child Skill proofs before exposing account Agent data."""
    context = authorized_context(task, actor)
    _conversation_snapshot(task, context)
    if context['actor_id'] is None:
        return True  # Existing sealed local-workspace boundary stays unchanged.
    from ai_task_engine import get_task_engine
    from lumenis.shared.agents.skills.execution import query_executions, verified_execution_scope
    from .durable_adapter import _sanitize_checkpoint_value
    admitted = {}
    safe_errors = {'AGENT_SKILL_RESULT_UNAVAILABLE', 'TOOL_STEP_TIMEOUT', 'USER_CANCELLED',
                   'AGENT_REGISTERED_TOOL_CHANGED', 'AGENT_TOOL_SCHEMA_INVALID',
                   'AGENT_CONVERSATION_CONTEXT_CHANGED', 'AGENT_CONVERSATION_CONTEXT_ACCESS_DENIED'}

    def verify_failure_scope(step, identifier=None):
        from lumenis.system.security.permission import check_actor_scope_permission
        expected = 'skillscope_agentstep_' + _digest({'task': task['task_id'],
            'skill': step.get('tool'), 'inputs': step.get('params', {})})[:32]
        decision = check_actor_scope_permission(context['actor'], module=step.get('tool'),
            action='read', domain_id=context['domain_id'], **context['scope'])
        if ((identifier is not None and identifier != expected)
                or step.get('tool') not in context['agent_runtime']['registry_bindings']
                or not decision.allowed or decision.verification_state != 'verified'):
            raise PermissionError('AGENT_RESULT_SKILL_SCOPE_DENIED')

    def verify_step(step):
        dispatched = step.get('result') if isinstance(step, dict) else None
        output = (dispatched if isinstance(dispatched, dict) and 'skill_execution_id' in dispatched
                  else dispatched.get('result') if isinstance(dispatched, dict) else None)
        identifier = output.get('skill_execution_id') if isinstance(output, dict) else None
        if isinstance(output, dict):
            if (set(output) - {'success', 'result', 'error', 'skill_execution_id', 'duration_ms'}
                    or ('duration_ms' in output and type(output['duration_ms']) not in (int, float))
                    or (output.get('success') is True and (output.get('error') is not None or step.get('error') is not None))):
                raise PermissionError('AGENT_RESULT_SKILL_PROOF_REQUIRED')
            if dispatched is not output and (set(dispatched) - {'success', 'result', 'error', 'duration_ms'}
                    or dispatched.get('success') is not output.get('success')
                    or dispatched.get('error') != output.get('error')):
                raise PermissionError('AGENT_RESULT_SKILL_PROOF_REQUIRED')
        if (isinstance(output, dict) and output.get('success') is False
                and output.get('result') is None
                and output.get('error') == 'AGENT_SKILL_RESULT_UNAVAILABLE'
                and set(output) <= {'success', 'result', 'error', 'skill_execution_id', 'duration_ms'}
                and step.get('error') in (None, 'AGENT_SKILL_RESULT_UNAVAILABLE')):
            # This is a data-free server failure acknowledgement, not a child
            # result. Keep ordinary failures readable while rechecking the exact
            # attempted Skill scope. Historical failure payloads cannot use it.
            verify_failure_scope(step, identifier)
            return
        if (not isinstance(step, dict) or not isinstance(identifier, str)
                or output.get('success') is not True):
            raise PermissionError('AGENT_RESULT_SKILL_PROOF_REQUIRED')
        if identifier not in admitted:
            rows = query_executions(execution_id=identifier, limit=1, strict=True)
            row = rows[0] if rows else None
            scope = verified_execution_scope(row, context['actor']) if row else None
            if not scope:
                raise PermissionError('AGENT_RESULT_SKILL_SCOPE_DENIED')
            admitted[identifier] = (row, scope)
        row, scope = admitted[identifier]
        expected = 'skillscope_agentstep_' + _digest({'task': task['task_id'],
            'skill': step.get('tool'), 'inputs': json.loads(row['input_json'])})[:32]
        if (identifier != expected or row['skill_id'] != step.get('tool')
                or scope['domain_id'] != context['domain_id']
                or any(scope[key] != context['scope'][key] for key in
                       ('subject_id', 'brand_focus_id', 'global_scope'))
                or output.get('result') != _sanitize_checkpoint_value(json.loads(row['output_json']))[0]):
            raise PermissionError('AGENT_RESULT_SKILL_BINDING_CHANGED')

    # Status is not proof that a checkpoint is data-free. Failed, timed-out,
    # cancelled and in-progress records can retain child output, including the
    # separate metadata copy written by complete_step. Verify each copy.
    raw_steps = get_task_engine().get_steps(task['task_id'])
    if any(step.get('error') is not None and step['error'] not in safe_errors for step in raw_steps):
        raise PermissionError('AGENT_RESULT_SKILL_PROOF_REQUIRED')
    checkpoints = DurableExecutionAdapter._db_checkpoints(raw_steps)
    for checkpoint in checkpoints:
        # Metadata is operational state, never an unsigned alternate output bag.
        metadata = checkpoint.metadata
        metric_keys = {'elapsed_seconds', 'estimated_cost', 'steps_started', 'replans'}
        limit_keys = {'max_steps', 'max_time_seconds', 'max_cost', 'max_retries',
                      'max_replans', 'step_timeout_seconds'}
        if (set(metadata) - metric_keys - {'limits', 'resumable', 'non_resumable_reason', 'result', 'error'}
                or any(type(metadata[key]) not in (int, float) for key in metric_keys & set(metadata))
                or ('resumable' in metadata and type(metadata['resumable']) is not bool)
                or metadata.get('non_resumable_reason') not in (None, 'sensitive checkpoint material omitted',
                                                               'canonical plan snapshot unavailable')
                or not isinstance(metadata.get('limits', {}), dict)
                or set(metadata.get('limits', {})) - limit_keys
                or any(type(value) not in (int, float) for value in metadata.get('limits', {}).values())):
            raise PermissionError('AGENT_RESULT_SKILL_PROOF_REQUIRED')
        steps = checkpoint.plan_snapshot.get('steps', [])
        for step in steps:
            if not isinstance(step, dict):
                raise PermissionError('AGENT_RESULT_SKILL_PROOF_REQUIRED')
            if step.get('status') in {'running', 'failed', 'cancelled', 'timeout'}:
                verify_failure_scope(step)
            if step.get('status') == 'completed' or step.get('result') is not None:
                verify_step(step)
            elif step.get('error') is not None:
                # Legacy exception-only steps have no child proof. Only fixed
                # data-free server codes may cross the result read boundary.
                if step['error'] not in safe_errors:
                    raise PermissionError('AGENT_RESULT_SKILL_PROOF_REQUIRED')
                verify_failure_scope(step)
        if (checkpoint.metadata.get('error') is not None
                and checkpoint.metadata['error'] not in safe_errors):
            raise PermissionError('AGENT_RESULT_SKILL_PROOF_REQUIRED')
        if checkpoint.metadata.get('result') is not None:
            matched = [step for step in steps if step.get('index') == checkpoint.step_index]
            if len(matched) != 1:
                raise PermissionError('AGENT_RESULT_SKILL_PROOF_REQUIRED')
            verify_step({**matched[0], 'result': checkpoint.metadata['result'],
                         'error': checkpoint.metadata.get('error')})
    result = task.get('result')
    if result is None and task.get('status') != 'succeeded':
        return True
    steps = result.get('final_step_results') if isinstance(result, dict) else None
    if (not isinstance(steps, list) or set(result) != {'final_step_results', 'completed_steps', 'total_steps'}
            or not 1 <= len(steps) <= 8
            or result.get('completed_steps') != len(steps) or result.get('total_steps') != len(steps)):
        raise PermissionError('AGENT_RESULT_SKILL_PROOF_REQUIRED')
    for index, step in enumerate(steps):
        if not isinstance(step, dict) or step.get('index') != index:
            raise PermissionError('AGENT_RESULT_SKILL_PROOF_REQUIRED')
        verify_step(step)
    return True


def create_agent_task(engine, *, actor, goal, domain_id, scope, steps=None):
    from account.skills import get_skill_info
    from account.authorization import check_dual_domain_permission
    from lumenis.shared.agents.skills.execution import _BACKGROUND_INPUTS, _background_binding
    from lumenis.system.security.permission import _is_server_local_workspace_principal
    local = _is_server_local_workspace_principal(actor)
    if (not isinstance(goal, str) or not goal.strip() or len(goal) > 16000
            or domain_id not in ('cth', 'zbmp')
            or (not local and (not isinstance(actor, dict) or type(actor.get('id')) is not int))
            or not AgentLoop._valid_typed_scope(domain_id, scope)):
        raise ValueError('AGENT_TASK_INPUT_INVALID')
    if steps is not None and (not isinstance(steps, list) or not 1 <= len(steps) <= 8):
        raise ValueError('AGENT_STEPS_INVALID')
    product = 'CTH' if domain_id == 'cth' else 'ZBMP'
    selected = steps or []
    permitted = {}
    # Runtime model planning can only select these already-authorized tools.
    for skill_id in _BACKGROUND_INPUTS:
        info = get_skill_info(skill_id)
        if info and info.get('status') == 'enabled' and (local or check_dual_domain_permission(
                actor['id'], product, module=skill_id, action='read')):
            permitted[skill_id] = _background_binding(info)
    normalized = []
    for entry in selected:
        if not isinstance(entry, dict) or set(entry) - {'skill_id', 'input'}:
            raise ValueError('AGENT_STEP_INPUT_INVALID')
        skill_id, inputs = entry.get('skill_id'), entry.get('input', {})
        if (skill_id not in permitted or not isinstance(inputs, dict)
                or set(inputs) - _BACKGROUND_INPUTS[skill_id]
                or len(json.dumps(inputs, ensure_ascii=False)) > 16000):
            raise PermissionError('AGENT_STEP_NOT_AUTHORIZED')
        normalized.append({'skill_id': skill_id, 'input': inputs})
    contract = {'schema_version': 1, 'module': 'agent_runtime',
                'mode': 'registered' if selected else 'gateway', 'steps': normalized,
                'registry_bindings': permitted}
    if local:
        contract.update(principal_kind='local_workspace', principal_ref='workspace:local', workspace_binding=_workspace_binding())
    context = {'actor_id': None if local else actor['id'], 'domain_id': domain_id,
               'scope': dict(scope), 'agent_runtime': contract}
    # Authorize before creating any durable task, using the same live Owner.
    authorized_context({'created_by': 'agent_runtime', 'context': context}, actor)
    task = engine.create_task(goal, context=context, created_by='agent_runtime')
    engine._db_update_task(task['task_id'], agent_id='agent-runtime-' + task['task_id'])
    return engine.get_task(task['task_id'])


def _current_binding(task_id, skill_id):
    from ai_task_engine import get_task_engine
    from account.skills import get_skill_info
    from account.authorization import check_dual_domain_permission
    from lumenis.shared.agents.skills.execution import _background_binding
    task = get_task_engine().get_task(task_id)
    context = authorized_context(task)
    info = get_skill_info(skill_id)
    expected = context['agent_runtime']['registry_bindings'].get(skill_id)
    if (not info or _background_binding(info) != expected or (context['actor_id'] is not None and not check_dual_domain_permission(
            context['actor_id'], context['product'], module=skill_id, action='read'))):
        raise PermissionError('AGENT_REGISTERED_TOOL_CHANGED')
    return {'configuration': {'binding': expected, 'task_id': task_id}, 'environment': {'local_only': True},
            'origin_scope_id': _digest({'actor': context['actor_id'], 'scope': context['scope'],
                                      'domain': context['domain_id']}),
            'implementation_revision': expected, 'available': True}


def _invoke_local_tool(task_id, skill_id, *, _source_free=False, _execution_control=None, **inputs):
    from ai_task_engine import get_task_engine
    from account.skills import execute_skill_api
    from lumenis.shared.agents.skills.execution import _BACKGROUND_INPUTS, query_executions, verified_execution_scope
    _current_binding(task_id, skill_id)
    task = get_task_engine().get_task(task_id)
    context = authorized_context(task)
    if task['status'] == 'cancelled':
        return {'success': False, 'cancelled': True, 'error': 'USER_CANCELLED'}
    if set(inputs) - _BACKGROUND_INPUTS[skill_id]:
        raise ValueError('AGENT_TOOL_SCHEMA_INVALID')
    execution_id = ('skillscope_' if context['actor_id'] is not None else '') + 'agentstep_' + _digest(
        {'task': task_id, 'skill': skill_id, 'inputs': inputs})[:32]
    old = query_executions(execution_id=execution_id, limit=1, strict=True)
    if old and old[0]['status'] == 'completed':
        if context['actor_id'] is not None:
            admitted = verified_execution_scope(old[0], context['actor'])
            if not admitted or any(admitted[key] != context['scope'].get(key)
                    for key in ('subject_id', 'brand_focus_id', 'global_scope')):
                raise PermissionError('AGENT_SKILL_SCOPE_RECEIPT_INVALID')
        return {'success': True, 'result': json.loads(old[0]['output_json']), 'skill_execution_id': execution_id}
    try:
        outcome = execute_skill_api(skill_id, task=task['user_input'], input_payload=inputs,
            action_type='READ', user_id=context['actor_id'], product=context['product'], _execution_id=execution_id,
            _agent_task_id=task_id, scope=context['scope'] if context['actor_id'] is not None else None,
            _workspace_principal=context['actor'] if context['actor_id'] is None else None, _local_only=_source_free,
            _execution_control=_execution_control)
    except Exception:
        if context['actor_id'] is None:
            raise
        return {'success': False, 'result': None, 'error': 'AGENT_SKILL_RESULT_UNAVAILABLE',
                'skill_execution_id': execution_id}

    _current_binding(task_id, skill_id)
    if context['actor_id'] is not None:
        # Never copy failed/unreceipted handler content (including exception text)
        # into the Agent loop's checkpoint or derived observations.
        rows = query_executions(execution_id=execution_id, limit=1, strict=True)
        readable = (outcome.get('success') is True and rows
                    and verified_execution_scope(rows[0], context['actor'])
                    and json.loads(rows[0]['output_json']) == outcome.get('result'))
        if not readable:
            return {'success': False, 'result': None, 'error': 'AGENT_SKILL_RESULT_UNAVAILABLE',
                    'skill_execution_id': execution_id}
    return {'success': outcome.get('success') is True, 'result': outcome.get('result'),
            'error': outcome.get('error') or outcome.get('code'), 'skill_execution_id': execution_id}


def _account_step_id(task_id, skill_id, inputs):
    return 'skillscope_agentstep_' + _digest({'task': task_id, 'skill': skill_id, 'inputs': inputs})[:32]


def _bound_local_handler(task_id, skill_id, *, account=False, conversation_sha256=None):
    def handler(*, _execution_control=None, **inputs):
        if _execution_control is not None:
            from .loop import StepExecutionControl
            if type(_execution_control) is not StepExecutionControl:
                raise PermissionError('TOOL_EXECUTION_CONTROL_INVALID')
            _execution_control.check()
        _assert_conversation_snapshot(task_id, conversation_sha256)
        try:
            result = _invoke_local_tool(task_id, skill_id, _execution_control=_execution_control, **inputs)
        except Exception:
            if not account:
                raise
            # Cover the entire execution adapter, including serialization and
            # durable readback faults after a handler has already read data.
            identifier = _account_step_id(task_id, skill_id, inputs)
            return {'success': False, 'result': None, 'error': 'AGENT_SKILL_RESULT_UNAVAILABLE',
                    'skill_execution_id': identifier}
        if _execution_control is not None:
            _execution_control.check()
        _assert_conversation_snapshot(task_id, conversation_sha256)
        return result
    return handler


def _bound_identity(task_id, skill_id, conversation_sha256=None):
    def identity():
        _assert_conversation_snapshot(task_id, conversation_sha256)
        result = _current_binding(task_id, skill_id)
        from lumenis.shared.agents.skills.execution import registered_handler_identity
        result['configuration']['handler_identity_sha256'] = registered_handler_identity(skill_id)
        if conversation_sha256 is not None:
            result['configuration']['conversation_context_sha256'] = conversation_sha256
        return result
    return identity


def _tool_router(task, conversation_sha256=None):
    from agent_capability.router import CapabilityRouter, ToolDefinition, ToolPermissionLevel
    from account import skills
    from lumenis.shared.agents.skills import execution
    router = CapabilityRouter(enabled=True)
    # Remove unbound core names; only the admitted existing local handlers enter
    # this request's resolver, with stable implementation and registry identity.
    router._tools.clear()
    for skill_id in task['context']['agent_runtime']['registry_bindings']:
        # Named plain functions are used for formation's implementation hash;
        # task/skill identity is explicit in the runtime identity provider.
        handler = _bound_local_handler(task['task_id'], skill_id,
            account=task['context'].get('actor_id') is not None, conversation_sha256=conversation_sha256)
        identity = _bound_identity(task['task_id'], skill_id, conversation_sha256)
        contract = execution.registered_background_contract(skills.get_skill_info(skill_id))
        router.register_tool(ToolDefinition(skill_id, skill_id, 'Bounded local registered Skill',
            handler=handler, identity_provider=identity, permission_level=ToolPermissionLevel.READ,
            origin='lumenis.shared.agents.skills', resource_uri='skill://' + skill_id,
            dependency_paths=(__file__, skills.__file__, execution.__file__),
            input_schema=contract['input_schema'], output_schema=contract['output_schema'],
            forwards_execution_control=True))
    return router


class _RegisteredPlanner:
    def __init__(self, contract, *, context_validator=None, conversation_sha256=None):
        self.contract = contract
        self.context_validator = context_validator
        self.conversation_sha256 = conversation_sha256
    def plan(self, goal, **kwargs):
        try:
            if self.context_validator is not None:
                self.context_validator()
        except (PermissionError, RuntimeError, ValueError) as exc:
            return Plan(goal=goal, mode='rule_based', model='none', is_fallback=True, fallback_reason=str(exc))
        return Plan(goal=goal, mode='rule_based', model='none', steps=[
            PlanStep(index=index, action='Run local ' + entry['skill_id'], tool=entry['skill_id'],
                     params=entry['input'], expected_output='Persisted local Skill result', risk_level='low')
            for index, entry in enumerate(self.contract['steps'])],
            context_budget={'required_context_sha256': self.conversation_sha256,
                            'measurement': 'NOT_REQUESTED_NO_MODEL', 'model_execution': 'NOT_RUN'})


def _gateway_request(task_id, system, user, context):
    """Typed user-authored task input, never a Canonical external source claim."""
    from ai_task_engine import get_task_engine
    from lumenis.system.ai_gateway.owned_service import OwnedServiceRequest
    task = get_task_engine().get_task(task_id)
    current = authorized_context(task)
    if task.get('status') == 'cancelled':
        raise PermissionError('USER_CANCELLED')
    if current['actor_id'] is None:
        raise PermissionError('LOCAL_AGENT_MODEL_SERVICE_UNAVAILABLE')
    policy = agent_source_use_policy()
    pack = context.get('conversation_context_pack')
    expected = pack.get('sha256') if type(pack) is dict else None
    actual = _assert_conversation_snapshot(task_id, expected)
    if actual != pack or context.get('committed_step_receipts', []) != _committed_step_receipts(task, current):
        raise PermissionError('AGENT_CONVERSATION_CONTEXT_INVALID')
    binding = {'task_context': task['context'], 'conversation_context_sha256': expected,
               'committed_step_receipts': context.get('committed_step_receipts', [])}
    revision = {'original_task_input': task['user_input'], 'planner_payload_sha256': _digest(user),
                'conversation_context_sha256': expected}
    return OwnedServiceRequest(operation='agent_plan', request_id='agent-plan:' + task_id,
        job_id=task_id, actor_ref='actor:' + str(current['actor_id']), domain_id='cth' if current['domain_id'] == 'cth' else 'bmp',
        scope=('GLOBAL / ALL' if current['scope']['global_scope'] else
               current['scope']['subject_id'] or current['scope']['brand_focus_id']),
        source_use_policy_version=policy['schema'],
        source_use_policy_sha256=_digest(policy), source_binding_sha256=_digest(binding),
        source_evidence_refs=('user-task:' + task_id,), input_revision_sha256=_digest(revision),
        system_prompt=system, user_payload=user, response_schema_json=json.dumps({'type': 'object',
            'required': ['steps'], 'properties': {'steps': {'type': 'array', 'maxItems': 8}},
            'additionalProperties': False}), max_output_tokens=2000)


def agent_source_use_policy():
    """Original user input and verified references; never external source bodies."""
    return {'schema': 'agent-planner-current-context-v2', 'training_allowed': False,
            'sources': 'original user task, source-free conversation, admitted local tool metadata and committed receipt references',
            'external_source_bodies': 'NOT_GRANTED', 'external_transmission': 'NOT_GRANTED'}


def validate_agent_source_use(request, *, actor=None):
    """Source validator for an exactly admitted existing OwnedServiceBinding.

    Registration/loading remains the Gateway owner's separate admission. This
    function cannot bind a runtime, authorize a tool or revive a cancelled task.
    """
    from ai_task_engine import get_task_engine
    from lumenis.system.ai_gateway.owned_service import OwnedServiceRequest, SourceUseDecision
    from lumenis.system.security import permission
    from .planner import _PLANNER_SYSTEM_PROMPT
    if type(request) is not OwnedServiceRequest or request.operation != 'agent_plan':
        raise ValueError('AGENT_MODEL_REQUEST_INVALID')
    task = get_task_engine().get_task(request.job_id)
    if not task:
        raise PermissionError('AGENT_TASK_NOT_FOUND')
    current = authorized_context(task, actor)
    if current['actor_id'] is None:
        raise PermissionError('LOCAL_AGENT_MODEL_SERVICE_UNAVAILABLE')
    # Parse only the canonical planner envelope; duplicate/reformatted data is
    # rejected by the exact reconstruction below. Prompts cannot supply sources.
    prefix = '目标：' + task['user_input'] + '\n最大步骤数：'
    if not request.user_payload.startswith(prefix) or not request.user_payload.endswith('\n请输出规划 JSON。'):
        raise PermissionError('AGENT_MODEL_INPUT_BINDING_INVALID')
    count, separator, raw = request.user_payload[len(prefix):].partition('\n上下文：')
    if separator != '\n上下文：' or not count.isascii() or not count.isdecimal() or not 1 <= int(count) <= 15:
        raise ValueError('AGENT_MODEL_INPUT_BINDING_INVALID')
    try:
        payload = json.loads(raw[:-len('\n请输出规划 JSON。')])
    except (ValueError, TypeError) as exc:
        raise ValueError('AGENT_MODEL_INPUT_BINDING_INVALID') from exc
    if type(payload) is not dict:
        raise ValueError('AGENT_MODEL_INPUT_BINDING_INVALID')
    expected = _planner_context(task, current)
    # Derived memory/learning remain readable through their own owners. An
    # arbitrary stored text body does not acquire model SourceUse from a Task.
    omissions = payload.get('context_omissions')
    if omissions is not None:
        if omissions != []:
            raise PermissionError('AGENT_MODEL_SOURCE_USE_REQUIRED')
        expected['context_omissions'] = []
    if payload != expected:
        raise PermissionError('AGENT_MODEL_SOURCE_USE_REQUIRED')
    rebuilt = Planner()._build_user_prompt(task['user_input'], expected, int(count))
    exact = _gateway_request(task['task_id'], _PLANNER_SYSTEM_PROMPT, rebuilt, expected)
    exact = replace(exact, response_schema_json=json.dumps(
        Planner._response_schema(int(count)), ensure_ascii=False, sort_keys=True, allow_nan=False))
    if request != exact:
        raise PermissionError('AGENT_MODEL_INPUT_BINDING_INVALID')
    scoped = permission.check_actor_scope_permission(current['actor'], domain_id=current['domain_id'],
        action='read', module='agent_runtime', **current['scope'])
    if scoped.allowed is not True or scoped.verification_state != 'verified' or not scoped.scope_audit_id:
        raise PermissionError('AGENT_TASK_SCOPE_DENIED')
    decision = permission.get_permission_gate().check(permission.OperationType.AI_CALL,
        resource='agent-source-use:v1:' + request.source_binding_sha256 + ':' + request.input_revision_sha256,
        caller=request.actor_ref, domain_id=request.domain_id)
    if permission.is_testing_bypass_enabled() or decision.allowed is not True or not decision.audit_id:
        raise PermissionError('AGENT_MODEL_PERMISSION_DENIED')
    # Admission/auditing can race cancellation or a human correction. Reopen
    # both owners before returning the source decision to the Gateway.
    fresh_task = get_task_engine().get_task(task['task_id'])
    if _planner_context(fresh_task, authorized_context(fresh_task, current['actor'])) != expected:
        raise PermissionError('AGENT_MODEL_SOURCE_CHANGED')
    fresh = _gateway_request(task['task_id'], _PLANNER_SYSTEM_PROMPT, rebuilt, expected)
    if replace(fresh, response_schema_json=request.response_schema_json) != request:
        raise PermissionError('AGENT_MODEL_SOURCE_CHANGED')
    return SourceUseDecision(True, 'AGENT_SOURCE_USE_VERIFIED', request.actor_ref,
        request.domain_id, request.scope, request.source_use_policy_version,
        request.source_use_policy_sha256, request.source_binding_sha256,
        request.source_evidence_refs, scoped.scope_audit_id, decision.audit_id)


def _planner_context(task, current):
    """Server-authored model context; no implicit source/learning body reads."""
    from account.skills import get_skill_info
    from lumenis.shared.agents.skills.execution import _BACKGROUND_INPUTS, registered_background_contract, registered_handler_identity
    context = dict(current)
    pack = _conversation_snapshot(task, current)
    if pack is not None:
        context['conversation_context_pack'] = pack
    context['committed_step_receipts'] = _committed_step_receipts(task, current)
    context['tool_catalog'] = []
    for sid in current['agent_runtime']['registry_bindings']:
        _current_binding(task['task_id'], sid)
        info = get_skill_info(sid)
        contract = registered_background_contract(info)
        context['tool_catalog'].append({'tool': sid, 'name': info.get('name'),
            'allowed_input_fields': sorted(_BACKGROUND_INPUTS[sid]),
            'input_schema': contract['input_schema'],
            'output_schema': contract['output_schema'],
            'handler_identity_sha256': registered_handler_identity(sid),
            'permission': 'READ', 'effects': 'bounded_local_computation'})
    return context


def run_agent_task(task_id):
    from ai_task_engine import get_task_engine
    from lumenis.system.collector.guard.task_queue import TaskQueue
    from lumenis.system.collector.guard.queue_worker import QueueWorker
    from lumenis.system.security.permission import admit_task_operational_write
    engine = get_task_engine()
    task = engine.get_task(task_id)
    context = authorized_context(task)
    queue = TaskQueue()
    try:
        queue_id = queue.enqueue_once('agent_runtime', {'task_id': task_id, 'actor_id': context['actor_id']}, task_id)
        operational = queue.get(queue_id)
        if task['status'] in {'succeeded', 'failed', 'cancelled'} and operational['status'] == 'running':
            queue.ack(queue_id, run_id=operational['run_id'], worker_id=operational['worker_id'], lease_owner=operational['lease_owner'])
            return task
        queue.reap_stale(90, task_id=queue_id)
        class SelectedQueue:
            def dequeue(self, **kwargs):
                return queue.dequeue(task_id=queue_id, **kwargs)
            def __getattr__(self, name):
                return getattr(queue, name)
        def processor(attempt):
            current = engine.get_task(task_id)
            live_context = authorized_context(current)
            if current['status'] in {'succeeded', 'failed', 'cancelled'}:
                return True
            admission = admit_task_operational_write(task_id=task_id, actor_id=live_context['actor_id'], queue=queue, attempt=attempt)
            durable = DurableExecutionAdapter(task_engine=engine, operational_admission=admission)
            contract = current['context']['agent_runtime']
            context_error = None
            try:
                live_context = _planner_context(current, live_context)
                conversation_pack = live_context.get('conversation_context_pack')
            except (ValueError, PermissionError) as exc:
                conversation_pack = None
                context_error = str(exc)
            conversation_sha256 = conversation_pack['sha256'] if conversation_pack else None
            def validate_context():
                if context_error is not None:
                    raise PermissionError(context_error)
                decision = admission.check('ai_task', fields={'status'})
                if decision.allowed is not True:
                    raise PermissionError(decision.reason)
                if runtime._start_time and runtime._check_budget(0) == 'max_time':
                    raise RuntimeError('AGENT_TASK_DEADLINE_EXCEEDED')
                return _assert_conversation_snapshot(task_id, conversation_sha256)
            planner = (_RegisteredPlanner(contract, context_validator=validate_context,
                                          conversation_sha256=conversation_sha256) if contract['mode'] == 'registered' else
                       Planner(gateway_request_factory=partial(_gateway_request, task_id), context_validator=validate_context,
                           model_result_reader=durable.read_model_response,
                           model_attempt_reserver=durable.reserve_model_request,
                           model_result_recorder=durable.record_model_response))
            runtime = AgentLoop(config=AgentConfig(max_steps=8, max_replans=0, max_retries=0,
                max_time_seconds=60, step_timeout_seconds=15, max_cost=0.01), planner=planner,
                durable_adapter=durable, tool_binding=_tool_router(current, conversation_sha256))
            working = None
            try:
                from agent_memory.working import WorkingMemory
                from agent_memory.episodic import EpisodicMemory
                from agent_memory.task import TaskMemory
                from lumenis.shared.database import main_db_path
                path = main_db_path()
                working = WorkingMemory(db_path=str(path), enabled=True).bind_task(task_id, live_context['actor_id'])
                working.begin_task(task_id, current['user_input'], {'domain_id': live_context['domain_id'], 'scope': live_context['scope']})
                episodic = EpisodicMemory(db_path=str(path), enabled=True).bind_task(task_id, live_context['actor_id'])
                # Memory is derived context only; it cannot grant tools or effects.
                # Memory stays useful in its original owner/UI. Reading a
                # record is not model SourceUse; do not inject arbitrary
                # stored source/Skill bodies under a user-input-only policy.
                episodic.query(limit=5)
            except Exception:
                working = None
            if durable.get_checkpoints(task_id):
                runtime.resume(task_id, context=live_context)
            else:
                runtime.run(current['user_input'], context=live_context,
                            agent_id=current['agent_id'], _existing_task_id=task_id)
            finished = engine.get_task(task_id)
            if working is not None:
                try:
                    validate_context()
                    working.add_step('original_task_terminal', output_data={'status': finished['status'],
                        'result': finished.get('result'), 'error': finished.get('error')},
                        status=finished['status'], persist=True)
                    working.archive_to_episodic(episodic)
                    working.end_task({'status': finished['status']})
                except Exception:
                    # Memory availability never changes the committed task outcome.
                    pass
            return finished['status'] in {'succeeded', 'failed', 'cancelled'}
        QueueWorker(SelectedQueue(), processor).process_once()
    finally:
        queue.close()
    return engine.get_task(task_id)


def start_agent_task(task_id):
    def work():
        try:
            run_agent_task(task_id)
        except Exception:
            import logging
            logging.getLogger(__name__).exception('Agent task interrupted; original task remains recoverable')
    from flask import has_request_context, copy_current_request_context
    target = copy_current_request_context(work) if has_request_context() else work
    thread = threading.Thread(target=target, name='agent-task-worker', daemon=True)
    thread.start()
    return thread
