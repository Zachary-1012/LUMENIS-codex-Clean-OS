"""Explicit, signed one-hop dependencies between existing SavedWork versions.

A dependency is the user's declared use of a source, not proof of entailment.
Only this Owner's signed receipt gives payload metadata dependency semantics.
"""
from contextlib import nullcontext
from copy import deepcopy
import json
import re

from . import saved_work
from lumenis.shared.evidence import store

KEY = 'work_dependencies'
SCHEMA = 'lumenis.work-dependencies/v1'


def _latest(artifact_id, *, actor, scope, connection=None):
    work = saved_work.read_committed_work(artifact_id, actor=actor, scope=scope, connection=connection)
    context = saved_work.authorize_saved_work(actor, scope, action='read', connection=connection)
    if connection is None:
        with saved_work.get_repository().connection(read_only=True, wal=False) as con:
            versions = saved_work._versions(con, work['document']['work_id'], context, actor)
    else:
        versions = saved_work._versions(connection, work['document']['work_id'], context, actor)
    if versions[-1]['artifact']['artifact_id'] != artifact_id:
        raise ValueError('DEPENDENCY_VERSION_CHANGED')
    return work


def _binding(work, context):
    return {'schema': SCHEMA, 'context': context,
            'artifact_id': work['artifact']['artifact_id'], 'sha256': work['artifact']['sha256'],
            'work_id': work['document']['work_id'], 'version': work['document']['version'],
            'dependencies_hash': saved_work._digest(work['document']['payload'][KEY])}


def _dependencies(work, actor, scope, connection=None):
    material = work['document']['payload'].get(KEY)
    if material is None:
        return []
    context = saved_work.authorize_saved_work(actor, scope, action='read', connection=connection)
    with (saved_work.get_repository().connection(read_only=True, wal=False)
          if connection is None else nullcontext(connection)) as con:
        rows = con.execute('SELECT * FROM app_evidence_records WHERE source=? AND asset_id=?',
                           (SCHEMA, work['artifact']['artifact_id'])).fetchall()
    if len(rows) != 1 or not store.verify_evidence_record_integrity(rows[0]):
        raise ValueError('DEPENDENCY_OWNER_RECEIPT_REQUIRED')
    row = dict(rows[0])
    if (row.get('provider') != __name__ or row.get('feature_id') != work['artifact']['artifact_id']
            or json.loads(row['inputs_json']).get('binding') != _binding(work, context)):
        raise ValueError('DEPENDENCY_OWNER_RECEIPT_MISMATCH')
    if not isinstance(material, dict) or material.get('schema') != SCHEMA:
        raise ValueError('DEPENDENCY_METADATA_INVALID')
    return deepcopy(material['items'])


def _location(document, location, replacement=None):
    if not isinstance(location, dict):
        raise ValueError('DEPENDENCY_LOCATION_INVALID')
    kind = location.get('type')
    if kind == 'markdown_paragraph' and set(location) == {'type', 'index'}:
        index = location['index']
        paragraphs = document['markdown'].split('\n\n')
        if type(index) is not int or not 0 <= index < len(paragraphs):
            raise ValueError('DEPENDENCY_LOCATION_INVALID')
        old = paragraphs[index]
        if replacement is not None:
            if '\n\n' in replacement:
                raise ValueError('DEPENDENCY_PARAGRAPH_STRUCTURE_CHANGE')
            paragraphs[index] = replacement
            document['markdown'] = '\n\n'.join(paragraphs)
        return old
    if kind == 'topic_card' and set(location) == {'type', 'topic_id', 'field'}:
        if (document.get('contract', {}).get('id') != 'lumenis.podcast-topic-vault'
                or not isinstance(location['field'], str) or location['field'] not in {'title', 'notes'}):
            raise ValueError('DEPENDENCY_LOCATION_INVALID')
        cards = document['payload'].get('topic_cards')
        if not isinstance(cards, list):
            raise ValueError('DEPENDENCY_TOPIC_CARDS_REQUIRED')
        matches = [card for card in cards if isinstance(card, dict) and card.get('topic_id') == location['topic_id']]
        if len(matches) != 1 or not isinstance(matches[0].get(location['field']), str):
            raise ValueError('DEPENDENCY_LOCATION_INVALID')
        old = matches[0][location['field']]
        if replacement is not None:
            if location['field'] == 'title' and len(replacement) > 300:
                raise ValueError('DEPENDENCY_TOPIC_TITLE_TOO_LONG')
            matches[0][location['field']] = replacement
            from podcast.intelligence.topic_planning import render_topic_markdown
            document['markdown'] = render_topic_markdown(document['payload'])
        return old
    raise ValueError('DEPENDENCY_LOCATION_INVALID')


