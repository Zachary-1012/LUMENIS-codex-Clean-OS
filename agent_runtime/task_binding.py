"""Production binding for the existing TaskEngine, AgentLoop and leased queue.

No second task store, scheduler, conversation, permission owner or provider.
Only explicitly registered, bounded local read/draft tools are admitted here.
"""
from __future__ import annotations

import hashlib
import json
import re
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


def _task_human_correction_context(task, current):
    """Reopen the same-task human corrections through the existing Memory owner."""
    from agent_memory.base import read_task_user_correction_context
    from lumenis.shared.database import main_db_path
    try:
        return read_task_user_correction_context(str(main_db_path()), task['task_id'],
            current['actor_id'])
    except Exception as exc:
        code = str(exc)
        if not re.fullmatch(r'MEMORY_[A-Z0-9_]{1,96}', code):
            code = 'MEMORY_CONTEXT_UNAVAILABLE'
        unavailable = {'schema': 'task-user-corrections/v1', 'state': 'UNAVAILABLE',
            'record_count': 0, 'records': [], 'source_policy': 'same_task_explicit_user_corrections_only',
            'unavailable_code': code}
        unavailable['snapshot_sha256'] = _digest(unavailable)
        return unavailable


def _assert_task_human_correction_snapshot(task_id, expected_sha256):
    from agent_capability.formation import FormationError
    from ai_task_engine import get_task_engine
    task = get_task_engine().get_task(task_id)
    if task is None:
        raise PermissionError('AGENT_TASK_NOT_FOUND')
    if task.get('status') == 'cancelled':
        raise FormationError('USER_CANCELLED', changed_fields=('task_status',))
    current = authorized_context(task)
    snapshot = _task_human_correction_context(task, current)
    if snapshot['snapshot_sha256'] != expected_sha256:
        raise FormationError('AGENT_TASK_MEMORY_CHANGED', changed_fields=('human_correction_memory',))
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
    shared = context['domain_id'] == 'shared'
    actor_id = context.get('actor_id')
    if contract.get('principal_kind') == 'local_workspace':
        principal = resolve_local_workspace_principal(module='content' if shared else 'skills', action='read')
        if (actor_id is not None or principal is None
                or (actor is not None and not _is_server_local_workspace_principal(actor))
                or contract.get('principal_ref') != 'workspace:local'
                or contract.get('workspace_binding') != _workspace_binding()):
            raise PermissionError('AGENT_WORKSPACE_IDENTITY_DENIED')
        actor = principal
        decision = None if shared else check_local_workspace_scope_permission(principal, domain_id=context['domain_id'],
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
        decision = None if shared else check_actor_scope_permission(actor, domain_id=context['domain_id'], action='read',
            module='agent_runtime', connection=connection, **scope)
    if shared:
        from lumenis.system.security.permission import authorize_shared_workspace
        authorize_shared_workspace(actor, scope, module='content', action='read', connection=connection)
    elif not decision.allowed:
        raise PermissionError('AGENT_TASK_SCOPE_DENIED')
    domain = context['domain_id']
    return {**context, 'actor': actor, 'module': 'agent_runtime', 'domain': domain,
            'product': 'SHARED' if shared else 'CTH' if domain == 'cth' else 'ZBMP',
            'role': None if shared else 'cth_analyst' if domain == 'cth' else 'zbmp_analyst'}


def authorize_task_result_read(task, actor=None):
    """Revalidate saved child Skill proofs before exposing account Agent data."""
    context = authorized_context(task, actor)
    _conversation_snapshot(task, context)
    shared = context['domain_id'] == 'shared'
    if context['actor_id'] is None and not shared:
        return True  # Existing sealed local-workspace boundary stays unchanged.
    from ai_task_engine import get_task_engine
    from lumenis.shared.agents.skills.execution import query_executions, verified_execution_scope, read_source_free_execution
    from .durable_adapter import _sanitize_checkpoint_value
    admitted = {}
    safe_errors = {'AGENT_SKILL_RESULT_UNAVAILABLE', 'TOOL_STEP_TIMEOUT', 'USER_CANCELLED',
                   'AGENT_REGISTERED_TOOL_CHANGED', 'AGENT_TOOL_SCHEMA_INVALID',
                   'AGENT_CONVERSATION_CONTEXT_CHANGED', 'AGENT_CONVERSATION_CONTEXT_ACCESS_DENIED'}

    def verify_failure_scope(step, identifier=None):
        from lumenis.system.security.permission import check_actor_scope_permission
        expected = ('skillscope_' if context['actor_id'] is not None else '') + 'agentstep_' + _digest({'task': task['task_id'],
            'skill': step.get('tool'), 'inputs': step.get('params', {})})[:32]
        if shared:
            _current_binding(task['task_id'], step.get('tool'))
            if identifier is not None and identifier != expected:
                raise PermissionError('AGENT_RESULT_SKILL_SCOPE_DENIED')
            return
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
            scope = ({'domain_id': 'shared', **context['scope']} if row and shared
                and read_source_free_execution(row, context['actor']) else
                verified_execution_scope(row, context['actor']) if row and not shared else None)
            if not scope:
                raise PermissionError('AGENT_RESULT_SKILL_SCOPE_DENIED')
            admitted[identifier] = (row, scope)
        row, scope = admitted[identifier]
        expected = ('skillscope_' if context['actor_id'] is not None else '') + 'agentstep_' + _digest({'task': task['task_id'],
            'skill': step.get('tool'), 'inputs': json.loads(row['input_json'])})[:32]
        if (identifier != expected or row['skill_id'] != step.get('tool')
                or scope['domain_id'] != context['domain_id']
                or any(scope[key] != context['scope'][key] for key in context['scope'])
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


_WORKSPACE_CREDENTIAL_ASSIGNMENT = re.compile(
    r"(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret|cookie|authorization)"
    r"(\s*[:=]\s*)([^\s,;]+)"
)
_WORKSPACE_WINDOWS_PATH = re.compile(
    r"(?<![A-Za-z0-9])(?:[A-Za-z]:\\|\\\\[^\\/\s]+\\[^\\/\s]+\\)[^\s\"'<>]+"
)
_WORKSPACE_POSIX_PATH = re.compile(
    r"(?<![A-Za-z0-9:])/(?:home|Users|tmp|var|opt|mnt|media|private|Volumes|root|workspace|work|repo|app|srv|data|etc)/[^\s\"'<>]+"
)
_WORKSPACE_STEP_STATUSES = frozenset({'pending', 'running', 'completed', 'failed', 'skipped'})
_WORKSPACE_TERMINAL_STATUSES = frozenset({'succeeded', 'completed', 'failed', 'cancelled', 'unknown', 'dlq'})


def _workspace_text(value, *, limit=12000):
    """Return display text with recognizable credentials and local paths removed."""
    if not isinstance(value, str):
        return None
    from .durable_adapter import _sanitize_checkpoint_value
    cleaned, _ = _sanitize_checkpoint_value(value[:limit])
    if not isinstance(cleaned, str):
        return None
    cleaned = _WORKSPACE_CREDENTIAL_ASSIGNMENT.sub(r'\1\2[REDACTED]', cleaned)
    cleaned = re.sub(r'(?i)file://[^\s\"\'<>]+', '[path hidden]', cleaned)
    cleaned = _WORKSPACE_WINDOWS_PATH.sub('[path hidden]', cleaned)
    cleaned = _WORKSPACE_POSIX_PATH.sub('[path hidden]', cleaned)
    cleaned = ''.join(char for char in cleaned if char in '\n\r\t' or ord(char) >= 32)
    cleaned = cleaned.strip()
    return cleaned[:limit] if cleaned else None


def _agent_result_text(task):
    """Project only known user-facing fields from verified registered Skill results."""
    if task.get('status') != 'succeeded' or not isinstance(task.get('result'), dict):
        return None
    rows = []
    for step in task['result'].get('final_step_results', []):
        if not isinstance(step, dict) or step.get('status') != 'completed':
            continue
        skill_id = step.get('tool')
        dispatched = step.get('result')
        output = (dispatched if isinstance(dispatched, dict) and 'skill_execution_id' in dispatched
                  else dispatched.get('result') if isinstance(dispatched, dict) else None)
        if not isinstance(output, dict) or output.get('success') is not True:
            continue
        value = output.get('result')
        # Agent steps may wrap the exact registered Skill response in the
        # TaskEngine dispatch result. Unwrap only the documented result field.
        for _ in range(3):
            if not isinstance(value, dict) or value.get('artifact_type'):
                break
            nested = value.get('result')
            if not isinstance(nested, dict):
                break
            value = nested
        if (skill_id == 'shared.social_card' and isinstance(value, dict)
                and value.get('artifact_type') == 'svg_draft' and isinstance(value.get('svg'), str)):
            # The existing local card producer emits its exact SVG draft. Parse only
            # its visible text nodes; never return markup to the generic task shell.
            try:
                import xml.etree.ElementTree as ET
                root = ET.fromstring(value['svg'])
                text = [node.text for node in root.iter()
                        if node.tag.rsplit('}', 1)[-1] == 'text' and isinstance(node.text, str)]
                rows.extend(item for item in (_workspace_text(item) for item in text) if item)
            except (ET.ParseError, ValueError, TypeError):
                pass
        elif skill_id == 'shared.video_shotcraft' and isinstance(value, dict):
            shots = value.get('shot_plan')
            if isinstance(shots, list):
                for index, shot in enumerate(shots[:8], 1):
                    if isinstance(shot, dict):
                        brief = _workspace_text(shot.get('brief'), limit=2000)
                        if brief:
                            rows.append(f'{index}. {brief}')
        # Other registered skills currently return registry/status data or a
        # workflow descriptor, not a customer-ready deliverable. Do not expose
        # those internal objects by recursively guessing text-bearing fields.
    content = '\n'.join(dict.fromkeys(rows))
    return _workspace_text(content, limit=20000) if content else None


def _agent_saved_work_refs(task, *, current):
    """Find the exact SavedWork item copied from a completed local card.

    The reference is reconstructed from the verified step receipt and looked
    up by SavedWork's deterministic work id. The SavedWork owner reopens and
    revalidates the current version before its id/title is exposed.
    """
    if task.get('status') != 'succeeded' or current.get('domain_id') != 'shared':
        return []
    from lumenis.shared.reporting import saved_work
    from lumenis.shared.agents.skills.execution import query_executions, read_source_free_execution
    result = task.get('result') if isinstance(task.get('result'), dict) else {}
    refs = []
    try:
        context = saved_work.authorize_saved_work(current['actor'], current['scope'], action='read')
    except Exception:
        return []
    for step in result.get('final_step_results', []):
        if (not isinstance(step, dict) or step.get('tool') != 'shared.social_card'
                or step.get('status') != 'completed'):
            continue
        dispatched = step.get('result')
        output = (dispatched if isinstance(dispatched, dict) and 'skill_execution_id' in dispatched
                  else dispatched.get('result') if isinstance(dispatched, dict) else None)
        if not isinstance(output, dict) or output.get('success') is not True:
            continue
        value = output.get('result')
        for _ in range(3):
            if not isinstance(value, dict) or value.get('artifact_type'):
                break
            nested = value.get('result')
            if not isinstance(nested, dict):
                break
            value = nested
        execution_id = output.get('skill_execution_id')
        if (not isinstance(execution_id, str) or not isinstance(value, dict)
                or value.get('artifact_type') != 'svg_draft'):
            continue
        executions = query_executions(execution_id=execution_id, limit=1, strict=True)
        source_result = (read_source_free_execution(executions[0], current['actor']) if executions else None)
        if source_result is None or source_result.get('skill_id') != 'shared.social_card':
            continue
        original_output = json.loads(source_result['output_json'])
        source_payload = original_output
        for _ in range(3):
            if not isinstance(source_payload, dict) or source_payload.get('artifact_type'):
                break
            nested = source_payload.get('result')
            if not isinstance(nested, dict):
                break
            source_payload = nested
        if source_payload != value:
            continue
        reference = {'task_id': task['task_id'], 'step_id': step.get('step_id'),
            'execution_id': execution_id, 'skill_id': 'shared.social_card',
            'output_sha256': _digest(original_output),
            'relation': 'user_selected_copy_of_local_draft',
            'model_execution': 'NOT_RUN', 'external_source_use': 'NOT_GRANTED'}
        request_id = 'agent-copy-' + _digest(reference)[:40]
        work_id = 'WORK-' + saved_work._digest({'context': context, 'request_id': request_id})[:24]
        try:
            with saved_work.get_repository().connection(read_only=True, wal=False) as con:
                rows = con.execute(
                    f"SELECT artifact_id FROM {saved_work._TABLE} WHERE kind=? AND source_execution_id=?",
                    (saved_work._KIND, work_id)).fetchall()
                versions = saved_work._versions(con, work_id, context, current['actor'])
                if not versions:
                    continue
                latest_id = versions[-1]['artifact']['artifact_id']
                if not any(row['artifact_id'] == latest_id for row in rows):
                    continue
                reopened = saved_work.reopen_work(
                    latest_id, actor=current['actor'], scope=current['scope'], connection=con)
                current_versions = saved_work._versions(con, work_id, context, current['actor'])
                if (not current_versions or current_versions[-1]['artifact']['artifact_id'] != latest_id
                        or reopened['document'].get('payload', {}).get('task_reference') != reference):
                    continue
                document = reopened.get('document')
                document_kind = document.get('kind') if isinstance(document, dict) else None
                if document_kind not in {'report', 'manuscript', 'media', 'video', 'podcast'}:
                    continue
                refs.append({'kind': document_kind, 'artifact_id': latest_id,
                    'title': _workspace_text(document.get('title'), limit=300) or '已保存作品'})
        except Exception:
            # Stale, revoked or malformed linked work is not exposed as a usable
            # workspace reference; its existing owner retains the diagnostic.
            continue
    return refs[:8]


def _agent_resume_available(task, *, engine=None):
    """Only advertise resume when the persisted Agent checkpoint is structurally resumable."""
    if (not isinstance(task, dict) or task.get('created_by') != 'agent_runtime'
            or task.get('status') not in {'pending', 'ready', 'running', 'failed'}):
        return False
    request_binding = (task.get('context') or {}).get('agent_task_request')
    if (task.get('status') == 'pending' and isinstance(request_binding, dict)
            and isinstance(request_binding.get('request_id'), str)
            and re.fullmatch(r'[0-9a-f]{32}', request_binding['request_id'])):
        # A server may persist the accepted request and stop before its first
        # queue dispatch. Offer the existing explicit run/resume action; never
        # dispatch again merely because a matching request was replayed.
        return True
    try:
        from ai_task_engine import get_task_engine
        from .durable_adapter import DurableExecutionAdapter
        from .loop import AgentLoop
        engine = engine or get_task_engine()
        checkpoints = DurableExecutionAdapter._db_checkpoints(engine.get_steps(task['task_id']))
        if not checkpoints:
            return False
        checkpoint = checkpoints[-1]
        metadata = checkpoint.metadata
        if (metadata.get('resumable') is not True
                or checkpoint.task_id != task.get('task_id')
                or checkpoint.agent_id != task.get('agent_id')
                or checkpoint.state not in {'executing', 'completed', 'failed'}
                or checkpoint.context != task.get('context')):
            return False
        plan = AgentLoop._restore_checkpoint_plan(checkpoint.plan_snapshot)
        if (plan.goal != task.get('user_input') or not plan.steps
                or len(plan.steps) > 8 or not isinstance(task.get('context'), dict)):
            return False
        index = checkpoint.step_index
        if type(index) is not int or index < 0 or index > len(plan.steps):
            return False
        next_index = next((i for i, step in enumerate(plan.steps)
                           if step.status not in {'completed', 'skipped'}), len(plan.steps))
        if next_index < len(plan.steps):
            step = plan.steps[next_index]
            if step.status in {'running', 'failed'}:
                action = AgentLoop._security_action(step)
                if action.value in {'WRITE', 'EXPORT', 'COMMIT', 'PUSH', 'DEPLOY'}:
                    return False
        return True
    except Exception:
        # A malformed, unreadable, revoked, or uncertain checkpoint is not resumable UI state.
        return False


def _agent_workspace_steps(task, *, engine=None):
    """Use durable plan state for progress while exposing only registered tool labels."""
    try:
        from ai_task_engine import get_task_engine
        from .durable_adapter import DurableExecutionAdapter
        engine = engine or get_task_engine()
        checkpoints = DurableExecutionAdapter._db_checkpoints(engine.get_steps(task['task_id']))
        if not checkpoints:
            return []
        snapshot = checkpoints[-1].plan_snapshot
        raw_steps = snapshot.get('steps') if isinstance(snapshot, dict) else None
        contract = (task.get('context') or {}).get('agent_runtime') or {}
        bindings = contract.get('registry_bindings') or {}
        from account.skills import get_skill_info
        result = []
        for item in raw_steps if isinstance(raw_steps, list) else []:
            if not isinstance(item, dict):
                continue
            tool = item.get('tool')
            info = get_skill_info(tool) if isinstance(tool, str) and tool in bindings else None
            label = _workspace_text(info.get('name'), limit=120) if isinstance(info, dict) else None
            status = item.get('status') if item.get('status') in _WORKSPACE_STEP_STATUSES else 'pending'
            result.append({'label': label or '处理用户请求', 'status': status})
            if len(result) >= 8:
                break
        return result
    except Exception:
        return []


def agent_task_workspace_view(task, *, actor=None, engine=None, include_result=True):
    """Current actor-authorized projection for ordinary Agent task clients."""
    current = authorized_context(task, actor)
    user_input = _workspace_text(task.get('user_input'), limit=16000) or ''
    title = next((line.strip() for line in user_input.splitlines() if line.strip()), '')[:120]
    status = task.get('status') if isinstance(task.get('status'), str) else 'unknown'
    request_binding = (task.get('context') or {}).get('agent_task_request')
    request_id = request_binding.get('request_id') if isinstance(request_binding, dict) else None
    if not isinstance(request_id, str) or re.fullmatch(r'[0-9a-f]{32}', request_id) is None:
        request_id = None
    if include_result is not True:
        # Task ownership and live scope remain readable after a child result is
        # revoked. This projection intentionally avoids checkpoints, child
        # executions, saved work and all result-derived text.
        return {
            'title': _workspace_text(title, limit=120) or '任务',
            'input': user_input,
            'status': status,
            'created_at': task.get('created_at'),
            'updated_at': task.get('updated_at'),
            'can_cancel': status in {'pending', 'ready', 'running'},
            'can_resume': False,
            'output_text': None,
            'work_refs': [],
            'steps': [],
            'error_code': None,
            'result_access_state': 'RESTRICTED',
            'request_id': request_id,
        }
    authorize_task_result_read(task, current['actor'])
    raw_error = task.get('error')
    match = re.match(r'^([A-Z][A-Z0-9_]{1,95})(?::|$)', raw_error) if isinstance(raw_error, str) else None
    error_code = match.group(1) if match else ('TASK_FAILED' if task.get('status') == 'failed' else None)
    output_text = _agent_result_text(task)
    work_refs = _agent_saved_work_refs(task, current=current)
    if status == 'succeeded' and isinstance(task.get('result'), dict):
        completed_tools = [step.get('tool') for step in task['result'].get('final_step_results', [])
                           if isinstance(step, dict) and step.get('status') == 'completed']
        unsupported = any(tool not in {'shared.social_card', 'shared.video_shotcraft'}
                          for tool in completed_tools)
        if unsupported:
            error_code = 'RESULT_PREVIEW_PARTIAL' if output_text or work_refs else 'RESULT_PREVIEW_UNSUPPORTED'
        elif completed_tools and not output_text and not work_refs:
            error_code = 'RESULT_PREVIEW_UNAVAILABLE'
    return {
        'title': _workspace_text(title, limit=120) or '任务',
        'input': user_input,
        'status': status,
        'created_at': task.get('created_at'),
        'updated_at': task.get('updated_at'),
        'can_cancel': status in {'pending', 'ready', 'running'},
        'can_resume': _agent_resume_available(task, engine=engine),
        'output_text': output_text,
        'work_refs': work_refs,
        'steps': _agent_workspace_steps(task, engine=engine),
        'error_code': error_code,
        'request_id': request_id,
    }


def agent_task_evidence_view(task, *, actor=None, engine=None):
    """Expose evidence descriptors only; raw evidence content remains with its owner."""
    current = authorized_context(task, actor)
    authorize_task_result_read(task, current['actor'])
    if engine is None:
        from ai_task_engine import get_task_engine
        engine = get_task_engine()
    evidence = []
    for row in engine.get_evidence(task['task_id']):
        evidence.append({
            'kind': _workspace_text(row.get('evidence_type'), limit=120) or '执行证据',
            'source': _workspace_text(row.get('source'), limit=256),
            'created_at': row.get('created_at'),
            'authenticity_score': row.get('authenticity_score'),
        })
    return evidence


def _agent_task_request_identity(actor, domain_id, scope, request_id):
    from lumenis.system.security.permission import _is_server_local_workspace_principal
    if not isinstance(request_id, str) or re.fullmatch(r'[0-9a-f]{32}', request_id) is None:
        raise ValueError('AGENT_TASK_REQUEST_ID_INVALID')
    if _is_server_local_workspace_principal(actor):
        actor_ref = 'workspace:local'
        actor_sha256 = _digest({'actor_ref': actor_ref, 'workspace_binding': _workspace_binding()})
    elif isinstance(actor, dict) and type(actor.get('id')) is int:
        actor_ref = 'actor:' + str(actor['id'])
        actor_sha256 = _digest({'actor_ref': actor_ref})
    else:
        raise PermissionError('VERIFIED_ACTOR_REQUIRED')
    scope_sha256 = _digest({'domain_id': domain_id, 'scope': scope})
    idempotency_sha256 = _digest({
        'actor_sha256': actor_sha256,
        'scope_sha256': scope_sha256,
        'request_id': request_id,
    })
    return {
        'request_id': request_id,
        'actor_ref': actor_ref,
        'actor_sha256': actor_sha256,
        'scope_sha256': scope_sha256,
        'idempotency_sha256': idempotency_sha256,
    }


def _agent_task_request_binding(actor, domain_id, scope, request_id, goal, steps):
    identity = _agent_task_request_identity(actor, domain_id, scope, request_id)
    try:
        payload_sha256 = _digest({'input': goal, 'steps': steps})
    except (TypeError, ValueError):
        raise ValueError('AGENT_STEPS_INVALID') from None
    return {**identity, 'payload_sha256': payload_sha256}


def _request_identity_matches(task, identity):
    if not isinstance(task, dict) or task.get('created_by') != 'agent_runtime':
        return False
    context = task.get('context') if isinstance(task.get('context'), dict) else {}
    saved = context.get('agent_task_request')
    return (isinstance(saved, dict)
            and all(saved.get(key) == identity.get(key)
                    for key in ('request_id', 'actor_ref', 'actor_sha256', 'scope_sha256',
                                'idempotency_sha256')))


def find_agent_task_for_request(engine, *, actor, request_id, domain_id, scope):
    """Read-only exact lookup under the current server actor and typed scope."""
    identity = _agent_task_request_identity(actor, domain_id, scope, request_id)
    task_id = 'task_' + identity['idempotency_sha256'][:32]
    task = engine.get_task(task_id)
    if task is None or not _request_identity_matches(task, identity):
        return None
    authorized_context(task, actor)
    return task


def _existing_agent_task_for_request(engine, *, actor, request_binding, goal):
    task_id = 'task_' + request_binding['idempotency_sha256'][:32]
    task = engine.get_task(task_id)
    if task is None:
        return None
    if not _request_identity_matches(task, request_binding):
        raise ValueError('AGENT_TASK_REQUEST_ID_CONFLICT')
    # A retry remains bound to the current actor and scope, but does not
    # revalidate or reexecute a child Skill whose output permission changed.
    authorized_context(task, actor)
    saved = task['context']['agent_task_request']
    if (task.get('user_input') != goal
            or saved.get('payload_sha256') != request_binding.get('payload_sha256')):
        raise ValueError('AGENT_TASK_REQUEST_ID_CONFLICT')
    return task


def create_agent_task(engine, *, actor, goal, domain_id, scope, steps=None,
                      request_id=None, return_created=False):
    from account.skills import get_skill_info
    from account.authorization import check_dual_domain_permission
    from lumenis.shared.agents.skills.execution import _BACKGROUND_INPUTS, _background_binding
    from lumenis.system.security.permission import _is_server_local_workspace_principal
    local = _is_server_local_workspace_principal(actor)
    if (not isinstance(goal, str) or not goal.strip() or len(goal) > 16000
            or domain_id not in ('cth', 'zbmp', 'shared')
            or (not local and (not isinstance(actor, dict) or type(actor.get('id')) is not int))
            or not AgentLoop._valid_typed_scope(domain_id, scope)):
        raise ValueError('AGENT_TASK_INPUT_INVALID')
    request_binding = None
    if request_id is not None:
        request_binding = _agent_task_request_binding(actor, domain_id, scope, request_id, goal, steps)
        existing = _existing_agent_task_for_request(
            engine, actor=actor, request_binding=request_binding, goal=goal)
        if existing is not None:
            return (existing, False) if return_created else existing
    if steps is not None and (not isinstance(steps, list) or not 1 <= len(steps) <= 8):
        raise ValueError('AGENT_STEPS_INVALID')
    shared = domain_id == 'shared'
    product = 'SHARED' if shared else 'CTH' if domain_id == 'cth' else 'ZBMP'
    selected = steps or []
    permitted = {}
    # Runtime model planning can only select these already-authorized tools.
    for skill_id in _BACKGROUND_INPUTS:
        info = get_skill_info(skill_id)
        if info and info.get('status') == 'enabled' and (
                shared and _shared_registered_skill(info) or not shared and (local or check_dual_domain_permission(
                actor['id'], product, module=skill_id, action='read'))):
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
    if request_binding is not None:
        context['agent_task_request'] = request_binding
    # Authorize before creating any durable task, using the same live Owner.
    authorized_context({'created_by': 'agent_runtime', 'context': context}, actor)
    if request_binding is None:
        task = engine.create_task(goal, context=context, created_by='agent_runtime')
        created = True
    else:
        task, created = engine.create_task(
            goal, context=context, created_by='agent_runtime',
            request_idempotency_key=request_binding['idempotency_sha256'],
            request_payload_sha256=request_binding['payload_sha256'],
            return_created=True)
        if not created:
            authorized_context(task, actor)
    if created:
        engine._db_update_task(task['task_id'], agent_id='agent-runtime-' + task['task_id'])
        task = engine.get_task(task['task_id'])
    return (task, created) if return_created else task


def _current_binding(task_id, skill_id):
    from ai_task_engine import get_task_engine
    from account.skills import get_skill_info
    from account.authorization import check_dual_domain_permission
    from lumenis.shared.agents.skills.execution import _background_binding
    task = get_task_engine().get_task(task_id)
    context = authorized_context(task)
    info = get_skill_info(skill_id)
    expected = context['agent_runtime']['registry_bindings'].get(skill_id)
    shared = context['domain_id'] == 'shared'
    if (not info or _background_binding(info) != expected or (shared and not _shared_registered_skill(info))
            or (not shared and context['actor_id'] is not None and not check_dual_domain_permission(
            context['actor_id'], context['product'], module=skill_id, action='read'))):
        raise PermissionError('AGENT_REGISTERED_TOOL_CHANGED')
    return {'configuration': {'binding': expected, 'task_id': task_id}, 'environment': {'local_only': True},
            'origin_scope_id': _digest({'actor': context['actor_id'], 'scope': context['scope'],
                                      'domain': context['domain_id']}),
            'implementation_revision': expected, 'available': True}


def _shared_registered_skill(info):
    """The existing source-free local Shared subset, never an arbitrary plugin."""
    from lumenis.shared.agents.skills.execution import _BACKGROUND_INPUTS
    return (info.get('skill_id') in _BACKGROUND_INPUTS and info['skill_id'].startswith('shared.')
        and str(info.get('product') or '').upper() == 'SHARED'
        and str(info.get('runtime') or 'builtin').lower() == 'builtin'
        and str(info.get('source') or 'builtin').lower() == 'builtin')


def prepare_shared_agent_deliverable(task_id, *, actor, step_index=0):
    """Copy a verified local card into the existing editable SavedWork format.

    Preparation is not a save or an export approval. The original Task and
    producer receipt remain separate; the new work is an explicitly selected
    user-authored copy and never external Evidence or Canonical data.
    """
    from ai_task_engine import get_task_engine
    from lumenis.shared.agents.skills.execution import query_executions, read_source_free_execution
    from lumenis.shared.reporting import saved_work
    from lumenis.shared.content_creation.audio_visuals import validate_visual_document, visual_document_markdown
    task = get_task_engine().get_task(task_id)
    current = authorized_context(task, actor)
    authorize_task_result_read(task, current['actor'])
    if (current['domain_id'] != 'shared' or task['status'] != 'succeeded'
            or type(step_index) is not int or not 0 <= step_index < len(task['result']['final_step_results'])):
        raise ValueError('AGENT_DELIVERABLE_NOT_AVAILABLE')
    step = task['result']['final_step_results'][step_index]
    if step.get('tool') != 'shared.social_card' or step.get('status') != 'completed':
        raise ValueError('AGENT_DELIVERABLE_EDITOR_NOT_BOUND')
    dispatched = step['result']
    output = dispatched if 'skill_execution_id' in dispatched else dispatched['result']
    rows = query_executions(execution_id=output['skill_execution_id'], limit=1, strict=True)
    row = read_source_free_execution(rows[0], current['actor']) if rows else None
    if row is None:
        raise PermissionError('AGENT_DELIVERABLE_PRODUCER_UNAVAILABLE')
    result = json.loads(row['output_json'])
    for _ in range(3):
        if result.get('artifact_type') == 'svg_draft':
            break
        result = result.get('result') if type(result.get('result')) is dict else {}
    if result.get('artifact_type') != 'svg_draft' or type(result.get('dimensions')) is not dict:
        raise ValueError('AGENT_DELIVERABLE_OUTPUT_INVALID')
    inputs = json.loads(row['input_json'])
    width, height = result['dimensions']['width'], result['dimensions']['height']
    title = inputs.get('title') or task['user_input']
    subtitle = inputs.get('subtitle') or ''
    accent = inputs.get('accent') or '#9fe7f5'
    import re
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', accent):
        accent = '#9fe7f5'
    common = {'rotation': 0, 'opacity': 1, 'visible': True, 'locked': False}
    def text_layer(identity, text, y, size, color):
        return {**common, 'id': identity, 'kind': 'text', 'name': identity,
            'x': 72, 'y': y, 'width': max(1, width - 144), 'height': max(1, size * 2.4),
            'text': text, 'font_size': size, 'color': color, 'align': 'left', 'line_height': 1.2}
    visual = validate_visual_document({'schema': 'lumenis.visual-document/v1',
        'canvas': {'width': width, 'height': height, 'background': '#151719'}, 'assets': [],
        'layers': [
            {**common, 'id': 'separator', 'name': 'Separator', 'kind': 'rectangle',
             'x': 72, 'y': height - 132, 'width': max(1, width - 144), 'height': 2,
             'fill': '#596167', 'stroke': '#596167', 'stroke_width': 0},
            {**common, 'id': 'accent', 'name': 'Accent', 'kind': 'ellipse',
             'x': width - 132, 'y': 76, 'width': 56, 'height': 56,
             'fill': '#00000000', 'stroke': accent, 'stroke_width': 4},
            text_layer('title', title, height * .46 - max(34, int(width * .07)), max(34, int(width * .07)), '#f5f7f8'),
            text_layer('subtitle', subtitle, height * .54 - max(20, int(width * .032)), max(20, int(width * .032)), '#b8c0c5'),
            text_layer('stamp', 'LUMENIS · DRAFT', height - 90, 18, accent),
        ]})
    reference = {'task_id': task_id, 'step_id': step['step_id'], 'execution_id': row['execution_id'],
        'skill_id': row['skill_id'], 'output_sha256': _digest(json.loads(row['output_json'])),
        'relation': 'user_selected_copy_of_local_draft', 'model_execution': 'NOT_RUN',
        'external_source_use': 'NOT_GRANTED'}
    draft = {'title': title if len(title) <= 300 else 'Editable visual draft',
        'markdown': visual_document_markdown(visual), 'kind': 'report',
        'payload': {'visual_document': visual, 'task_reference': reference}, 'citations': [],
        'request_id': 'agent-copy-' + _digest(reference)[:40], 'task_id': task_id}
    resource = saved_work.work_write_resource(**draft, work_id=None, previous_artifact_id=None,
        actor=current['actor'], scope=current['scope'])
    return {'state': 'READY_TO_SAVE', 'saved': False, 'draft': draft, 'resource': resource,
            'source': reference, 'scope': dict(current['scope']), 'editor': 'existing_visual_document'}


def save_shared_agent_deliverable(task_id, *, actor, step_index=0):
    """Commit through SavedWork's exact Permission, Artifact and readback gates."""
    from lumenis.shared.reporting.saved_work import save_work
    prepared = prepare_shared_agent_deliverable(task_id, actor=actor, step_index=step_index)
    from lumenis.system.security import permission
    approval = permission.get_permission_gate().get_valid_approval_token(
        permission.OperationType.DATA_EXPORT.value, prepared['resource'], exact=True)
    if approval is None:
        raise PermissionError('AGENT_DELIVERABLE_APPROVAL_REQUIRED')
    def verify_source(_connection, _artifact, _document):
        fresh = prepare_shared_agent_deliverable(task_id, actor=actor, step_index=step_index)
        if fresh != prepared:
            raise PermissionError('AGENT_DELIVERABLE_SOURCE_CHANGED')
        if permission.get_permission_gate().get_valid_approval_token(
                permission.OperationType.DATA_EXPORT.value, prepared['resource'], exact=True) != approval:
            raise PermissionError('AGENT_DELIVERABLE_APPROVAL_CHANGED')
    return save_work(**prepared['draft'], actor=actor, scope=prepared['scope'], before_commit=verify_source)


def _invoke_local_tool(task_id, skill_id, *, _source_free=False, _execution_control=None, **inputs):
    from ai_task_engine import get_task_engine
    from account.skills import execute_skill_api
    from lumenis.shared.agents.skills.execution import _BACKGROUND_INPUTS, query_executions, verified_execution_scope
    _current_binding(task_id, skill_id)
    task = get_task_engine().get_task(task_id)
    context = authorized_context(task)
    shared = context['domain_id'] == 'shared'
    if task['status'] == 'cancelled':
        return {'success': False, 'cancelled': True, 'error': 'USER_CANCELLED'}
    if set(inputs) - _BACKGROUND_INPUTS[skill_id]:
        raise ValueError('AGENT_TOOL_SCHEMA_INVALID')
    execution_id = ('skillscope_' if context['actor_id'] is not None else '') + 'agentstep_' + _digest(
        {'task': task_id, 'skill': skill_id, 'inputs': inputs})[:32]
    old = query_executions(execution_id=execution_id, limit=1, strict=True)
    if old and old[0]['status'] == 'completed':
        if shared:
            from lumenis.shared.agents.skills.execution import read_source_free_execution
            if read_source_free_execution(old[0], context['actor']) is None:
                raise PermissionError('AGENT_SKILL_SCOPE_RECEIPT_INVALID')
        elif context['actor_id'] is not None:
            admitted = verified_execution_scope(old[0], context['actor'])
            if not admitted or any(admitted[key] != context['scope'].get(key)
                    for key in ('subject_id', 'brand_focus_id', 'global_scope')):
                raise PermissionError('AGENT_SKILL_SCOPE_RECEIPT_INVALID')
        return {'success': True, 'result': json.loads(old[0]['output_json']), 'skill_execution_id': execution_id}
    try:
        if shared:
            from lumenis.shared.agents.skills.execution import execute_shared_agent_skill
            outcome = execute_shared_agent_skill(task_id, skill_id, inputs, actor=context['actor'],
                execution_id=execution_id, execution_control=_execution_control)
        else:
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
    if context['actor_id'] is not None or shared:
        # Never copy failed/unreceipted handler content (including exception text)
        # into the Agent loop's checkpoint or derived observations.
        rows = query_executions(execution_id=execution_id, limit=1, strict=True)
        from lumenis.shared.agents.skills.execution import read_source_free_execution
        readable = (outcome.get('success') is True and rows
                    and (read_source_free_execution(rows[0], context['actor']) if shared else verified_execution_scope(rows[0], context['actor']))
                    and json.loads(rows[0]['output_json']) == outcome.get('result'))
        if not readable:
            return {'success': False, 'result': None, 'error': 'AGENT_SKILL_RESULT_UNAVAILABLE',
                    'skill_execution_id': execution_id}
    return {'success': outcome.get('success') is True, 'result': outcome.get('result'),
            'error': outcome.get('error') or outcome.get('code'), 'skill_execution_id': execution_id}


def _account_step_id(task_id, skill_id, inputs):
    return 'skillscope_agentstep_' + _digest({'task': task_id, 'skill': skill_id, 'inputs': inputs})[:32]


def _bound_local_handler(task_id, skill_id, *, account=False, conversation_sha256=None,
                         human_memory_sha256=None):
    def handler(*, _execution_control=None, **inputs):
        if _execution_control is not None:
            from .loop import StepExecutionControl
            if type(_execution_control) is not StepExecutionControl:
                raise PermissionError('TOOL_EXECUTION_CONTROL_INVALID')
            _execution_control.check()
        _assert_conversation_snapshot(task_id, conversation_sha256)
        if human_memory_sha256 is not None:
            _assert_task_human_correction_snapshot(task_id, human_memory_sha256)
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
        if human_memory_sha256 is not None:
            _assert_task_human_correction_snapshot(task_id, human_memory_sha256)
        return result
    return handler


def _bound_identity(task_id, skill_id, conversation_sha256=None, human_memory_sha256=None):
    def identity():
        _assert_conversation_snapshot(task_id, conversation_sha256)
        if human_memory_sha256 is not None:
            _assert_task_human_correction_snapshot(task_id, human_memory_sha256)
        result = _current_binding(task_id, skill_id)
        from lumenis.shared.agents.skills.execution import registered_handler_identity
        result['configuration']['handler_identity_sha256'] = registered_handler_identity(skill_id)
        if conversation_sha256 is not None:
            result['configuration']['conversation_context_sha256'] = conversation_sha256
        if human_memory_sha256 is not None:
            result['configuration']['human_correction_memory_sha256'] = human_memory_sha256
        return result
    return identity


def _tool_router(task, conversation_sha256=None, human_memory_sha256=None):
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
            account=task['context'].get('actor_id') is not None,
            conversation_sha256=conversation_sha256, human_memory_sha256=human_memory_sha256)
        identity = _bound_identity(task['task_id'], skill_id, conversation_sha256, human_memory_sha256)
        contract = execution.registered_background_contract(skills.get_skill_info(skill_id))
        router.register_tool(ToolDefinition(skill_id, skill_id, 'Bounded local registered Skill',
            handler=handler, identity_provider=identity, permission_level=ToolPermissionLevel.READ,
            origin='lumenis.shared.agents.skills', resource_uri='skill://' + skill_id,
            dependency_paths=(__file__, skills.__file__, execution.__file__),
            input_schema=contract['input_schema'], output_schema=contract['output_schema'],
            forwards_execution_control=True))
    return router


class _RegisteredPlanner:
    def __init__(self, contract, *, context_validator=None, conversation_sha256=None,
                 human_memory_sha256=None):
        self.contract = contract
        self.context_validator = context_validator
        self.conversation_sha256 = conversation_sha256
        self.human_memory_sha256 = human_memory_sha256
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
                            'human_correction_memory_sha256': self.human_memory_sha256,
                            'measurement': 'NOT_REQUESTED_NO_MODEL', 'model_execution': 'NOT_RUN'})


