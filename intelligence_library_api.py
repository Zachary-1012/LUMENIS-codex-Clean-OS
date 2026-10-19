#!/usr/bin/env python3
"""Scoped research discovery over the existing Evidence/Importer/catalog owners.

Catalog labels help discovery. They never replace source bytes, scope, rights,
producer verification or current source-use approval, and never create facts.
"""
import hashlib
import json
from pathlib import Path
import sqlite3
from flask import Blueprint, jsonify, request
from lumenis.shared.database import get_repository, main_db_path

intelligence_library_bp = Blueprint('intelligence_library', __name__, url_prefix='/api/intelligence/library')
DB_PATH = main_db_path()
_LIBRARY_ROOT = Path(__file__).resolve().parent / "intelligence_library"
CATALOG_FILTERS = ('sub_library', 'source_origin', 'product', 'domain', 'evidence_level',
                   'knowledge_status', 'landing_status', 'admission_status')


def _get_db():
    return get_repository().connect(read_only=True, wal=False)


def _row_to_dict(row):
    value = dict(row)
    tags = value.get('tags') or []
    if isinstance(tags, str):
        try:
            tags = json.loads(tags)
        except ValueError as exc:
            raise ValueError('LIBRARY_TAGS_INVALID') from exc
    if not isinstance(tags, list) or any(type(tag) is not str for tag in tags):
        raise ValueError('LIBRARY_TAGS_INVALID')
    value['tags'] = tags
    return value


def _catalog_candidate(connection, item, *, asset_id=None):
    """Check a proposed catalog link; this does not authorize the association."""
    provenance = item['provenance']['provenance']
    asset_id = asset_id or (provenance.get('content_origin') or {}).get('research_id')
    if asset_id is None:
        return None
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='intelligence_assets'").fetchone():
        raise ValueError('LIBRARY_SCHEMA_UNAVAILABLE')
    cursor = connection.execute('SELECT * FROM intelligence_assets WHERE asset_id=?', (asset_id,))
    rows = cursor.fetchall()
    if len(rows) != 1:
        raise ValueError('LIBRARY_PARENT_UNAVAILABLE')
    catalog = _row_to_dict(dict(zip((column[0] for column in cursor.description), rows[0])))
    if catalog.get('admission_status') != 'ADMITTED':
        raise ValueError('LIBRARY_PARENT_WITHDRAWN')
    source_context = item['provenance']['context']
    domain = source_context['domain_id']
    allowed_domains = {'cth': {'CTH', 'cth', 'SHARED', 'shared'},
                       'zbmp': {'ZBMP', 'zbmp', 'BMP', 'bmp', 'SHARED', 'shared'}}
    if (catalog.get('domain') not in allowed_domains.get(domain, set())
            or catalog.get('product') not in {'ZBC', 'LUMENIS', 'CTH' if domain == 'cth' else 'ZBMP', 'SHARED'}):
        raise ValueError('LIBRARY_PARENT_CONTEXT_MISMATCH')
    # A user-declared research_id alone does not establish catalog membership.
    # Compare the approved original to the current catalog's confined file;
    # never follow arbitrary source paths or search the surrounding filesystem.
    root = _LIBRARY_ROOT.resolve()
    selected = catalog.get('library_path') or catalog.get('source_path')
    if not isinstance(selected, str) or not selected:
        raise ValueError('LIBRARY_PARENT_BINDING_UNVERIFIED')
    relative = Path(selected)
    if relative.is_absolute():
        path = relative.resolve()
    elif relative.parts and relative.parts[0] == 'intelligence_library':
        path = (root.parent / relative).resolve()
    else:
        path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('LIBRARY_PARENT_BINDING_UNVERIFIED')
    try:
        with path.open('rb') as source:
            raw = source.read(8 * 1024 * 1024 + 1)
    except OSError as exc:
        raise ValueError('LIBRARY_PARENT_UNAVAILABLE') from exc
    if (not 0 < len(raw) <= 8 * 1024 * 1024
            or hashlib.sha256(raw).hexdigest() != item['provenance']['source_fingerprint']):
        raise ValueError('LIBRARY_PARENT_BINDING_UNVERIFIED')
    return catalog


_BINDING_FEATURE = 'INTELLIGENCE_ASSET_SOURCE_BINDING'
_BINDING_VERSION = 'intelligence-asset-source-binding:v1'


def _binding_material(catalog, item):
    # Discovery labels do not grant rights. Bind the catalog identity, exact
    # original Evidence and its signed ownership/use, rather than equal bytes.
    return {'schema': _BINDING_VERSION,
        'catalog': {key: catalog.get(key) for key in
                    ('asset_id', 'source_path', 'library_path', 'product', 'domain')},
        'evidence_id': item['id'], 'source_id': item['asset_id'], 'source_version': item['version'],
        'source_artifact_ref': item['provenance']['source_artifact_ref'],
        'integrity_digest': item['integrity_digest'], 'content_hash': item['content_hash'],
        'source_fingerprint': item['provenance']['source_fingerprint'],
        'context': item['provenance']['context'], 'owner': item['provenance']['owner'],
        'rights': item['provenance']['provenance']['rights'],
        'intended_use': item['provenance']['provenance'].get('intended_use', 'research_reference'),
        'fact_verification': 'NOT_VERIFIED', 'learning_admission': 'NOT_ADMITTED'}


