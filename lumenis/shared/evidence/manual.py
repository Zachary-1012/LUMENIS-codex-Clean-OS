# -*- coding: utf-8 -*-
"""
LUMENIS Shared Evidence · Manual/App Evidence Adapter

定位：Shared Evidence 的人工/App 证据采集能力（Shadow模式，不碰App自动化）
- 用户主动打开App → 截图/分享 → 上传 → OCR/手动字段识别 → 证据记录 → 人工确认 → Shadow
- 禁止：自动登录、自动浏览、私有API、逆向签名、抓包、绕风控
- 数据只做Shadow记录，不进入生产高频采集链路

最小对象：
AppEvidence
├── id
├── source              来源平台（xhs_app / douyin_app / weibo_app）
├── capture_mode        采集方式（screenshot / share_link / manual_input）
├── captured_at         截图/采集时间
├── topic               关联话题
├── metric_name         指标名（browse_count / discussion_count / note_count等）
├── metric_value        指标值
├── evidence_hash       证据文件哈希（去重用）
├── evidence_path       证据文件本地路径
├── parse_confidence    解析置信度（0-1，OCR或手动输入）
├── verified_by         人工确认人
├── verified_at         确认时间
├── status              状态（pending / confirmed / rejected / shadow）
├── notes               备注
├── created_at
├── updated_at
"""
import os
import logging
import json
import re
import hashlib
import sqlite3
from pathlib import Path
from datetime import datetime
from flask import jsonify, request

# ========== 配置 ==========
MODULE_VERSION = '1.0.0-shadow'
PROJECT_ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = os.path.join(
    os.environ.get('ZBC_DATA_DIR') or str(PROJECT_ROOT / 'data'),
    'app_evidence',
)
# 上传安全限制（对齐 INGESTION_AND_TERMINOLOGY_STANDARD）
EVIDENCE_ALLOWED_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp',  # 图片
    '.pdf', '.txt', '.csv',                              # 文档
    '.mp4', '.mov', '.webm',                             # 视频
}
EVIDENCE_MAX_FILE_SIZE_MB = 500
EVIDENCE_MAX_FILE_SIZE_BYTES = EVIDENCE_MAX_FILE_SIZE_MB * 1024 * 1024

from lumenis.shared.database import get_repository, main_db_path  # Shared Database canonical authority
DB_PATH = main_db_path()

# 支持的来源平台
SUPPORTED_SOURCES = ['xhs_app', 'douyin_app', 'weibo_app', 'other']
# 支持的采集方式
SUPPORTED_CAPTURE_MODES = ['screenshot', 'share_link', 'manual_input']
# 支持的指标名
SUPPORTED_METRICS = ['browse_count', 'discussion_count', 'note_count', 'like_count', 'comment_count', 'collect_count', 'other']
# 状态
STATUS_PENDING = 'pending'
STATUS_CONFIRMED = 'confirmed'
STATUS_REJECTED = 'rejected'
STATUS_SHADOW = 'shadow'

# Canonical table/schema ownership lives in Shared Evidence Store.
from . import store as evidence_store


logger = logging.getLogger(__name__)

class ManualEvidenceError(ValueError):
    """Stable errors for the existing manual Evidence adapter."""


def _get_db():
    return get_repository().connect()


def init_db():
    evidence_store.init_evidence_store(main_db_path())


def _now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _authorize(actor, scope, action='read', connection=None):
    from lumenis.system.security import permission
    if not isinstance(scope, dict) or set(scope) != {'domain_id', 'subject_id', 'brand_focus_id', 'global_scope'}:
        raise ManualEvidenceError('EVIDENCE_SCOPE_REQUIRED')
    domain = scope['domain_id']
    product = 'CTH' if domain == 'cth' else 'ZBMP'
    expected = evidence_store._normalize_record_evidence_scope(product=product, **scope)
    checker = (permission.check_local_workspace_scope_permission
               if type(actor) is permission.LocalWorkspacePrincipal else permission.check_actor_scope_permission)
    decision = checker(actor, module='evidence', action=action, **scope, connection=connection)
    if decision.verification_state != 'verified':
        raise ManualEvidenceError('EVIDENCE_AUTHORIZATION_UNAVAILABLE')
    if not decision.allowed:
        raise PermissionError('EVIDENCE_SCOPE_DENIED')
    identity = (actor.principal_ref if type(actor) is permission.LocalWorkspacePrincipal else 'actor:' + str(actor['id']))
    return expected, identity


