"""Actor-scoped research reference lifecycle on the existing SavedWork owner.

Immutable seed bodies remain reference-only; every adoption/edit/state change is
an actor-authorized SavedWork version. These wrappers create no new truth store.
"""
from __future__ import annotations
from contextlib import nullcontext
from copy import deepcopy
import json
import re
from .reference_assets import query_reference_assets

SCHEMA = 'lumenis.research-reference/v1'


def _owner():
    from lumenis.shared.reporting import saved_work
    return saved_work


def _reference(item):
    return {'artifact_id': item['artifact']['artifact_id'], 'sha256': item['artifact']['sha256'],
            'work_id': item['document']['work_id'], 'version': item['document']['version']}


def _body(item):
    body = item['document'].get('payload', {}).get('research_reference')
    if not isinstance(body, dict) or body.get('schema') != SCHEMA:
        raise ValueError('NOT_A_RESEARCH_REFERENCE')
    return body


def _edit(body, edits):
    body = deepcopy(body)
    if edits is None:
        return body
    if not isinstance(edits, dict):
        raise ValueError('REFERENCE_EDITS_INVALID')
    scenario = body['original']['kind'] == 'scenarios'
    allowed = {'inputs', 'work', 'goal'} if scenario else {'data'}
    if set(edits) - allowed:
        raise ValueError('REFERENCE_EDITS_INVALID')
    current = body['current']
    for key, value in edits.items():
        if key == 'goal':
            if not isinstance(value, str) or not value.strip():
                raise ValueError('REFERENCE_GOAL_INVALID')
            current['goal'] = value
        else:
            if not isinstance(value, dict):
                raise ValueError('REFERENCE_EDITS_INVALID')
            if key == 'data' and set(value).intersection({
                    'rights', 'license', 'canonical', 'classification', 'review_status',
                    'evidence', 'source', 'source_url', 'effective_date'}):
                raise ValueError('REFERENCE_PROVENANCE_EDIT_FORBIDDEN')
            # Shallow per-field replacement preserves unspecified original fields;
            # original is separately immutable across all revisions.
            target = current if key == 'data' else current.setdefault(key, {})
            target.update(deepcopy(value))
    body['amendments_status'] = 'USER_DECLARED_NOT_EXTERNALLY_VERIFIED'
    return body


def _save(body, *, actor, scope, request_id, parent=None):
    owner = _owner()
    owner.authorize_saved_work(actor, scope, action='write')
    title = 'Research reference: ' + body['asset_id']
    markdown = 'Historical research reference; rights UNKNOWN; not Canonical fact.\n\n' + json.dumps(body, ensure_ascii=False, sort_keys=True, indent=2)
    args = dict(title=title, markdown=markdown, kind='research',
                payload={'research_reference': body}, citations=[], request_id=request_id,
                actor=actor, scope=scope)
    if parent:
        args.update(work_id=parent['document']['work_id'],
                    previous_artifact_id=parent['artifact']['artifact_id'],
                    expected_draft_digest=parent['document']['draft_digest'])
    from intelligence_library_api import _write_reference_work_binding
    args['before_commit'] = lambda con, record, document: _write_reference_work_binding(
        con, record, document, actor=actor, scope=scope)
    try:
        item = owner.save_work(**args)
    except owner.SavedWorkError as exc:
        if str(exc) in ('WORK_REVISION_CONFLICT', 'WORK_DRAFT_REVISION_CONFLICT'):
            raise ValueError('REFERENCE_NEEDS_REVISION') from exc
        raise
    return {**item, 'reference': _reference(item), 'current_status': body['lifecycle']}


def adopt_reference_asset(asset_id: str, *, actor, scope, request_id: str, edits=None):
    owner = _owner()
    owner.authorize_saved_work(actor, scope, action='write')
    matches = [r for r in query_reference_assets(page_size=100)['items'] if r['asset_id'] == asset_id]
    if len(matches) != 1:
        raise ValueError('REFERENCE_ASSET_NOT_FOUND')
    original = matches[0]
    current = deepcopy(original['data'])
    if original['kind'] == 'scenarios':
        current['goal'] = current.get('expected_outcome', '')
        current['inputs'].setdefault('budget_currency', None)
    body = {'schema': SCHEMA, 'asset_id': asset_id, 'original': original, 'current': current,
            'lifecycle': 'active', 'classification': original['classification'],
            'license': 'UNKNOWN', 'rights': 'UNKNOWN', 'review_status': 'PENDING_REVERIFICATION',
            'canonical': False, 'amendments_status': 'NONE', 'state_reason': 'user_adopted_reference'}
    return _save(_edit(body, edits), actor=actor, scope=scope, request_id=request_id)