def _binding_json(material):
    return json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _catalog_for_source(connection, item):
    # Research identity is not automatically catalog identity. Only a service
    # receipt can attach a catalog; preserve ordinary independently admitted
    # researcher notes whose research_id is not a catalog association.
    linked = connection.execute("SELECT asset_id FROM app_evidence_records WHERE feature_id=? "
        "AND json_valid(collection_metadata) AND json_extract(collection_metadata, '$.source_id')=?",
        (_BINDING_FEATURE, item['asset_id'])).fetchall()
    if len(linked) > 1:
        raise ValueError('LIBRARY_PARENT_BINDING_CONFLICT')
    asset_id = linked[0][0] if linked else (item['provenance']['provenance'].get('content_origin') or {}).get('research_id')
    if not linked:
        if asset_id is None:
            return None
        table = connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='intelligence_assets'").fetchone()
        catalog_exists = table and connection.execute('SELECT 1 FROM intelligence_assets WHERE asset_id=?', (asset_id,)).fetchone()
        parent_receipt = connection.execute('SELECT 1 FROM app_evidence_records WHERE feature_id=? AND asset_id=?',
                                            (_BINDING_FEATURE, asset_id)).fetchone()
        if not catalog_exists and not parent_receipt:
            return None
    catalog = _catalog_candidate(connection, item, asset_id=asset_id)
    expected = _binding_material(catalog, item)
    cursor = connection.execute('SELECT * FROM app_evidence_records WHERE feature_id=? AND asset_id=?',
                                (_BINDING_FEATURE, catalog['asset_id']))
    rows = cursor.fetchall()
    if not rows:
        raise ValueError('LIBRARY_PARENT_BINDING_REQUIRED')
    if len(rows) != 1:
        raise ValueError('LIBRARY_PARENT_BINDING_CONFLICT')
    receipt = dict(zip((column[0] for column in cursor.description), rows[0]))
    from lumenis.shared.evidence import store
    try:
        valid = (store.classify_evidence_integrity(receipt).get('verified') is True
            and receipt.get('source') == 'intelligence_library'
            and receipt.get('provider') == __name__ and receipt.get('version') == _BINDING_VERSION
            and receipt.get('result') == 'PASS' and receipt.get('status') == 'verified'
            and json.loads(receipt['collection_metadata']) == expected
            and json.loads(receipt['outputs_json']) == {'binding_sha256': hashlib.sha256(_binding_json(expected).encode()).hexdigest()}
            and receipt['content_hash'] == hashlib.sha256(_binding_json(expected).encode()).hexdigest())
    except (TypeError, ValueError, KeyError):
        valid = False
    if not valid:
        raise ValueError('LIBRARY_PARENT_BINDING_UNVERIFIED')
    return catalog


def _require_catalog_migration_authority(connection, actor, scope):
    """Use the existing controlled installation owner, never client role claims.

    Legacy catalog rows have no per-account ownership proof. Only the sealed
    local workspace principal with current whole-workspace write authority can
    migrate them; an ordinary account's own Source/import approval cannot grant
    rights over another legacy catalog identity. Run before reading that object.
    """
    from lumenis.system.security import permission
    code = 'LIBRARY_MIGRATION_AUTHORITY_REQUIRED'
    gate = permission.get_permission_gate()
    if (type(actor) is not permission.LocalWorkspacePrincipal
            or type(gate) is not permission.PermissionGate or not gate.fail_closed
            or permission.is_testing_bypass_enabled()
            or not gate.has_permission(permission.PermissionLevel.COMMIT)
            or not gate.has_permission(permission.PermissionLevel.HUMAN_APPROVAL)):
        raise PermissionError(code)
    decision = permission.check_local_workspace_scope_permission(actor,
        domain_id=scope.get('domain_id') if isinstance(scope, dict) else None,
        module='reports', action='write', global_scope=True,
        subject_id=None, brand_focus_id=None, gate=gate, connection=connection)
    if (decision.allowed is not True or decision.verification_state != 'verified'
            or not decision.audit_id):
        raise PermissionError(code)