def _source(spec, target, *, actor, scope, connection=None):
    if not isinstance(spec, dict) or set(spec) != {'artifact_id', 'start', 'end', 'quote'}:
        raise ValueError('DEPENDENCY_SOURCE_INVALID')
    source = _latest(spec['artifact_id'], actor=actor, scope=scope, connection=connection)
    if source['document']['work_id'] == target['document']['work_id']:
        raise ValueError('DEPENDENCY_SELF_REFERENCE')
    start, end, quote = spec['start'], spec['end'], spec['quote']
    text = source['document']['markdown']
    if (type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text)
            or not isinstance(quote, str) or not 1 <= len(quote) <= 2000 or text[start:end] != quote):
        raise ValueError('DEPENDENCY_SOURCE_QUOTE_MISMATCH')
    return {**spec, 'work_id': source['document']['work_id'], 'version': source['document']['version'],
            'sha256': source['artifact']['sha256']}


def _spec(bound):
    return {key: bound[key] for key in ('artifact_id', 'start', 'end', 'quote')}


def _replay(artifact_id, request_id, operation, *, actor, scope):
    parent = saved_work.read_committed_work(artifact_id, actor=actor, scope=scope)
    context = saved_work.authorize_saved_work(actor, scope, action='read')
    with saved_work.get_repository().connection(read_only=True, wal=False) as con:
        versions = saved_work._versions(con, parent['document']['work_id'], context, actor)
    for work in versions:
        if work['document']['request_id'] != request_id:
            continue
        if KEY not in work['document']['payload']:
            raise ValueError('DEPENDENCY_REQUEST_REUSE_CONFLICT')
        items = _dependencies(work, actor, scope)
        if (work['document'].get('parent_artifact_id') != artifact_id
                or work['document']['payload'][KEY].get('operation_hash') != saved_work._digest(operation)):
            raise ValueError('DEPENDENCY_REQUEST_REUSE_CONFLICT')
        for item in items:
            saved_work.read_committed_work(item['source']['artifact_id'], actor=actor, scope=scope)
        return {**saved_work.reopen_work(work['artifact']['artifact_id'], actor=actor, scope=scope), 'replayed': True}
    return None