def _read_record(con, record_id, expected):
    if type(record_id) is not int or record_id < 1:
        raise ManualEvidenceError('EVIDENCE_ID_INVALID')
    row = con.execute('SELECT * FROM app_evidence_records WHERE id=?', (record_id,)).fetchone()
    if row is None:
        return None
    record = dict(row)
    try:
        marker = json.loads(record['inputs_json']).get(evidence_store._EVIDENCE_SCOPE_KEY)
    except (ValueError, TypeError, AttributeError):
        return None
    if (marker != expected or record.get('domain_id') != expected['domain_id']
            or record.get('product_id') != expected['product_id'] or record.get('source') not in SUPPORTED_SOURCES
            or record.get('feature_id') not in ('APP_MANUAL_EVIDENCE', '', None)):
        return None
    if not evidence_store.verify_evidence_record_integrity(record):
        raise ManualEvidenceError('EVIDENCE_INTEGRITY_UNAVAILABLE')
    return record


def _file_state(record):
    path = record.get('evidence_path')
    if not path:
        return 'NOT_APPLICABLE'
    resolved = Path(path).resolve()
    if Path(EVIDENCE_DIR).resolve() not in resolved.parents or Path(path).is_symlink():
        return 'OUTSIDE_MANAGED_STORE'
    if not resolved.is_file():
        return 'MISSING'
    # New captures bind the original bytes into the signed Evidence metadata.
    # Legacy rows without this field retain their existence-only file state.
    inputs = json.loads(record.get('inputs_json') or '{}')
    expected_hash = inputs.get('manual_capture', {}).get('file_sha256')
    if expected_hash:
        try:
            with resolved.open('rb') as stream:
                actual_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
        except OSError:
            return 'CHECK_UNAVAILABLE'
        if actual_hash != expected_hash:
            return 'INTEGRITY_MISMATCH'
    return 'AVAILABLE'


def _discard_uncommitted_upload(path):
    """Remove only an uncommitted file created by this upload attempt.

    Readback/response failure can happen after a durable commit. In that case,
    or when DB state is uncertain, preserve the original bytes for recovery.
    """
    if not path:
        return
    try:
        with get_repository().connection(read_only=True, wal=False) as con:
            committed = con.execute(
                'SELECT 1 FROM app_evidence_records WHERE evidence_path=? LIMIT 1', (path,)
            ).fetchone()
        if committed is None and _file_state({'evidence_path': path}) == 'AVAILABLE':
            os.remove(path)
    except (OSError, sqlite3.Error):
        logger.warning('Failed upload bytes retained because cleanup state is uncertain')


def get_evidence(record_id, *, actor=None, scope=None):
    expected, _ = _authorize(actor, scope)
    with get_repository().connection(read_only=True, wal=False) as con:
        record = _read_record(con, record_id, expected)
    _authorize(actor, scope)
    return {**record, 'file_state': _file_state(record)} if record else None


def _records(actor, scope):
    expected, _ = _authorize(actor, scope)
    rows, offset = [], 0
    while True:
        page = evidence_store.query_scoped_evidence(product=expected['product_id'], **scope, limit=200, offset=offset)
        if not page:
            break
        for record in page:
            if record.get('source') not in SUPPORTED_SOURCES or record.get('feature_id') not in ('APP_MANUAL_EVIDENCE', '', None):
                continue
            if not evidence_store.verify_evidence_record_integrity(record):
                raise ManualEvidenceError('EVIDENCE_INTEGRITY_UNAVAILABLE')
            rows.append({**record, 'file_state': _file_state(record)})
        offset += len(page)
    _authorize(actor, scope)
    return rows


