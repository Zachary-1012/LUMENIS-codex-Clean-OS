"""Opt-in fixed-source observations in the existing Collector queue/Evidence owners.

No daemon, pin mutation, automatic review or Canonical truth promotion. The
review owner must separately approve exact material through record_source_review.
"""
from __future__ import annotations
import hashlib
import json
import re
import time
from lumenis.shared.evaluation.openai_math_papers import provenance as p
from lumenis.shared.evaluation.openai_math_papers.core import digest
from lumenis.shared.database import get_repository
from lumenis.shared.evidence.store import record_evidence, verify_evidence_record_integrity
from lumenis.shared.reporting.saved_work import authorize
from lumenis.system.security import OperationType, get_permission_gate
from ...adapters.public_source import fetch_public_url

CONFIG_SOURCE = 'collector:math_upstream_schedule'
OBS_SOURCE = 'collector:math_upstream_observation'
TASK_TYPE = 'collect_math_upstream_review'
SCHEMA = 'lumenis.math-upstream-observation/v1'
HEAD_URL = 'https://api.github.com/repos/openai/math/commits/main'


def sources():
    result = {}
    for family, entry in p.REGISTRY.items():
        result[entry['path']] = {'family': family, 'identity': entry['manuscript_identity'], 'blob': entry['blob'], 'kind': 'manuscript'}
        if entry.get('additional_path'):
            result[entry['additional_path']] = {'family': family, 'identity': entry['dependency_identities'][0], 'blob': entry['additional_blob'], 'kind': 'dependency'}
    result['history.md'] = {'family': None, 'identity': 'openai/math:history.md', 'blob': None, 'kind': 'history'}
    return result


def _rows(con, source):
    rows = con.execute('SELECT * FROM app_evidence_records WHERE source=? ORDER BY id', (source,)).fetchall()
    result = []
    for row in rows:
        row = dict(row)
        if not verify_evidence_record_integrity(row):
            raise ValueError('UPSTREAM_EVIDENCE_INTEGRITY')
        result.append((row['id'], json.loads(row['outputs_json'])))
    return result


def _principal(actor, scope, con=None):
    return authorize(actor, scope, action='write', connection=con)