def _prepare_catalog_binding(connection, asset_id, evidence_id, *, actor, scope):
    _require_catalog_migration_authority(connection, actor, scope)
    from lumenis.shared.reporting.saved_work import authorize_saved_work, _verified_evidence
    context = authorize_saved_work(actor, scope, action='write', connection=connection)
    item = _verified_evidence(connection, evidence_id, context, actor)
    if item.get('feature_id') != 'DOCUMENT_IMPORT':
        raise ValueError('LIBRARY_BINDING_IMPORTER_SOURCE_REQUIRED')
    provenance = item['provenance']['provenance']
    if provenance.get('intended_use', 'research_reference') not in {'research_reference', 'report_quote'}:
        raise PermissionError('CONTENT_SOURCE_USE_DENIED')
    catalog = _catalog_candidate(connection, item, asset_id=asset_id)
    if catalog is None or catalog['asset_id'] != asset_id:
        raise ValueError('LIBRARY_PARENT_BINDING_UNVERIFIED')
    # Migration cannot use a GLOBAL caller to reassign focused ownership.
    if context != item['provenance']['context']:
        raise PermissionError('LIBRARY_BINDING_CONTEXT_MISMATCH')
    material = _binding_material(catalog, item)
    return material, 'intelligence-asset-bind:v1:' + hashlib.sha256(_binding_json(material).encode()).hexdigest()


def catalog_binding_resource(asset_id, evidence_id, *, actor, scope):
    """Prepare an exact legacy association for explicit DATA_IMPORT approval.

    This is a read-only migration preview. It grants no scope, source-use,
    independent fact verification or admission to learning/production truth.
    """
    with get_repository().connection(read_only=True, wal=False) as connection:
        material, resource = _prepare_catalog_binding(connection, asset_id, evidence_id, actor=actor, scope=scope)
    return {'resource': resource, 'binding': material, 'caller': _binding_json(material['context']),
            'state': 'APPROVAL_REQUIRED'}


def bind_legacy_catalog_asset(asset_id, evidence_id, *, actor, scope):
    """Commit one approved binding through existing Permission/Evidence owners.

    Old catalog rows stay recoverable but unreadable until this exact migration
    is approved. Existing bindings cannot be overwritten or borrowed by copies.
    """
    from lumenis.system.security import permission
    from lumenis.shared.reporting.saved_work import _check_effect, staging_write
    from lumenis.shared.evidence import store
    prepared = catalog_binding_resource(asset_id, evidence_id, actor=actor, scope=scope)
    resource, caller = prepared['resource'], prepared['caller']
    gate = permission.get_permission_gate()
    def authorize(connection=None):
        token = gate.get_valid_approval_token(permission.OperationType.DATA_IMPORT.value, resource, exact=True)
        if token is None:
            raise PermissionError('LIBRARY_BINDING_EXACT_APPROVAL_REQUIRED')
        _check_effect(actor, scope, permission.OperationType.DATA_IMPORT, resource, connection=connection)
        return token
    token = authorize()
    with staging_write(resource), get_repository().transaction() as connection:
        connection.execute('BEGIN IMMEDIATE')
        material, current_resource = _prepare_catalog_binding(connection, asset_id, evidence_id, actor=actor, scope=scope)
        if material != prepared['binding'] or current_resource != resource:
            raise PermissionError('LIBRARY_BINDING_CHANGED')
        authorize(connection)
        if connection.execute("SELECT 1 FROM app_evidence_records WHERE feature_id=? AND (asset_id=? OR "
                              "(json_valid(collection_metadata) AND json_extract(collection_metadata, '$.source_id')=?))",
                              (_BINDING_FEATURE, asset_id, material['source_id'])).fetchone():
            raise ValueError('LIBRARY_PARENT_BINDING_CONFLICT')
        context = material['context']
        digest = hashlib.sha256(_binding_json(material).encode()).hexdigest()
        receipt = store.record_evidence(connection=connection, source='intelligence_library',
            product='CTH' if context['domain_id'] == 'cth' else 'ZBMP',
            feature_id=_BINDING_FEATURE, asset_id=asset_id, version=_BINDING_VERSION,
            provider=__name__, result='PASS', status='verified', env='staging',
            inputs={'binding_resource': resource}, outputs={'binding_sha256': digest},
            raw_content=_binding_json(material), collection_metadata=material,
            domain_id=context['domain_id'], subject_id=context['subject_id'],
            brand_focus_id=context['brand_focus_id'], global_scope=context['global_scope'])
        if type(receipt) is not int or receipt < 1:
            raise RuntimeError('LIBRARY_BINDING_RECEIPT_FAILED')
        if authorize(connection) != token:
            raise PermissionError('LIBRARY_BINDING_APPROVAL_CHANGED')
        with gate.intelligence_catalog_binding_commit_lease(token, resource=resource, caller=caller) as require_current:
            if _prepare_catalog_binding(connection, asset_id, evidence_id, actor=actor, scope=scope)[0] != material:
                raise PermissionError('LIBRARY_BINDING_CHANGED')
            require_current()
            connection.commit()
    return {'state': 'BOUND', 'asset_id': asset_id, 'evidence_id': evidence_id,
            'binding_evidence_id': receipt, 'fact_verification': 'NOT_VERIFIED'}