def list_evidence(status=None, topic=None, source=None, limit=50, offset=0, *, actor=None, scope=None):
    if type(limit) is not int or not 1 <= limit <= 200 or type(offset) is not int or offset < 0:
        raise ManualEvidenceError('INVALID_EVIDENCE_QUERY')
    rows = [row for row in _records(actor, scope)
            if (not status or row['status'] == status) and (not topic or topic in (row.get('topic') or ''))
            and (not source or row['source'] == source)]
    return {'records': rows[offset:offset+limit], 'total': len(rows), 'limit': limit, 'offset': offset}


def get_stats(*, actor=None, scope=None):
    rows = _records(actor, scope)
    result = {name: sum(row['status'] == name for row in rows)
              for name in (STATUS_PENDING, STATUS_CONFIRMED, STATUS_REJECTED, STATUS_SHADOW, 'withdrawn')}
    result.update(total=len(rows), by_source={}, by_metric={}, module_version=MODULE_VERSION, mode='shadow_only')
    for row in rows:
        for group, key in (('by_source', 'source'), ('by_metric', 'metric_name')):
            value = row.get(key)
            result[group][value] = result[group].get(value, 0) + 1
    return result


def _resource(expected, identity, action, material):
    payload = {'scope': expected, 'actor': identity, 'action': action, 'material': material}
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False).encode('utf-8')
    return 'manual-evidence:v1:' + hashlib.sha256(raw).hexdigest()


def _effect(actor, scope, operation, resource, connection=None):
    from lumenis.system.security import permission
    _, identity = _authorize(actor, scope, 'write', connection)
    if permission.is_testing_bypass_enabled():
        raise PermissionError('EVIDENCE_PERMISSION_UNVERIFIED')
    decision = permission.get_permission_gate().check(operation, resource=resource, caller=identity,
        domain_id='bmp' if scope['domain_id'] in ('bmp','zbmp') else 'cth',
        exact_approval_required=operation == permission.OperationType.DATA_DELETE)
    if not decision.allowed:
        raise PermissionError('EVIDENCE_EFFECT_PERMISSION_DENIED')
    return identity


def _fenced(resource):
    from lumenis.system.security.action_firewall import AgentAction
    from lumenis.system.security.effect_fence import get_effect_fence
    import uuid
    fence = get_effect_fence()
    decision = fence.check(action=AgentAction.WRITE, target='manual-evidence-shadow',
                           payload={'effect_mode':'staging', 'resource':resource},
                           operation_id='manual-evidence-attempt:' + uuid.uuid4().hex)
    if not decision.allowed:
        raise PermissionError('EVIDENCE_EFFECT_FENCE_DENIED')
    return fence, decision


def _scope_args(expected):
    return {'product': expected['product_id'], 'domain_id': expected['domain_id'],
            'subject_id': expected.get('subject_id'), 'brand_focus_id': expected.get('brand_focus_id'),
            'global_scope': expected['global']}