def _gateway_request(task_id, system, user, context):
    """Typed user-authored task input, never a Canonical external source claim."""
    from ai_task_engine import get_task_engine
    from lumenis.system.ai_gateway.owned_service import OwnedServiceRequest
    task = get_task_engine().get_task(task_id)
    current = authorized_context(task)
    if task.get('status') == 'cancelled':
        raise PermissionError('USER_CANCELLED')
    shared = current['domain_id'] == 'shared'
    if current['actor_id'] is None and not shared:
        raise PermissionError('LOCAL_AGENT_MODEL_SERVICE_UNAVAILABLE')
    policy = agent_source_use_policy()
    pack = context.get('conversation_context_pack')
    expected = pack.get('sha256') if type(pack) is dict else None
    actual = _assert_conversation_snapshot(task_id, expected)
    if actual != pack or context.get('committed_step_receipts', []) != _committed_step_receipts(task, current):
        raise PermissionError('AGENT_CONVERSATION_CONTEXT_INVALID')
    memory_context = context.get('human_correction_memory')
    if type(memory_context) is not dict or memory_context.get('schema') != 'task-user-corrections/v1':
        raise PermissionError('AGENT_MODEL_MEMORY_CONTEXT_INVALID')
    current_memory = _task_human_correction_context(task, current)
    if current_memory != memory_context:
        raise PermissionError('AGENT_MODEL_MEMORY_CONTEXT_CHANGED')
    memory_sha256 = memory_context['snapshot_sha256']
    binding = {'task_context': task['context'], 'conversation_context_sha256': expected,
               'human_correction_memory_sha256': memory_sha256,
               'committed_step_receipts': context.get('committed_step_receipts', [])}
    revision = {'original_task_input': task['user_input'], 'planner_payload_sha256': _digest(user),
                'conversation_context_sha256': expected,
                'human_correction_memory_sha256': memory_sha256}
    return OwnedServiceRequest(operation='agent_plan', request_id='agent-plan:' + task_id,
        job_id=task_id, actor_ref='workspace:local' if current['actor_id'] is None else 'actor:' + str(current['actor_id']),
        domain_id='shared' if shared else 'cth' if current['domain_id'] == 'cth' else 'bmp',
        scope=('shared_workspace:v1' if shared else 'GLOBAL / ALL' if current['scope']['global_scope'] else
               current['scope']['subject_id'] or current['scope']['brand_focus_id']),
        source_use_policy_version=policy['schema'],
        source_use_policy_sha256=_digest(policy), source_binding_sha256=_digest(binding),
        source_evidence_refs=('user-task:' + task_id,
            'task-human-corrections:' + task_id + ':' + memory_sha256),
        input_revision_sha256=_digest(revision),
        system_prompt=system, user_payload=user, response_schema_json=json.dumps({'type': 'object',
            'required': ['steps'], 'properties': {'steps': {'type': 'array', 'maxItems': 8}},
            'additionalProperties': False}), max_output_tokens=2000)