def configuration(*, schedule_id, cadence_seconds, enabled, actor, scope):
    if not isinstance(schedule_id, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', schedule_id):
        raise ValueError('UPSTREAM_SCHEDULE_ID')
    if type(cadence_seconds) is not int or not 3600 <= cadence_seconds <= 604800 or type(enabled) is not bool:
        raise ValueError('UPSTREAM_CADENCE_OR_ENABLED')
    material = {'schedule_id': schedule_id, 'cadence_seconds': cadence_seconds, 'enabled': enabled,
                'principal': _principal(actor, scope), 'sources': sources(), 'head_url': HEAD_URL,
                'implementation_pin': p.UPSTREAM_COMMIT, 'review_owner': 'openai_math_papers.provenance.record_source_review'}
    return {**material, 'resource': 'math-upstream-schedule:' + digest(material)}


def _permission(config, actor, scope, con=None, collect=False):
    principal = _principal(actor, scope, con)
    if principal != config['principal'] or config['sources'] != sources() or config['implementation_pin'] != p.UPSTREAM_COMMIT:
        raise PermissionError('UPSTREAM_BINDING_CHANGED')
    _validate_configuration(config)
    caller = principal.get('principal_ref') or f"actor:{principal['actor_id']}"
    gate = get_permission_gate()
    operations = [OperationType.CONFIG_MODIFY]
    if collect:
        operations += [OperationType.COLLECTOR_START, OperationType.EXTERNAL_NETWORK]
    for operation in operations:
        if gate.get_valid_approval_token(operation.value, config['resource'], exact=True) is None:
            raise PermissionError('UPSTREAM_EXACT_APPROVAL_REQUIRED:' + operation.value)
        decision = gate.check(operation, resource=config['resource'], caller=caller, exact_approval_required=True,
                              domain_id='bmp' if principal['domain_id'] == 'zbmp' else 'cth')
        if not decision.allowed:
            raise PermissionError('UPSTREAM_PERMISSION_DENIED')


def configure(*, schedule_id, cadence_seconds, enabled, actor, scope):
    config = configuration(schedule_id=schedule_id, cadence_seconds=cadence_seconds, enabled=enabled, actor=actor, scope=scope)
    with get_repository().connection() as con:
        con.execute('BEGIN IMMEDIATE')
        _permission(config, actor, scope, con)
        history = _configuration_history(con, schedule_id)
        if history and history[0][1]['principal'] != config['principal']:
            raise PermissionError('UPSTREAM_SCHEDULE_OWNER_MISMATCH')
        ident = record_evidence(connection=con, source=CONFIG_SOURCE, product='Shared', feature_id='G165',
                                outputs=config, result='PASS', status='verified', raw_content=json.dumps(config, sort_keys=True))
        con.commit()
    return {'configuration_evidence_id': ident, **config}


def _validate_configuration(config):
    material = {k: v for k, v in config.items() if k != 'resource'}
    if config.get('resource') != 'math-upstream-schedule:' + digest(material):
        raise PermissionError('UPSTREAM_CONFIG_INTEGRITY')


def _configuration_history(con, schedule_id):
    history = [(i, c) for i, c in _rows(con, CONFIG_SOURCE) if c['schedule_id'] == schedule_id]
    for _, config in history:
        _validate_configuration(config)
    return history


def _current(con, schedule_id):
    history = _configuration_history(con, schedule_id)
    if not history:
        raise PermissionError('UPSTREAM_NOT_CONFIGURED')
    # The first signed configuration owns this ID permanently. Historical
    # cross-scope overwrites cannot take ownership or hide the original owner.
    owner = history[0][1]['principal']
    return next((i, c) for i, c in reversed(history) if c['principal'] == owner)


def _observation_configuration(con, observation, owner):
    """Reopen the exact signed acquisition version, never today's bare ID."""
    history = _configuration_history(con, observation['schedule_id'])
    origin = next((c for i, c in history if i == observation.get('configuration_evidence_id')), None)
    if (type(observation.get('configuration_evidence_id')) is not int
            or not history or history[0][1]['principal'] != owner or origin is None
            or origin['principal'] != owner
            or observation.get('principal', owner) != owner
            or observation.get('configuration_resource', origin['resource']) != origin['resource']
            or observation.get('implementation_pin', origin['implementation_pin']) != origin['implementation_pin']):
        raise PermissionError('UPSTREAM_OBSERVATION_SCOPE_MISMATCH')
    return origin


def _observations(con, schedule_id, owner):
    configurations = dict(_configuration_history(con, schedule_id))
    result = []
    for ident, observation in _rows(con, OBS_SOURCE):
        if observation.get('schedule_id') != schedule_id:
            continue
        origin = configurations.get(observation.get('configuration_evidence_id'))
        if origin is not None and origin['principal'] != owner:
            # Preserve foreign historical evidence without exposing it or
            # preventing the first owner's valid observations from recovering.
            continue
        _observation_configuration(con, observation, owner)
        row = dict(con.execute('SELECT * FROM app_evidence_records WHERE id=?', (ident,)).fetchone())
        inputs = json.loads(row['inputs_json'])
        expected = {'domain_id': owner['domain_id'], 'product_id': {'cth': 'CTH', 'zbmp': 'ZBMP'}[owner['domain_id']]}
        expected['global'] = owner['global_scope']
        if owner['subject_id'] is not None:
            expected['subject_id'] = owner['subject_id']
        if owner['brand_focus_id'] is not None:
            expected['brand_focus_id'] = owner['brand_focus_id']
        if (inputs.get('configuration_evidence_id') != observation['configuration_evidence_id']
                or inputs.get('_lumenis_scope') != expected):
            raise PermissionError('UPSTREAM_OBSERVATION_CUSTODY_MISMATCH')
        result.append((ident, observation))
    return result


def tick(queue, *, actor, scope, now=None):
    now = time.time() if now is None else float(now)
    with get_repository().connection(read_only=True) as con:
        schedule_ids = {config['schedule_id'] for _, config in _rows(con, CONFIG_SOURCE)}
        latest = {schedule_id: _current(con, schedule_id) for schedule_id in schedule_ids}
        admitted = []
        for ident, config in latest.values():
            if config['enabled'] and config['principal'] == _principal(actor, scope, con):
                _permission(config, actor, scope, con, collect=True)
                admitted.append((ident, config))
    jobs = []
    for ident, config in admitted:
        bucket = int(now // config['cadence_seconds'])
        key = digest({'configuration': ident, 'bucket': bucket})
        jobs.append(queue.enqueue_once(TASK_TYPE, {'schedule_id': config['schedule_id'],
                    'configuration_evidence_id': ident, 'bucket': bucket}, key))
    return jobs


def _fetch(url):
    response = fetch_public_url(url, timeout=10, max_bytes=500_000,
                                allowed_host_suffixes=('api.github.com', 'raw.githubusercontent.com'))
    if response.status_code != 200 or response.url != url:
        raise RuntimeError('UPSTREAM_HTTP_UNAVAILABLE')
    return response.content


def _sha(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{40}', value):
        raise ValueError('UPSTREAM_VERSION_UNKNOWN')
    return value


def collect_observation(fetch=_fetch):
    head = json.loads(fetch(HEAD_URL))
    commit = _sha(head.get('sha'))
    tree_sha = _sha(head.get('commit', {}).get('tree', {}).get('sha'))
    tree_url = f'https://api.github.com/repos/openai/math/git/trees/{tree_sha}?recursive=1'
    raw_tree = fetch(tree_url)
    tree = json.loads(raw_tree)
    if tree.get('sha') != tree_sha or tree.get('truncated') is not False or not isinstance(tree.get('tree'), list):
        raise ValueError('UPSTREAM_TREE_INCOMPLETE')
    entries = {}
    for entry in tree['tree']:
        path = entry.get('path')
        if path in sources():
            if path in entries or entry.get('type') != 'blob':
                raise ValueError('UPSTREAM_TREE_AMBIGUOUS')
            entries[path] = _sha(entry.get('sha'))
    observations = []
    for path, spec in sources().items():
        blob = entries.get(path)
        change = 'UNCHANGED_PINNED_FRAGMENT' if blob == spec['blob'] and blob else 'REVIEW_REQUIRED'
        item = {**spec, 'path': path, 'observed_blob': blob, 'status': change,
                'change_kind': 'history_requires_review' if spec['kind'] == 'history' else 'deleted' if blob is None else 'source_change' if blob != spec['blob'] else 'unchanged',
                'source_url': f'https://github.com/openai/math/blob/{commit}/{path}',
                'rights': 'public-reference-only', 'canonical_truth': False}
        if change == 'REVIEW_REQUIRED' and blob:
            content = fetch(f'https://raw.githubusercontent.com/openai/math/{commit}/{path}')
            if len(content) > 500_000 or hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest() != blob:
                raise ValueError('UPSTREAM_BLOB_INTEGRITY')
            item.update(content=content.decode('utf-8'), content_sha256=hashlib.sha256(content).hexdigest())
        observations.append(item)
    return {'schema': SCHEMA, 'upstream_commit': commit, 'tree_sha': tree_sha,
            'tree_url': tree_url, 'tree_content': raw_tree.decode('utf-8'),
            'tree_sha256': hashlib.sha256(raw_tree).hexdigest(), 'sources': observations,
            'status': 'REVIEW_REQUIRED' if any(i['status'] == 'REVIEW_REQUIRED' for i in observations) else 'NO_FRAGMENT_CHANGE',
            'production_review_changed': False, 'implementation_pin': p.UPSTREAM_COMMIT,
            'review_owner': 'openai_math_papers.provenance.record_source_review'}


def processor(queue, *, actor_provider, fetch=_fetch):
    """actor_provider resolves a current server principal; payload cannot grant it."""
    def process(task):
        if task.get('task_type') != TASK_TYPE:
            return False
        payload = task['payload']
        actor, scope = actor_provider()
        def admitted(con):
            ident, config = _current(con, payload['schedule_id'])
            if ident != payload['configuration_evidence_id'] or not config['enabled']:
                raise PermissionError('UPSTREAM_SCHEDULE_SUPERSEDED')
            _permission(config, actor, scope, con, collect=True)
            return config['principal']
        with get_repository().connection(read_only=True) as con:
            principal = admitted(con)
            for ident, observation in _observations(con, payload['schedule_id'], principal):
                if (observation.get('request_key') == payload['request_key']
                        and observation.get('configuration_evidence_id') == payload['configuration_evidence_id']
                        and observation.get('acquisition_status') == 'OBSERVED'):
                    return True
        acquired = time.time()
        try:
            observation = collect_observation(fetch)
            observation.update(acquisition_status='OBSERVED', last_verified_acquisition_at=acquired)
        except (RuntimeError, ValueError, OSError, KeyError, TypeError) as exc:
            observation = {'schema': SCHEMA, 'acquisition_status': 'UNKNOWN', 'status': 'FETCH_UNAVAILABLE',
                           'error_code': type(exc).__name__, 'last_verified_acquisition_at': None,
                           'production_review_changed': False}
        observation.update(request_key=payload['request_key'], schedule_id=payload['schedule_id'],
                           configuration_evidence_id=payload['configuration_evidence_id'], attempted_at=acquired,
                           principal=principal)
        receipt = {k: task[k] for k in ('run_id', 'worker_id', 'lease_owner')}
        with queue.attempt_guard(task['id'], **receipt) as valid:
            if not valid:
                raise RuntimeError('UPSTREAM_LEASE_SUPERSEDED')
            with get_repository().connection() as con:
                con.execute('BEGIN IMMEDIATE')
                verified_principal = admitted(con)
                # Only the server-verified normalized business domain selects custody.
                # Shared/content is not admitted by this owner's scope contract.
                product = {'cth': 'CTH', 'zbmp': 'ZBMP'}[verified_principal['domain_id']]
                # Evidence commit may precede queue ACK: recover without duplicating observations.
                existing = [(i, o) for i, o in _observations(con, payload['schedule_id'], verified_principal)
                            if o.get('request_key') == payload['request_key']
                            and o.get('configuration_evidence_id') == payload['configuration_evidence_id']
                            and o.get('acquisition_status') == 'OBSERVED']
                if not existing:
                    record_evidence(connection=con, source=OBS_SOURCE, product=product, feature_id='G165',
                        outputs=observation, inputs={'configuration_evidence_id': payload['configuration_evidence_id']},
                        raw_content=json.dumps(observation, sort_keys=True), status='pending', result='GAP',
                        domain_id=verified_principal['domain_id'], global_scope=verified_principal['global_scope'],
                        subject_id=verified_principal['subject_id'], brand_focus_id=verified_principal['brand_focus_id'])
                con.commit()
        return observation['acquisition_status'] == 'OBSERVED'
    return process


def read_handoff(*, schedule_id, actor, scope):
    with get_repository().connection(read_only=True) as con:
        _, config = _current(con, schedule_id)
        _permission(config, actor, scope, con)
        observations = [{'evidence_id': i, **o} for i, o in _observations(con, schedule_id, config['principal'])]
    verified = [o for o in observations if o['acquisition_status'] == 'OBSERVED']
    return {'observations': observations, 'last_verified_acquisition_at': verified[-1]['attempted_at'] if verified else None,
            'current_status': observations[-1]['status'] if observations else 'NOT_RUN',
            'review_owner': config['review_owner'], 'review_permission': 'SEPARATE_EXACT_MATERIAL_APPROVAL_REQUIRED',
            'production_review_changed': False}


def prepare_changed_review(*, evidence_id, path, actor, scope):
    """Exact stored changed-fragment reference -> existing review-owner arguments.

    History interpretation/withdrawals and missing blobs require a reviewer to
    acquire appropriate evidence; no keyword inference or guessed family mapping.
    """
    with get_repository().connection(read_only=True) as con:
        matches = [o for i, o in _rows(con, OBS_SOURCE) if i == evidence_id]
        if len(matches) != 1 or matches[0].get('acquisition_status') != 'OBSERVED':
            raise ValueError('UPSTREAM_OBSERVATION_UNAVAILABLE')
        observation = matches[0]
        _, config = _current(con, observation['schedule_id'])
        _permission(config, actor, scope, con)
        _observation_configuration(con, observation, config['principal'])
        if not any(i == evidence_id for i, _ in _observations(con, observation['schedule_id'], config['principal'])):
            raise PermissionError('UPSTREAM_OBSERVATION_UNAVAILABLE')
        candidates = [item for item in observation['sources'] if item['path'] == path]
        if len(candidates) != 1:
            raise ValueError('UPSTREAM_SOURCE_UNKNOWN')
        item = candidates[0]
        if item['kind'] == 'history' or item['change_kind'] != 'source_change' or not item.get('content'):
            raise ValueError('UPSTREAM_MANUAL_INTERPRETATION_REQUIRED')
        content = item['content']
        if hashlib.sha256(content.encode()).hexdigest() != item['content_sha256']:
            raise ValueError('UPSTREAM_CONTENT_HASH')
        principal = _principal(actor, scope, con)
    args = dict(identity=item['identity'], state='REVIEW_REQUIRED', evidence_url=item['source_url'],
                evidence_sha256=item['content_sha256'], upstream_commit=observation['upstream_commit'],
                change_kind='source_change', evidence_content=content)
    material = {k: v for k, v in args.items() if k != 'evidence_content'}
    material.update(schema=p.REVIEW_SCHEMA, implementation_pin=p.UPSTREAM_COMMIT,
                    reviewer=principal.get('principal_ref') or f"actor:{principal['actor_id']}", review_scope=principal)
    return {'resource': 'math-source-review:' + digest(material), 'review_arguments': args,
            'observation_evidence_id': evidence_id, 'production_review_changed': False}


def apply_changed_review(*, evidence_id, path, actor, scope):
    prepared = prepare_changed_review(evidence_id=evidence_id, path=path, actor=actor, scope=scope)
    return p.record_source_review(**prepared['review_arguments'], actor=actor, scope=scope)