def create_evidence(source='xhs_app', capture_mode='screenshot', captured_at=None,
                    topic=None, metric_name=None, metric_value=None,
                    evidence_path=None, parse_confidence=1.0, notes=None, *, actor=None, scope=None):
    expected, identity = _authorize(actor, scope, 'write')
    if not metric_name or metric_value is None or source not in SUPPORTED_SOURCES or capture_mode not in SUPPORTED_CAPTURE_MODES:
        raise ManualEvidenceError('EVIDENCE_INPUT_INVALID')
    file_hash = None
    if evidence_path:
        state = _file_state({'evidence_path':evidence_path})
        if state != 'AVAILABLE':
            raise ManualEvidenceError('EVIDENCE_FILE_UNAVAILABLE')
        with open(evidence_path, 'rb') as stream:
            file_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    material = {'source':source, 'capture_mode':capture_mode, 'captured_at':captured_at,
                'topic':topic, 'metric_name':metric_name, 'metric_value':str(metric_value),
                'file_sha256':file_hash, 'notes':notes}
    resource = _resource(expected, identity, 'create', material)
    from lumenis.system.security.permission import OperationType
    _effect(actor, scope, OperationType.DB_WRITE, resource)
    fence, attempt = _fenced(resource)
    committed = False
    try:
        with get_repository().transaction() as con:
            _effect(actor, scope, OperationType.DB_WRITE, resource, con)
            record_id = evidence_store.record_evidence(source=source, feature_id='APP_MANUAL_EVIDENCE',
                capture_mode=capture_mode, captured_at=captured_at, metric_name=metric_name,
                metric_value=str(metric_value), topic=topic or '', notes=notes or '', status=STATUS_PENDING,
                result='PENDING', inputs={'manual_capture':material, 'actor':identity, 'resource':resource,
                                         'fence_operation_id':attempt.idempotency_key,
                                         'use_permission':'NOT_GRANTED_BY_MANUAL_CAPTURE'},
                evidence_path=evidence_path, parse_confidence=parse_confidence,
                **_scope_args(expected), connection=con)
            _effect(actor, scope, OperationType.DB_WRITE, resource, con)
        committed = True
        fence.complete(attempt.idempotency_key, success=True)
    except BaseException:
        if not committed:
            fence.complete(attempt.idempotency_key, success=False)
        raise
    return get_evidence(record_id, actor=actor, scope=scope), None