def agent_source_use_policy():
    """Original user input and verified references; never external source bodies."""
    return {'schema': 'agent-planner-current-context-v3', 'training_allowed': False,
            'sources': 'original user task, source-free conversation, same-task explicit human memory corrections, admitted local tool metadata and committed receipt references',
            'human_memory': 'active user-authored corrections for this exact task only; unverified context, never Evidence or Canonical fact',
            'external_source_bodies': 'NOT_GRANTED', 'external_transmission': 'NOT_GRANTED'}


def shared_agent_ai_resource(request, max_steps):
    return ('agent-owned-ai:v1:' + request.job_id + ':' + str(max_steps) + ':'
            + request.source_binding_sha256 + ':' + request.input_revision_sha256)


def validate_shared_agent_ai_resource(resource, *, actor, scope):
    """Pure Permission callback: reconstruct current input, never call a model."""
    import re
    matched = re.fullmatch(r'agent-owned-ai:v1:(task_[0-9a-f]{16}):([1-9]|1[0-5]):([0-9a-f]{64}):([0-9a-f]{64})',
                          resource) if type(resource) is str else None
    if not matched or not AgentLoop._valid_typed_scope('shared', scope):
        return False
    try:
        from ai_task_engine import get_task_engine
        from .planner import _PLANNER_SYSTEM_PROMPT
        task = get_task_engine().get_task(matched[1])
        current = authorized_context(task, actor)
        if current['domain_id'] != 'shared' or current['scope'] != scope:
            return False
        context = _planner_context(task, current)
        user = Planner()._build_user_prompt(task['user_input'], context, int(matched[2]))
        request = _gateway_request(task['task_id'], _PLANNER_SYSTEM_PROMPT, user, context)
        return shared_agent_ai_resource(request, int(matched[2])) == resource
    except Exception:
        return False


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
    shared = current['domain_id'] == 'shared'
    if current['actor_id'] is None and not shared:
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
    resource = 'agent-source-use:v1:' + request.source_binding_sha256 + ':' + request.input_revision_sha256
    if shared:
        resource = shared_agent_ai_resource(request, int(count))
        _, scope_audit_id = permission.authorize_shared_workspace(current['actor'], current['scope'],
            action='read', module='content', _return_audit=True)
        decision = permission.check_shared_workspace_effect(current['actor'], current['scope'],
            permission.OperationType.AI_CALL, resource, module='content', action='read')
    else:
        scoped = permission.check_actor_scope_permission(current['actor'], domain_id=current['domain_id'],
            action='read', module='agent_runtime', **current['scope'])
        if scoped.allowed is not True or scoped.verification_state != 'verified' or not scoped.scope_audit_id:
            raise PermissionError('AGENT_TASK_SCOPE_DENIED')
        scope_audit_id = scoped.scope_audit_id
        decision = permission.get_permission_gate().check(permission.OperationType.AI_CALL,
            resource=resource, caller=request.actor_ref, domain_id=request.domain_id)
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
        request.source_evidence_refs, scope_audit_id, decision.audit_id)