def verified_research_source(connection, evidence_id, *, actor, context, facts_only=False):
    """Read from the original source owner and recheck its current catalog."""
    from lumenis.shared.reporting.saved_work import _verified_evidence
    item = _verified_evidence(connection, evidence_id, context, actor)
    provenance = item['provenance']['provenance']
    if provenance.get('intended_use', 'research_reference') not in {'research_reference', 'report_quote'}:
        raise PermissionError('CONTENT_SOURCE_USE_DENIED')
    catalog = _catalog_for_source(connection, item)
    if facts_only and catalog is not None and catalog.get('knowledge_status') not in {'FACT', 'VERIFIED'}:
        raise ValueError('LIBRARY_KNOWLEDGE_NOT_ADMITTED')
    result = {
        'evidence_id': evidence_id, 'source_id': item['asset_id'],
        'asset_id': catalog['asset_id'] if catalog else item['asset_id'],
        'content_hash': item['content_hash'], 'integrity_digest': item['integrity_digest'],
        'version': item['version'], 'scope': item['provenance']['context'],
        'rights': provenance['rights'], 'intended_use': provenance.get('intended_use', 'research_reference'),
        'title': provenance['title'], 'summary': item['raw_content'], 'text': item['raw_content'],
        'sub_library': catalog.get('sub_library') if catalog else None,
        'tags': catalog.get('tags', []) if catalog else [],
        'truth_kind': 'source_reference', 'fact_verification': 'NOT_VERIFIED',
        'catalog_bound': catalog is not None,
    }
    if catalog:
        result.update({key: catalog.get(key) for key in CATALOG_FILTERS})
    return result


def _visible_binding_source_refs(connection, *, actor, context):
    """Recover missing-source references only from signed, currently visible links.

    An orphan association must make its owner's read partial, without revealing
    another actor's or subject's missing-source counts to this caller.
    """
    from lumenis.shared.evidence.store import classify_evidence_integrity
    from lumenis.shared.reporting.saved_work import (
        authorize, _client_scope, _context_owner, _shared_context, SavedWorkError,
    )
    cursor = connection.execute('SELECT * FROM app_evidence_records WHERE feature_id=?', (_BINDING_FEATURE,))
    names = [column[0] for column in cursor.description]
    refs = set()
    for row in cursor.fetchall():
        receipt = dict(zip(names, row))
        try:
            material = json.loads(receipt['collection_metadata'])
            digest = hashlib.sha256(_binding_json(material).encode()).hexdigest()
            if (classify_evidence_integrity(receipt).get('verified') is not True
                    or receipt.get('source') != 'intelligence_library'
                    or receipt.get('provider') != __name__ or receipt.get('version') != _BINDING_VERSION
                    or receipt.get('result') != 'PASS' or receipt.get('status') != 'verified'
                    or material.get('schema') != _BINDING_VERSION
                    or material['catalog']['asset_id'] != receipt['asset_id']
                    or receipt['content_hash'] != digest
                    or json.loads(receipt['outputs_json']) != {'binding_sha256': digest}
                    or type(material.get('evidence_id')) is not int or material['evidence_id'] <= 0):
                continue
            original = material['context']
            if _context_owner(original) != _context_owner(context):
                continue
            if not _shared_context(context) and (
                    original.get('domain_id') != context['domain_id']
                    or not context['global_scope'] and original != context):
                continue
            if authorize(actor, _client_scope(original), action='read', connection=connection) != original:
                continue
            refs.add(material['evidence_id'])
        except (KeyError, TypeError, ValueError, PermissionError, SavedWorkError):
            # Unverifiable metadata cannot establish visibility or expose IDs.
            continue
    return refs