def _has_references(con, record_id):
    def quote(name): return '"' + name.replace('"', '""') + '"'
    values = {str(record_id), 'app_evidence_records:' + str(record_id)}
    def references(value):
        if isinstance(value, list):
            return any(references(item) for item in value)
        if isinstance(value, dict):
            return any((key in {'evidence_id','evidence_ref','scope_evidence_ref','source_evidence_ref','creation_evidence_ref',
                               'rights_evidence_ref','review_evidence_ref','analysis_evidence_ref','rejected_candidate_evidence_ref'} and str(item) in values)
                       or (key in {'source_evidence_refs','evidence_refs','review_evidence_refs'} and isinstance(item,list)
                           and any(str(ref) in values for ref in item))
                       or (isinstance(item, (list,dict)) and references(item)) for key,item in value.items())
        return isinstance(value, str) and value == 'app_evidence_records:' + str(record_id)
    for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        for fk in con.execute('PRAGMA foreign_key_list(' + quote(table) + ')'):
            if fk[2].lower() == 'app_evidence_records' and fk[4] in (None, 'id'):
                if con.execute('SELECT 1 FROM ' + quote(table) + ' WHERE ' + quote(fk[3]) + '=? LIMIT 1', (record_id,)).fetchone():
                    return True
        columns = {row[1] for row in con.execute('PRAGMA table_info(' + quote(table) + ')')}
        for column in columns & {'scope_evidence_ref','source_evidence_ref','creation_evidence_ref','evidence_ref','evidence_id'}:
            if con.execute('SELECT 1 FROM ' + quote(table) + ' WHERE CAST(' + quote(column) + ' AS TEXT) IN (?,?) LIMIT 1',
                           (str(record_id), 'app_evidence_records:' + str(record_id))).fetchone():
                return True
        json_columns = columns & {'source_refs_json', 'evidence_refs_json'}
        if table == 'daily_reports' and 'source_snapshot' in columns:
            json_columns.add('source_snapshot')
        if table == 'evaluation_records' and 'metadata' in columns:
            json_columns.add('metadata')
        if table == 'app_evidence_records':
            json_columns.update(columns & {'inputs_json', 'outputs_json', 'collection_metadata'})
        for column in json_columns:
            query = ('SELECT ' + quote(column) + ' FROM ' + quote(table) +
                     ' WHERE ' + quote(column) + " IS NOT NULL AND " + quote(column) + " != ''")
            parameters = ()
            if table == 'app_evidence_records':
                query += ' AND id != ?'
                parameters = (record_id,)
            for row in con.execute(query, parameters):
                # The retained Reporting engine writes this exact legacy text
                # format, containing note/time/count criteria and no Evidence
                # IDs. Unknown non-JSON snapshots still fail closed.
                if (table == 'daily_reports' and column == 'source_snapshot'
                        and isinstance(row[0], str)
                        and re.fullmatch(r'notes:publish_date\[[^,\[\];]{1,64},[^,\[\];]{1,64}\];subject:verified;stats_count=\d+', row[0])):
                    continue
                try:
                    parsed = json.loads(row[0])
                    if (references(parsed) or column == 'evidence_refs_json' and isinstance(parsed,list)
                            and any(str(ref) in values for ref in parsed)):
                        return True
                except (TypeError, ValueError) as exc:
                    raise ManualEvidenceError('EVIDENCE_REFERENCE_CHECK_UNAVAILABLE') from exc
    # SavedWork's Artifact row indexes the first citation only; the existing
    # immutable document owner retains every citation in its JSON bytes.
    if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='lumenis_shared_artifacts'").fetchone():
        from lumenis.shared.reporting import saved_work
        import shared_artifacts
        root = shared_artifacts.artifact_root()
        for row in con.execute("SELECT artifact_id,relative_path FROM lumenis_shared_artifacts WHERE kind='saved_document'"):
            try:
                path = (root / row['relative_path']).resolve()
                if not path.is_relative_to(root) or not path.is_file() or not 0 < path.stat().st_size <= saved_work._LIMIT:
                    raise ValueError('SavedWork reference bytes unavailable')
                # The owner reader validates registry size/hash, full schema and
                # context. This guard reads references only, grants no content
                # use and never exposes another saved document to the caller.
                with path.open('rb') as stream:
                    context = json.loads(stream.read(saved_work._LIMIT + 1)).get('context')
                document = saved_work._read(con, row['artifact_id'], context, verify_sources=False)['document']
                if references(document['citations']):
                    return True
            except (OSError, TypeError, ValueError, KeyError) as exc:
                raise ManualEvidenceError('EVIDENCE_REFERENCE_CHECK_UNAVAILABLE') from exc
    return False


def evidence_transition_resource(record_id, status, reason, *, actor=None, scope=None):
    expected, identity = _authorize(actor, scope, 'write')
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
        raise ManualEvidenceError('EVIDENCE_REASON_REQUIRED')
    record = get_evidence(record_id, actor=actor, scope=scope)
    if record is None:
        raise LookupError('EVIDENCE_NOT_FOUND')
    return _resource(expected, identity, 'transition', {'record_id':record_id, 'before_digest':record['integrity_digest'],
                                                      'status':status, 'reason':reason})