def _save(target, document, items, *, actor, scope, request_id, reason, recheck, operation, reason_limit=2000):
    if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= reason_limit:
        raise ValueError('DEPENDENCY_REASON_REQUIRED')
    for item in items:
        if saved_work._digest(_location(document, item['location'])) != item['target_text_hash']:
            raise ValueError('DEPENDENCY_OTHER_LOCATION_CHANGED')
    document['payload'][KEY] = {'schema': SCHEMA, 'items': items,
                               'operation_hash': saved_work._digest(operation), 'reason': reason.strip(), 'semantics': 'explicit-user-dependency-not-fact-verification'}

    def commit(con, artifact, committed_document):
        recheck(con)
        context = saved_work.authorize_saved_work(actor, scope, action='write', connection=con)
        receipt = store.record_evidence(
            source=SCHEMA, feature_id=artifact['artifact_id'], asset_id=artifact['artifact_id'],
            product='SHARED' if context.get('scope_kind') == 'shared_workspace' else ('ZBMP' if context.get('domain_id') == 'zbmp' else 'CTH'),
            domain_id=context.get('domain_id'), subject_id=context.get('subject_id'),
            brand_focus_id=context.get('brand_focus_id'), global_scope=context.get('global_scope', False),
            inputs={'binding': _binding({'artifact': artifact, 'document': committed_document}, context)},
            outputs={'dependency_recorded': True, 'source_entailment': 'NOT_VERIFIED'},
            account=context.get('principal_ref') or 'actor:' + str(context['actor_id']),
            provider=__name__, status='pending', capture_mode='explicit-actor-dependency', connection=con)
        row = con.execute('SELECT * FROM app_evidence_records WHERE id=?', (receipt,)).fetchone()
        if not store.verify_evidence_record_integrity(row):
            raise ValueError('DEPENDENCY_RECEIPT_SIGNING_FAILED')

    return saved_work.save_work(
        title=document['title'], markdown=document['markdown'], kind=document['kind'],
        payload=document['payload'], citations=document['citations'], contract=document['contract'],
        task_id=document.get('task_id'), assertion_id=document.get('assertion_id'),
        request_id=request_id, actor=actor, scope=scope, work_id=document['work_id'],
        previous_artifact_id=target['artifact']['artifact_id'],
        expected_draft_digest=target['document']['draft_digest'], before_commit=commit)