def discover_research_sources(connection, *, actor, scope, query='', limit=30, offset=0,
                              filters=None, tags=None, asset_id=None, evidence_ids=None,
                              facts_only=False, catalog_only=False):
    """Search the full admitted population, then paginate verified matches.

    A row that cannot prove scope/parent/use is withheld. Storage errors propagate
    and corrupt candidates make completeness explicit instead of an empty success.
    """
    from lumenis.shared.reporting.saved_work import authorize_saved_work, SavedWorkError
    if (not isinstance(query, str) or len(query) > 2000 or type(limit) is not int or not 1 <= limit <= 200
            or type(offset) is not int or offset < 0):
        raise ValueError('LIBRARY_SEARCH_INVALID')
    filters = filters or {}
    if (not isinstance(filters, dict) or set(filters) - set(CATALOG_FILTERS)
            or any(type(value) is not str for value in filters.values())
            or tags is not None and (type(tags) is not list or any(type(tag) is not str for tag in tags))):
        raise ValueError('LIBRARY_FILTER_INVALID')
    if asset_id is not None and (type(asset_id) is not str or not asset_id or asset_id != asset_id.strip()):
        raise ValueError('LIBRARY_ASSET_ID_INVALID')
    if evidence_ids is not None and (type(evidence_ids) is not list or not 1 <= len(evidence_ids) <= 100
            or any(type(ref) is not int or ref <= 0 for ref in evidence_ids)
            or len(set(evidence_ids)) != len(evidence_ids)):
        raise ValueError('CONTENT_SOURCE_EVIDENCE_REQUIRED')
    context = authorize_saved_work(actor, scope, action='read', connection=connection)
    snapshot = (connection.execute('PRAGMA data_version').fetchone()[0], connection.total_changes)
    candidate_ids = {row[0] for row in connection.execute(
        "SELECT id FROM app_evidence_records WHERE feature_id IN ('DOCUMENT_IMPORT','COLLECTED_SOURCE')")}
    if catalog_only:
        candidate_ids.update(_visible_binding_source_refs(connection, actor=actor, context=context))
    if evidence_ids is not None:
        candidate_ids.intersection_update(evidence_ids)
    records, matched, unavailable, scanned, seen_assets = [], 0, 0, 0, set()
    unavailable_reasons = {}
    # Unbound legacy catalog rows have no provable Source scope. Never expose
    # their identities/counts, but do not claim that an unreadable old catalog
    # is a verified empty library either.
    catalog_binding_required = bool(catalog_only and connection.execute(
        "SELECT 1 FROM intelligence_assets a WHERE a.admission_status='ADMITTED' "
        "AND NOT EXISTS (SELECT 1 FROM app_evidence_records e WHERE e.feature_id=? AND e.asset_id=a.asset_id "
        "AND json_valid(e.collection_metadata) AND json_type(e.collection_metadata, '$.evidence_id')='integer' "
        "AND json_extract(e.collection_metadata, '$.evidence_id')>0) LIMIT 1",
        (_BINDING_FEATURE,)).fetchone())

    for evidence_id in sorted(candidate_ids, reverse=True):
        scanned += 1
        try:
            item = verified_research_source(connection, evidence_id, actor=actor, context=context,
                                            facts_only=facts_only)
        except (SavedWorkError, PermissionError, ValueError) as exc:
            if evidence_ids is not None:
                raise
            before_unavailable = unavailable
            if str(exc) == 'WORK_EVIDENCE_CONTEXT_MISMATCH':
                # The existing Evidence reader uses this code for both hidden
                # scope and invalid signatures. Only a verified foreign scope
                # is an ordinary hidden row; corruption is incomplete reading.
                from lumenis.shared.evidence.store import classify_evidence_integrity
                cursor = connection.execute('SELECT * FROM app_evidence_records WHERE id=?', (evidence_id,))
                raw = cursor.fetchone()
                evidence = dict(zip((column[0] for column in cursor.description), raw)) if raw else {}
                unavailable += classify_evidence_integrity(evidence).get('verified') is not True
            elif str(exc) != 'WORK_PERMISSION_DENIED':
                unavailable += 1
            if unavailable > before_unavailable:
                reason = str(exc) if str(exc).isupper() and all(c.isalpha() or c == '_' for c in str(exc)) else 'SOURCE_VERIFICATION_FAILED'
                unavailable_reasons[reason] = unavailable_reasons.get(reason, 0) + 1
            continue
        if catalog_only:
            if not item['catalog_bound'] or item['asset_id'] in seen_assets:
                continue
            seen_assets.add(item['asset_id'])
        if asset_id is not None and item['asset_id'] != asset_id:
            continue
        if any(item.get(key) != value for key, value in filters.items()):
            continue
        if tags and not all(tag in item['tags'] for tag in tags):
            continue
        searchable = '\n'.join([item['title'], item['text'], item.get('sub_library') or '', *item['tags']]).casefold()
        if not all(term in searchable for term in query.casefold().split()):
            continue
        matched += 1
        if offset < matched <= offset + limit:
            records.append(item)
    if evidence_ids is not None and scanned != len(evidence_ids):
        raise ValueError('WORK_EVIDENCE_MISSING')
    # Re-open the original owners after discovery. No cached generic projection
    # may outlive its source/catalog authorization during the same request.
    for previous in records:
        current = verified_research_source(connection, previous['evidence_id'], actor=actor,
                                           context=context, facts_only=facts_only)
        if current != previous:
            raise PermissionError('CONTENT_SOURCE_STALE')
    if authorize_saved_work(actor, scope, action='read', connection=connection) != context:
        raise PermissionError('CONTENT_CONTEXT_CHANGED')
    if snapshot != (connection.execute('PRAGMA data_version').fetchone()[0], connection.total_changes):
        raise RuntimeError('LIBRARY_SNAPSHOT_CHANGED')
    has_more = matched > offset + len(records)
    return {'records': records, 'matched_count': matched, 'returned_count': len(records),
            'limit': limit, 'offset': offset, 'has_more': has_more,
            'next_offset': offset + len(records) if has_more else None,
            'verification_complete': unavailable == 0 and not catalog_binding_required, 'unavailable_count': unavailable,
            'catalog_binding_code': 'LIBRARY_PARENT_BINDING_REQUIRED' if catalog_binding_required else None,
            'unavailable_reasons': unavailable_reasons,
            'state': 'partial' if unavailable or catalog_binding_required else 'ready' if matched else 'empty'}


def _request_sources(*, query='', limit=50, offset=0, asset_id=None, filters=None):
    from experience_runtime import _content_project_scope
    actor, scope = _content_project_scope('read', read_only_auth=True)
    scope = scope.get('shared_workspace_scope', scope)
    connection = _get_db()
    try:
        if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='intelligence_assets'").fetchone():
            raise ValueError('LIBRARY_SCHEMA_UNAVAILABLE')
        return discover_research_sources(connection, actor=actor, scope=scope, query=query,
            limit=limit, offset=offset, asset_id=asset_id, filters=filters, catalog_only=True)
    finally:
        connection.close()