def update_evidence_status(record_id, status, verified_by=None, notes=None, *, actor=None, scope=None, reason=None):
    if status not in (STATUS_PENDING, STATUS_CONFIRMED, STATUS_REJECTED, STATUS_SHADOW, 'withdrawn'):
        raise ManualEvidenceError('EVIDENCE_STATUS_INVALID')
    expected, identity = _authorize(actor, scope, 'write')
    resource = evidence_transition_resource(record_id, status, reason, actor=actor, scope=scope)
    current = get_evidence(record_id, actor=actor, scope=scope)
    if current['status'] == status:
        # Re-reading an immutable terminal state is not another mutation/grant.
        return current, None
    from lumenis.system.security.permission import OperationType
    operation = OperationType.DATA_DELETE if status == 'withdrawn' else OperationType.DB_WRITE
    _effect(actor, scope, operation, resource)
    fence, attempt = _fenced(resource)
    committed = False
    try:
        with get_repository().transaction() as con:
            _effect(actor, scope, operation, resource, con)
            before = _read_record(con, record_id, expected)
            if before is None:
                raise LookupError('EVIDENCE_NOT_FOUND')
            actual = _resource(expected, identity, 'transition', {'record_id':record_id,
                'before_digest':before['integrity_digest'], 'status':status, 'reason':reason})
            if actual != resource:
                raise ManualEvidenceError('EVIDENCE_VERSION_CHANGED')
            if _has_references(con, record_id):
                raise ManualEvidenceError('EVIDENCE_REFERENCED')
            if before['status'] == 'withdrawn' and status != STATUS_PENDING:
                raise ManualEvidenceError('EVIDENCE_RESTORE_TO_PENDING_REQUIRED')
            if status in (STATUS_CONFIRMED, STATUS_SHADOW) and _file_state(before) not in ('AVAILABLE', 'NOT_APPLICABLE'):
                raise ManualEvidenceError('EVIDENCE_FILE_UNAVAILABLE')
            now = _now()
            con.execute('UPDATE app_evidence_records SET status=?, verified_by=?, verified_at=?, updated_at=? WHERE id=?',
                        (status, identity, now, now, record_id))
            evidence_store._sign_evidence_record(con, record_id)
            history_id = evidence_store.record_evidence(source='manual_lifecycle', feature_id='APP_MANUAL_LIFECYCLE',
                inputs={'record_id':record_id,'actor':identity,'reason':reason,'resource':resource,
                        'prior_record':before,'fence_operation_id':attempt.idempotency_key},
                outputs={'status':status,'file_state':_file_state(before)}, status='recorded', result='RECORDED',
                **_scope_args(expected), connection=con)
            _effect(actor, scope, operation, resource, con)
        committed = True
        fence.complete(attempt.idempotency_key, success=True)
    except BaseException:
        if not committed:
            fence.complete(attempt.idempotency_key, success=False)
        raise
    return get_evidence(record_id, actor=actor, scope=scope), None


def delete_evidence(record_id, *, actor=None, scope=None, reason=None):
    """Withdraw a record atomically; original bytes and audit history are retained."""
    update_evidence_status(record_id, 'withdrawn', actor=actor, scope=scope, reason=reason)
    return True, None


def parse_screenshot_manual(evidence_path, topic=None, metric_name=None, metric_value=None, notes=None, *, actor=None, scope=None):
    return create_evidence(evidence_path=evidence_path, topic=topic, metric_name=metric_name,
                           metric_value=metric_value, notes=notes, actor=actor, scope=scope)