def read_reference_work(artifact_id: str, *, actor, scope, expected_sha256=None,
                        require_current=True, connection=None):
    """Fresh authorized read with exact hash and complete same-work version scan.

    Caller should invoke again in its commit/read transaction for dependencies.
    Historical reads require explicit require_current=False and return stale state;
    they never resurrect a withdrawn version as a usable current reference.
    """
    owner = _owner()
    if expected_sha256 is not None and (not isinstance(expected_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_sha256)):
        raise ValueError('REFERENCE_HASH_INVALID')
    if connection is not None:
        from lumenis.system.security import permission
        permission._require_canonical_scope_connection(connection)
    reader = owner.get_repository().connection(read_only=True, wal=False) if connection is None else nullcontext(connection)
    with reader as con:
        if connection is None:
            con.execute('BEGIN')
        context = owner.authorize_saved_work(actor, scope, action='read', connection=con)
        item = owner.read_committed_work(artifact_id, actor=actor, scope=scope, connection=con)
        _body(item)
        if expected_sha256 is not None and item['artifact']['sha256'] != expected_sha256:
            raise ValueError('REFERENCE_HASH_MISMATCH')
        # Existing owner validates each version's actor/scope and complete chain.
        # Its 1000-version bound fails closed, never silently truncates latest.
        versions = owner._versions(con, item['document']['work_id'], context, actor)
        latest = owner.read_committed_work(versions[-1]['artifact']['artifact_id'], actor=actor, scope=scope, connection=con)
        from intelligence_library_api import _verify_reference_work_binding
        _verify_reference_work_binding(con, item, context)
        if latest['artifact']['artifact_id'] != artifact_id:
            _verify_reference_work_binding(con, latest, context)
        state = _body(latest)['lifecycle']
        changed = latest['artifact']['artifact_id'] != artifact_id
        if require_current and state == 'withdrawn':
            raise ValueError('REFERENCE_WITHDRAWN')
        if require_current and changed:
            raise ValueError('REFERENCE_NEEDS_REVISION')
        owner.authorize_saved_work(actor, scope, action='read', connection=con)
        item.pop('content', None)  # Raw committed bytes are internal, not HTTP JSON.
        return {**item, 'reference': _reference(item), 'current_reference': _reference(latest),
                'current_status': 'withdrawn' if state == 'withdrawn' else 'needs_revision' if changed else 'active'}


def revise_reference_work(artifact_id: str, *, actor, scope, request_id: str,
                          expected_sha256: str, operation='update', edits=None):
    owner = _owner()
    owner.authorize_saved_work(actor, scope, action='write')
    if not isinstance(expected_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', expected_sha256):
        raise ValueError('REFERENCE_HASH_INVALID')
    if operation not in ('update', 'withdraw', 'restore'):
        raise ValueError('REFERENCE_OPERATION_INVALID')
    parent = read_reference_work(artifact_id, actor=actor, scope=scope,
                                 expected_sha256=expected_sha256, require_current=False)
    # SavedWork checks request replay before CAS, so identical retries remain
    # idempotent while new requests against stale parents fail at commit.
    body = deepcopy(_body(parent))
    if operation == 'restore' and body['lifecycle'] != 'withdrawn':
        raise ValueError('REFERENCE_NOT_WITHDRAWN')
    if operation != 'restore' and body['lifecycle'] == 'withdrawn':
        raise ValueError('REFERENCE_WITHDRAWN')
    if operation != 'update' and edits is not None:
        raise ValueError('REFERENCE_STATE_EDITS_FORBIDDEN')
    if operation == 'update':
        body = _edit(body, edits)
    body['lifecycle'] = 'withdrawn' if operation == 'withdraw' else 'active'
    body['state_reason'] = 'user_' + operation
    return _save(body, actor=actor, scope=scope, request_id=request_id, parent=parent)


def list_reference_work(*, actor, scope, query='', limit=30, cursor=None):
    """Same SavedWork pagination; retain continuation across unrelated work."""
    result = _owner().search_work(actor=actor, scope=scope, query=query, limit=limit,
                                  cursor=cursor, kind='research')
    result['items'] = [{**r, 'reference': _reference(r)} for r in result['items']
                       if r['document'].get('payload', {}).get('research_reference', {}).get('schema') == SCHEMA]
    return result