def bind_dependency(artifact_id, *, actor, scope, dependency_id, location, source,
                    expected_text, request_id, reason, replace_bindings=False):
    if type(replace_bindings) is not bool:
        raise ValueError("DEPENDENCY_REPLACEMENT_INVALID")
    operation = {'mode': 'bind', 'dependency_id': dependency_id, 'location': location, 'source': source, 'expected_text': expected_text, 'reason': reason}
    if replace_bindings:
        operation['replace_bindings'] = True
    replay = _replay(artifact_id, request_id, operation, actor=actor, scope=scope)
    if replay is not None:
        return replay
    target = _latest(artifact_id, actor=actor, scope=scope)
    # Explicit replacement discards every old claim. No old receipt, source
    # reference or location becomes authoritative through this new declaration.
    items = [] if replace_bindings else _dependencies(target, actor, scope)
    if (not isinstance(dependency_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', dependency_id)
            or len(items) >= 20 or any(item['id'] == dependency_id or item['location'] == location for item in items)):
        raise ValueError('DEPENDENCY_ID_OR_LOCATION_CONFLICT')
    document = deepcopy(target['document'])
    if _location(document, location) != expected_text:
        raise ValueError('DEPENDENCY_TARGET_CHANGED')
    bound = _source(source, target, actor=actor, scope=scope)
    item = {'id': dependency_id, 'location': location, 'target_text_hash': saved_work._digest(expected_text), 'source': bound}
    items.append(item)

    def recheck(con):
        if _source(source, target, actor=actor, scope=scope, connection=con) != bound:
            raise ValueError('DEPENDENCY_SOURCE_CHANGED')
        for previous in items[:-1]:
            # Historical source versions remain inspectable, but must still be readable.
            saved_work.read_committed_work(previous['source']['artifact_id'], actor=actor, scope=scope, connection=con)

    return _save(target, document, items, actor=actor, scope=scope, request_id=request_id, reason=reason, recheck=recheck, operation=operation)


def preview_impact(artifact_id, *, actor, scope):
    target = _latest(artifact_id, actor=actor, scope=scope)
    items = _dependencies(target, actor, scope)
    result = []
    context = saved_work.authorize_saved_work(actor, scope, action='read')
    for item in items:
        # Fail closed before returning any dependent/source text if source access was revoked.
        source = saved_work.read_committed_work(item['source']['artifact_id'], actor=actor, scope=scope)
        if source['artifact']['sha256'] != item['source']['sha256']:
            raise ValueError('DEPENDENCY_SOURCE_CHANGED')
        with saved_work.get_repository().connection(read_only=True, wal=False) as con:
            versions = saved_work._versions(con, item['source']['work_id'], context, actor)
        current = saved_work.read_committed_work(versions[-1]['artifact']['artifact_id'], actor=actor, scope=scope)
        text = _location(target['document'], item['location'])
        if saved_work._digest(text) != item['target_text_hash']:
            raise ValueError('DEPENDENCY_TARGET_CHANGED')
        result.append({'id': item['id'], 'location': item['location'], 'target_text': text,
                       'bound_source': item['source'],
                       'current_source': {'artifact_id': current['artifact']['artifact_id'],
                                          'sha256': current['artifact']['sha256'], 'version': current['document']['version']},
                       'state': 'SOURCE_VERSION_CHANGED' if current['artifact']['artifact_id'] != item['source']['artifact_id'] else 'CURRENT'})
    preview = {'artifact_id': artifact_id, 'sha256': target['artifact']['sha256'], 'items': result,
               'automatic_rewrite': False, 'source_entailment': 'NOT_VERIFIED'}
    return {**preview, 'preview_hash': saved_work._digest(preview)}


def accept_update(artifact_id, *, actor, scope, dependency_id, source, replacement_text,
                  expected_preview_hash, request_id, reason):
    operation = {'mode': 'accept', 'dependency_id': dependency_id, 'source': source, 'replacement_text': replacement_text, 'expected_preview_hash': expected_preview_hash, 'reason': reason}
    replay = _replay(artifact_id, request_id, operation, actor=actor, scope=scope)
    if replay is not None:
        return replay
    preview = preview_impact(artifact_id, actor=actor, scope=scope)
    if preview['preview_hash'] != expected_preview_hash:
        raise ValueError('DEPENDENCY_PREVIEW_CHANGED')
    target = _latest(artifact_id, actor=actor, scope=scope)
    items = _dependencies(target, actor, scope)
    matches = [item for item in items if item['id'] == dependency_id]
    if len(matches) != 1:
        raise ValueError('DEPENDENCY_NOT_FOUND')
    if (not isinstance(replacement_text, str) or not 1 <= len(replacement_text.strip()) <= 10000
            or any(ord(c) < 32 and c not in '\n\t' for c in replacement_text)):
        raise ValueError('DEPENDENCY_REPLACEMENT_INVALID')
    selected = matches[0]
    bound = _source(source, target, actor=actor, scope=scope)
    if bound['work_id'] != selected['source']['work_id']:
        raise ValueError('DEPENDENCY_SOURCE_WORK_MISMATCH')
    document = deepcopy(target['document'])
    _location(document, selected['location'], replacement_text)
    selected.update(source=bound, target_text_hash=saved_work._digest(replacement_text))

    def recheck(con):
        if _source(source, target, actor=actor, scope=scope, connection=con) != bound:
            raise ValueError('DEPENDENCY_SOURCE_CHANGED')
        for item in items:
            saved_work.read_committed_work(item['source']['artifact_id'], actor=actor, scope=scope, connection=con)
        for observed in preview['items']:
            _latest(observed['current_source']['artifact_id'], actor=actor, scope=scope, connection=con)

    return _save(target, document, items, actor=actor, scope=scope, request_id=request_id, reason=reason, recheck=recheck, operation=operation)


def revise_owned_work(artifact_id, *, actor, scope, request_id, expected_sha256,
                      reason, edits, citations=None, source_adoptions=None):
    """Continue verified dependencies through ordinary, non-dependent edits.

    Generic storage remains unable to mint this owner's receipt. No source
    adoption, location inference or copied-metadata authorization occurs here.
    """
    target, document = saved_work._prepare_work_revision(artifact_id, actor=actor,
        scope=scope, request_id=request_id, expected_sha256=expected_sha256,
        reason=reason, edits=edits, citations=citations, source_adoptions=source_adoptions)
    if not isinstance(target['document']['payload'].get(KEY), dict):
        raise ValueError('DEPENDENCY_OWNER_RECEIPT_REQUIRED')
    items = _dependencies(target, actor, scope)
    for edit in edits:
        tokens = tuple(token.replace('~1', '/').replace('~0', '~')
                       for token in edit['pointer'][1:].split('/'))
        if tokens[:2] == ('payload', KEY):
            raise ValueError('DEPENDENCY_METADATA_EDIT_FORBIDDEN')
    if (document['citations'] != target['document']['citations'] or source_adoptions):
        raise ValueError('DEPENDENCY_EXPLICIT_SOURCE_ADOPTION_REQUIRED')
    old_text, new_text = target['document']['markdown'], document['markdown']
    if old_text != new_text:
        old_parts, new_parts = old_text.split('\n\n'), new_text.split('\n\n')
        if len(old_parts) != len(new_parts):
            raise ValueError('DEPENDENCY_LOCATION_CHANGE_REQUIRES_REBIND')
        for item in items:
            location = item['location']
            if location.get('type') != 'markdown_paragraph':
                raise ValueError('DEPENDENCY_LOCATION_CHANGE_REQUIRES_REBIND')
            text = _location(target['document'], location)
            if (_location(document, location) != text or old_parts.count(text) != 1
                    or new_parts.count(text) != 1):
                raise ValueError('DEPENDENCY_LOCATION_CHANGE_REQUIRES_REBIND')
    for item in items:
        if saved_work._digest(_location(document, item['location'])) != item['target_text_hash']:
            raise ValueError('DEPENDENCY_TARGET_CHANGED')
    operation = {'mode': 'revise', 'expected_sha256': expected_sha256,
                 'edits': deepcopy(edits), 'reason': reason,
                 'citations': deepcopy(document['citations']),
                 'source_adoptions': deepcopy(source_adoptions or [])}
    replay = _replay(artifact_id, request_id, operation, actor=actor, scope=scope)
    if replay is not None:
        return replay
    _latest(artifact_id, actor=actor, scope=scope)

    def sources(connection=None):
        heads = []
        context = saved_work.authorize_saved_work(actor, scope, action='read', connection=connection)
        for item in items:
            bound = item['source']
            source = saved_work.read_committed_work(bound['artifact_id'], actor=actor,
                                                   scope=scope, connection=connection)
            source_doc = source['document']
            if (source['artifact']['sha256'] != bound['sha256']
                    or source_doc['work_id'] != bound['work_id']
                    or source_doc['version'] != bound['version']
                    or source_doc['markdown'][bound['start']:bound['end']] != bound['quote']):
                raise ValueError('DEPENDENCY_SOURCE_CHANGED')
            with (saved_work.get_repository().connection(read_only=True, wal=False)
                  if connection is None else nullcontext(connection)) as con:
                versions = saved_work._versions(con, bound['work_id'], context, actor)
            head = saved_work.read_committed_work(versions[-1]['artifact']['artifact_id'],
                                                 actor=actor, scope=scope, connection=connection)
            heads.append((head['artifact']['artifact_id'], head['artifact']['sha256']))
        return heads

    observed_heads = sources()
    def recheck(con):
        # save_work already serialized and checked latest parent before staging
        # this child. Calling _latest(parent) now would see our own staged child.
        current = saved_work.read_committed_work(artifact_id, actor=actor, scope=scope, connection=con)
        if (current['artifact']['sha256'] != expected_sha256
                or current['document'] != target['document']
                or _dependencies(current, actor, scope, connection=con) != items):
            raise ValueError('DEPENDENCY_PARENT_CHANGED')
        if sources(connection=con) != observed_heads:
            raise ValueError('DEPENDENCY_SOURCE_CHANGED')

    return _save(target, document, items, actor=actor, scope=scope,
                 request_id=request_id, reason=reason, recheck=recheck,
                 operation=operation, reason_limit=4000)