def register_app_evidence(app):
    init_db()
    def boundary(call, action='read'):
        from .api import resolve_evidence_request_scope
        try:
            context, error = resolve_evidence_request_scope(action)
            if error:
                return error
            scope = {key:context[key] for key in ('domain_id','subject_id','brand_focus_id','global_scope')}
            result = call(context['actor'], scope)
            return jsonify({'ok':True, 'data':result})
        except (ManualEvidenceError, PermissionError, LookupError) as exc:
            code = str(exc)
            status = (403 if isinstance(exc, PermissionError) else 404 if isinstance(exc, LookupError)
                      else 503 if 'UNAVAILABLE' in code else 409 if code in {'EVIDENCE_REFERENCED','EVIDENCE_VERSION_CHANGED'} else 400)
            return jsonify({'ok':False,'code':code}), status
        except Exception:
            logger.exception('Manual Evidence owner operation failed')
            return jsonify({'ok':False,'code':'EVIDENCE_OPERATION_UNAVAILABLE'}), 503

    @app.route('/api/app_evidence/stats', methods=['GET'])
    def api_evidence_stats():
        return boundary(lambda actor,scope:get_stats(actor=actor,scope=scope))

    @app.route('/api/app_evidence/list', methods=['GET'])
    def api_evidence_list():
        def read(actor,scope):
            try:
                limit=int(request.args.get('limit',50))
                offset=int(request.args.get('offset',0))
            except ValueError as exc:
                raise ManualEvidenceError('INVALID_EVIDENCE_QUERY') from exc
            return list_evidence(status=request.args.get('status'),topic=request.args.get('topic'),
                source=request.args.get('source'),limit=limit,offset=offset,actor=actor,scope=scope)
        return boundary(read)

    @app.route('/api/app_evidence/<int:record_id>', methods=['GET'])
    def api_evidence_get(record_id):
        def read(actor,scope):
            record=get_evidence(record_id,actor=actor,scope=scope)
            if record is None: raise LookupError('EVIDENCE_NOT_FOUND')
            return record
        return boundary(read)

    @app.route('/api/app_evidence/upload', methods=['POST'])
    def api_evidence_upload():
        # File staging is authorized before any managed-file write. Store creation
        # performs the exact material/resource check and cleans failed uploads.
        def upload(actor,scope):
            _authorize(actor,scope,'write')
            from lumenis.system.security.permission import OperationType
            expected, identity = _authorize(actor,scope,'write')
            resource='/api/app_evidence/upload'
            _effect(actor,scope,OperationType.DB_WRITE,resource)
            fence, attempt=_fenced(resource)
            path=None
            try:
                file=request.files.get('file')
                if file and file.filename:
                    ext=Path(file.filename).suffix.lower()
                    if ext not in EVIDENCE_ALLOWED_EXTENSIONS: raise ManualEvidenceError('EVIDENCE_FILE_TYPE_INVALID')
                    os.makedirs(EVIDENCE_DIR,exist_ok=True)
                    path=str(Path(EVIDENCE_DIR)/('evidence_'+os.urandom(16).hex()+ext))
                    file.save(path)
                    if os.path.getsize(path)>EVIDENCE_MAX_FILE_SIZE_BYTES: raise ManualEvidenceError('EVIDENCE_FILE_TOO_LARGE')
                record,error=create_evidence(source=request.form.get('source','xhs_app'),capture_mode=request.form.get('capture_mode','screenshot'),
                    captured_at=request.form.get('captured_at'),topic=request.form.get('topic'),metric_name=request.form.get('metric_name'),
                    metric_value=request.form.get('metric_value'),notes=request.form.get('notes'),evidence_path=path,actor=actor,scope=scope)
                fence.complete(attempt.idempotency_key,success=True)
                return record
            except BaseException:
                _discard_uncommitted_upload(path)
                fence.complete(attempt.idempotency_key,success=False)
                raise
        return boundary(upload,'write')

    def transition(record_id,status,actor,scope):
        payload=request.get_json(silent=True) or request.form
        record,error=update_evidence_status(record_id,status,actor=actor,scope=scope,reason=payload.get('reason'))
        return record

    @app.route('/api/app_evidence/<int:record_id>/confirm', methods=['POST'])
    def api_evidence_confirm(record_id): return boundary(lambda actor,scope:transition(record_id,STATUS_CONFIRMED,actor,scope),'write')
    @app.route('/api/app_evidence/<int:record_id>/reject', methods=['POST'])
    def api_evidence_reject(record_id): return boundary(lambda actor,scope:transition(record_id,STATUS_REJECTED,actor,scope),'write')
    @app.route('/api/app_evidence/<int:record_id>/shadow', methods=['POST'])
    def api_evidence_shadow(record_id): return boundary(lambda actor,scope:transition(record_id,STATUS_SHADOW,actor,scope),'write')
    @app.route('/api/app_evidence/<int:record_id>/restore', methods=['POST'])
    def api_evidence_restore(record_id): return boundary(lambda actor,scope:transition(record_id,STATUS_PENDING,actor,scope),'write')
    @app.route('/api/app_evidence/<int:record_id>', methods=['DELETE'])
    def api_evidence_delete(record_id): return boundary(lambda actor,scope:transition(record_id,'withdrawn',actor,scope),'write')
    return True