def _public(item):
    return {key: value for key, value in item.items() if key != 'text'}


def _error(exc):
    if isinstance(exc, sqlite3.Error):
        return jsonify({'ok': False, 'code': 'LIBRARY_STORAGE_UNAVAILABLE'}), 503
    from experience_runtime import _content_project_error
    return _content_project_error(exc)


@intelligence_library_bp.route('', methods=['GET'])
def list_assets():
    try:
        page, per_page = int(request.args.get('page', 1)), int(request.args.get('per_page', 50))
        if page < 1:
            raise ValueError('LIBRARY_SEARCH_INVALID')
        result = _request_sources(query=request.args.get('q', ''), limit=per_page,
            offset=(page - 1) * per_page,
            filters={key: request.args[key] for key in CATALOG_FILTERS if request.args.get(key)})
        return jsonify({'ok': True, 'data': [_public(item) for item in result.pop('records')],
            'pagination': {'page': page, 'per_page': per_page, 'total': result['matched_count'],
                           'total_pages': (result['matched_count'] + per_page - 1) // per_page}, **result})
    except Exception as exc:
        return _error(exc)


@intelligence_library_bp.route('/<asset_id>', methods=['GET'])
def get_asset(asset_id):
    try:
        result = _request_sources(asset_id=asset_id, limit=1)
        if not result['records']:
            return jsonify({'ok': False, 'code': 'LIBRARY_ASSET_NOT_FOUND'}), 404
        return jsonify({'ok': True, 'data': _public(result['records'][0])})
    except Exception as exc:
        return _error(exc)


@intelligence_library_bp.route('/search', methods=['GET'])
def search_assets():
    try:
        query = request.args.get('q', '').strip()
        if not query:
            raise ValueError('LIBRARY_QUERY_REQUIRED')
        result = _request_sources(query=query, limit=int(request.args.get('limit', 50)),
            offset=int(request.args.get('offset', 0)),
            filters={key: request.args[key] for key in CATALOG_FILTERS if request.args.get(key)})
        return jsonify({'ok': True, 'query': query, 'count': result['returned_count'],
                        'data': [_public(item) for item in result.pop('records')], **result})
    except Exception as exc:
        return _error(exc)


def _all_request_sources():
    from experience_runtime import _content_project_scope
    from lumenis.shared.reporting.saved_work import authorize_saved_work
    actor, scope = _content_project_scope('read', read_only_auth=True)
    scope = scope.get('shared_workspace_scope', scope)
    records, offset, complete, unavailable, matched = [], 0, True, 0, None
    reasons, binding_code = {}, None
    connection = _get_db()
    try:
        if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='intelligence_assets'").fetchone():
            raise ValueError('LIBRARY_SCHEMA_UNAVAILABLE')
        context = authorize_saved_work(actor, scope, action='read', connection=connection)
        snapshot = (connection.execute('PRAGMA data_version').fetchone()[0], connection.total_changes)
        while True:
            result = discover_research_sources(connection, actor=actor, scope=scope,
                limit=200, offset=offset, catalog_only=True)
            if matched is not None and matched != result['matched_count']:
                raise RuntimeError('LIBRARY_SNAPSHOT_CHANGED')
            matched = result['matched_count']
            records.extend(result['records'])
            complete = complete and result['verification_complete']
            binding_code = binding_code or result.get('catalog_binding_code')
            unavailable = max(unavailable, result['unavailable_count'])
            for reason, count in result.get('unavailable_reasons', {}).items():
                reasons[reason] = max(reasons.get(reason, 0), count)
            if not result['has_more']:
                break
            offset = result['next_offset']
        if len(records) != matched or len({item['asset_id'] for item in records}) != len(records):
            raise RuntimeError('LIBRARY_SNAPSHOT_CHANGED')
        for previous in records:
            if verified_research_source(connection, previous['evidence_id'], actor=actor,
                    context=context) != previous:
                raise PermissionError('CONTENT_SOURCE_STALE')
        current_actor, current_scope = _content_project_scope('read', read_only_auth=True)
        current_scope = current_scope.get('shared_workspace_scope', current_scope)
        if authorize_saved_work(current_actor, current_scope, action='read', connection=connection) != context:
            raise PermissionError('CONTENT_CONTEXT_CHANGED')
        if snapshot != (connection.execute('PRAGMA data_version').fetchone()[0], connection.total_changes):
            raise RuntimeError('LIBRARY_SNAPSHOT_CHANGED')
        return records, {**result, 'verification_complete': complete, 'unavailable_count': unavailable,
                         'unavailable_reasons': reasons, 'catalog_binding_code': binding_code,
                         'state': 'partial' if not complete else 'ready' if records else 'empty'}
    finally:
        connection.close()


@intelligence_library_bp.route('/stats', methods=['GET'])
def get_stats():
    try:
        records, result = _all_request_sources()
        stats = {'total': len(records)}
        for key in CATALOG_FILTERS:
            counts = {}
            for row in records:
                if row.get(key) is not None:
                    counts[row[key]] = counts.get(row[key], 0) + 1
            stats['by_' + key] = counts
        return jsonify({'ok': True, 'data': stats, 'verification_complete': result['verification_complete'],
                        'state': result['state'], 'unavailable_reasons': result['unavailable_reasons'],
                        'catalog_binding_code': result['catalog_binding_code']})
    except Exception as exc:
        return _error(exc)


@intelligence_library_bp.route('/sub_libraries', methods=['GET'])
def list_sub_libraries():
    try:
        records, result = _all_request_sources()
        counts = {}
        for item in records:
            if item['sub_library'] is not None:
                counts[item['sub_library']] = counts.get(item['sub_library'], 0) + 1
        return jsonify({'ok': True, 'data': [{'name': key, 'count': counts[key]} for key in sorted(counts)],
                        'verification_complete': result['verification_complete'],
                        'state': result['state'], 'unavailable_reasons': result['unavailable_reasons'],
                        'catalog_binding_code': result['catalog_binding_code']})
    except Exception as exc:
        return _error(exc)

# Actor-owned reference adaptations use the same signed Evidence and SavedWork
# owners as the Library. They are not legacy globally-admitted catalog entries,
# importer grants, full-source permissions, or Canonical/FACT records.
_REFERENCE_BINDING_FEATURE = 'INTELLIGENCE_REFERENCE_WORK_BINDING'
_REFERENCE_BINDING_VERSION = 'intelligence-reference-work-binding:v1'


def _reference_binding_material(record, document, context):
    body = document['payload']['research_reference']
    return {'schema': _REFERENCE_BINDING_VERSION,
            'reference': {'artifact_id': record['artifact_id'], 'sha256': record['sha256'],
                          'work_id': document['work_id'], 'version': document['version']},
            'context': context, 'asset_id': body['asset_id'],
            'original_provenance': body['original']['provenance'],
            'lifecycle': body['lifecycle'], 'rights': 'UNKNOWN', 'license': 'UNKNOWN',
            'evidence_level': 'RAW', 'knowledge_status': 'REFERENCE',
            'fact_verification': 'NOT_VERIFIED', 'learning_admission': 'NOT_ADMITTED'}


def _write_reference_work_binding(connection, record, document, *, actor, scope):
    """Called inside SavedWork's existing authorized commit transaction."""
    from lumenis.shared.reporting.saved_work import authorize_saved_work
    from lumenis.shared.evidence import store
    context = authorize_saved_work(actor, scope, action='write', connection=connection)
    if document['context'] != context:
        raise PermissionError('REFERENCE_BINDING_CONTEXT_MISMATCH')
    material = _reference_binding_material(record, document, context)
    digest = hashlib.sha256(_binding_json(material).encode()).hexdigest()
    evidence_id = store.record_evidence(
        connection=connection, source='intelligence_library', product='SHARED',
        feature_id=_REFERENCE_BINDING_FEATURE, asset_id=record['artifact_id'],
        version=_REFERENCE_BINDING_VERSION, provider=__name__, result='REFERENCE',
        status='raw_reference', env='local', level='RAW', authenticity_score=0.0,
        raw_content=_binding_json(material), collection_metadata=material,
        inputs={'reference': material['reference']}, outputs={'binding_sha256': digest})
    if type(evidence_id) is not int or evidence_id < 1:
        raise RuntimeError('REFERENCE_BINDING_WRITE_FAILED')
    return evidence_id


def read_reference_library_source(binding_evidence_id, *, actor, scope, connection=None):
    """Verify signed catalog/source binding and its current exact actor version."""
    from contextlib import nullcontext
    from lumenis.shared.reporting.saved_work import authorize_saved_work
    from lumenis.shared.evidence import store
    from agent_research.reference_work import read_reference_work
    if type(binding_evidence_id) is not int or binding_evidence_id <= 0:
        raise ValueError('REFERENCE_BINDING_ID_INVALID')
    reader = get_repository().connection(read_only=True, wal=False) if connection is None else nullcontext(connection)
    with reader as con:
        if connection is None:
            con.execute('BEGIN')
        context = authorize_saved_work(actor, scope, action='read', connection=con)
        cursor = con.execute('SELECT * FROM app_evidence_records WHERE id=? AND feature_id=?',
                             (binding_evidence_id, _REFERENCE_BINDING_FEATURE))
        raw = cursor.fetchone()
        receipt = dict(zip((column[0] for column in cursor.description), raw)) if raw else {}
        try:
            material = json.loads(receipt['collection_metadata'])
            digest = hashlib.sha256(_binding_json(material).encode()).hexdigest()
            valid = (store.classify_evidence_integrity(receipt).get('verified') is True
                     and receipt['source'] == 'intelligence_library' and receipt['provider'] == __name__
                     and receipt['version'] == _REFERENCE_BINDING_VERSION
                     and receipt['result'] == 'REFERENCE' and receipt['status'] == 'raw_reference'
                     and material['context'] == context and receipt['content_hash'] == digest
                     and json.loads(receipt['outputs_json']) == {'binding_sha256': digest})
        except (ValueError, TypeError, KeyError):
            valid = False
        if not valid:
            raise ValueError('REFERENCE_BINDING_UNAVAILABLE')
        ref = material['reference']
        item = read_reference_work(ref['artifact_id'], actor=actor, scope=scope,
                                   expected_sha256=ref['sha256'], connection=con)
        if material != _reference_binding_material(item['artifact'], item['document'], context):
            raise ValueError('REFERENCE_BINDING_CHANGED')
        return {'binding_evidence_id': binding_evidence_id, 'reference': ref,
                'asset_id': material['asset_id'], 'title': item['document']['title'],
                'record': item, 'catalog_bound': True, 'evidence_level': 'RAW',
                'knowledge_status': 'REFERENCE', 'rights': 'UNKNOWN', 'license': 'UNKNOWN',
                'source_provenance': material['original_provenance'],
                'fact_verification': 'NOT_VERIFIED', 'canonical': False,
                'source_use': 'PRIVATE_REFERENCE_ONLY_NOT_EXTERNAL_SOURCE_AUTHORIZATION'}


def _reference_binding_id(artifact_id, *, actor, scope):
    from lumenis.shared.reporting.saved_work import authorize_saved_work
    with get_repository().connection(read_only=True, wal=False) as con:
        authorize_saved_work(actor, scope, action='read', connection=con)
        rows = con.execute('SELECT id FROM app_evidence_records WHERE feature_id=? AND asset_id=?',
                           (_REFERENCE_BINDING_FEATURE, artifact_id)).fetchall()
        if len(rows) != 1:
            raise ValueError('REFERENCE_BINDING_UNAVAILABLE')
        return rows[0][0]


def adopt_reference_library_asset(asset_id, *, actor, scope, request_id, edits=None):
    from agent_research.reference_work import adopt_reference_asset
    saved = adopt_reference_asset(asset_id, actor=actor, scope=scope, request_id=request_id, edits=edits)
    evidence_id = _reference_binding_id(saved['reference']['artifact_id'], actor=actor, scope=scope)
    return {**read_reference_library_source(evidence_id, actor=actor, scope=scope),
            'replayed': saved['replayed']}


def discover_reference_library_sources(*, actor, scope, query='', limit=30, cursor=None):
    from agent_research.reference_work import list_reference_work
    page = list_reference_work(actor=actor, scope=scope, query=query, limit=limit, cursor=cursor)
    items, unavailable = [], 0
    for row in page['items']:
        try:
            evidence_id = _reference_binding_id(row['artifact']['artifact_id'], actor=actor, scope=scope)
            items.append(read_reference_library_source(evidence_id, actor=actor, scope=scope))
        except ValueError as exc:
            if str(exc) not in {'REFERENCE_NEEDS_REVISION', 'REFERENCE_WITHDRAWN'}:
                unavailable += 1
    return {'items': items, 'has_more': page['has_more'], 'next_cursor': page['next_cursor'],
            'verification_complete': page['verification_complete'] and unavailable == 0,
            'unavailable_count': page['unverified_candidates'] + unavailable,
            'state': 'reference_catalog', 'canonical': False}


def _verify_reference_work_binding(connection, item, context):
    """Receipt check shared by direct reference reads and Library discovery.

    Keep this below the source reader to avoid resolving a reference recursively.
    A valid SavedWork blob alone cannot silently bypass its signed Library link.
    """
    from lumenis.shared.evidence import store
    cursor = connection.execute('SELECT * FROM app_evidence_records WHERE feature_id=? AND asset_id=?',
        (_REFERENCE_BINDING_FEATURE, item['artifact']['artifact_id']))
    rows = cursor.fetchall()
    if len(rows) != 1:
        raise ValueError('REFERENCE_BINDING_UNAVAILABLE')
    receipt = dict(zip((c[0] for c in cursor.description), rows[0]))
    expected = _reference_binding_material(item['artifact'], item['document'], context)
    digest = hashlib.sha256(_binding_json(expected).encode()).hexdigest()
    try:
        valid = (store.classify_evidence_integrity(receipt).get('verified') is True
                 and receipt['source'] == 'intelligence_library' and receipt['provider'] == __name__
                 and receipt['version'] == _REFERENCE_BINDING_VERSION
                 and receipt['result'] == 'REFERENCE' and receipt['status'] == 'raw_reference'
                 and json.loads(receipt['collection_metadata']) == expected
                 and receipt['content_hash'] == digest
                 and json.loads(receipt['outputs_json']) == {'binding_sha256': digest})
    except (ValueError, TypeError, KeyError):
        valid = False
    if not valid:
        raise ValueError('REFERENCE_BINDING_UNAVAILABLE')
    return receipt['id']