def _planner_context(task, current):
    """Server-authored model context; no implicit source/learning body reads."""
    from account.skills import get_skill_info
    from lumenis.shared.agents.skills.execution import _BACKGROUND_INPUTS, registered_background_contract, registered_handler_identity
    context = dict(current)
    pack = _conversation_snapshot(task, current)
    if pack is not None:
        context['conversation_context_pack'] = pack
    context['human_correction_memory'] = _task_human_correction_context(task, current)
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
                correction_memory_sha256 = live_context['human_correction_memory']['snapshot_sha256']
            except (ValueError, PermissionError) as exc:
                conversation_pack = None
                correction_memory_sha256 = None
                context_error = str(exc)
            conversation_sha256 = conversation_pack['sha256'] if conversation_pack else None
            def validate_execution_context():
                if context_error is not None:
                    raise PermissionError(context_error)
                decision = admission.check('ai_task', fields={'status'})
                if decision.allowed is not True:
                    raise PermissionError(decision.reason)
                if runtime._start_time and runtime._check_budget(0) == 'max_time':
                    raise RuntimeError('AGENT_TASK_DEADLINE_EXCEEDED')
                return _assert_conversation_snapshot(task_id, conversation_sha256)
            def validate_model_context():
                validate_execution_context()
                if correction_memory_sha256 is not None:
                    return _assert_task_human_correction_snapshot(task_id, correction_memory_sha256)
                return None
            planner = (_RegisteredPlanner(contract, context_validator=validate_execution_context,
                                          conversation_sha256=conversation_sha256,
                                          human_memory_sha256=correction_memory_sha256) if contract['mode'] == 'registered' else
                       Planner(gateway_request_factory=partial(_gateway_request, task_id), context_validator=validate_model_context,
                           model_result_reader=durable.read_model_response,
                           model_attempt_reserver=durable.reserve_model_request,
                           model_result_recorder=durable.record_model_response))
            runtime = AgentLoop(config=AgentConfig(max_steps=8, max_replans=0, max_retries=0,
                max_time_seconds=60, step_timeout_seconds=15, max_cost=0.01), planner=planner,
                durable_adapter=durable, tool_binding=_tool_router(current, conversation_sha256,
                    correction_memory_sha256))
            working = None
            try:
                from agent_memory.working import WorkingMemory
                from agent_memory.episodic import EpisodicMemory
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
                    validate_execution_context()
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
