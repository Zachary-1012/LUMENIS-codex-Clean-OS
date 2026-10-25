"""Single AI Hub conversation owner; conversation retention is not training consent.

Schema installation is exclusively the canonical Shared migration's responsibility.
Ordinary reads/writes must never call ensure_schema or create compatibility tables.
"""
from __future__ import annotations

TURN_MAX_BYTES = 8 * 1024 * 1024
CONVERSATION_MAX_BYTES = 64 * 1024 * 1024
PAGE_MAX_TURNS = 100
SCHEMA_VERSION = 1

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS ai_conversations (
        conversation_id TEXT PRIMARY KEY,
        actor_ref TEXT NOT NULL,
        workspace_binding TEXT NOT NULL CHECK(length(workspace_binding)=64),
        scope_json TEXT NOT NULL CHECK(json_valid(scope_json)),
        title TEXT NOT NULL CHECK(length(title)<=512),
        revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>=1),
        state TEXT NOT NULL DEFAULT 'active' CHECK(state IN ('active','archived')),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS ai_conversation_turns (
        turn_id TEXT PRIMARY KEY,
        conversation_id TEXT NOT NULL REFERENCES ai_conversations(conversation_id),
        idempotency_key TEXT NOT NULL CHECK(length(idempotency_key) BETWEEN 1 AND 128),
        request_sha256 TEXT NOT NULL CHECK(length(request_sha256)=64),
        sequence INTEGER NOT NULL CHECK(sequence>=1),
        role TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
        origin_kind TEXT NOT NULL CHECK(origin_kind IN
            ('user_input','model_output','task_projection','system_status')),
        content_json TEXT NOT NULL CHECK(json_valid(content_json)
            AND length(CAST(content_json AS BLOB))<=8388608),
        task_id TEXT,
        state TEXT NOT NULL CHECK(state IN
            ('recorded','reserved','completed','unavailable','failed','interrupted')),
        revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>=1),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(conversation_id,idempotency_key),
        UNIQUE(conversation_id,sequence),
        CHECK((origin_kind='task_projection' AND task_id IS NOT NULL)
           OR (origin_kind<>'task_projection' AND task_id IS NULL))
    )""",
    "CREATE INDEX IF NOT EXISTS idx_ai_conversation_owner ON ai_conversations(actor_ref,workspace_binding,updated_at,conversation_id)",
    "CREATE INDEX IF NOT EXISTS idx_ai_conversation_task ON ai_conversation_turns(task_id,conversation_id)",
)


def ensure_schema(connection):
    """Migration-only, no commit: preserve the caller's atomic schema transaction."""
    if not connection.in_transaction:
        raise RuntimeError('CONVERSATION_SCHEMA_REQUIRES_MIGRATION_TRANSACTION')
    for statement in SCHEMA:
        connection.execute(statement)
    expected = {
        'ai_conversations': {'conversation_id', 'actor_ref', 'workspace_binding', 'scope_json',
            'title', 'revision', 'state', 'created_at', 'updated_at'},
        'ai_conversation_turns': {'turn_id', 'conversation_id', 'idempotency_key', 'request_sha256',
            'sequence', 'role', 'origin_kind', 'content_json', 'task_id', 'state', 'revision',
            'created_at', 'updated_at'},
    }
    for table, columns in expected.items():
        actual = {row[1] for row in connection.execute('PRAGMA table_info(' + table + ')')}
        if not columns.issubset(actual):
            raise RuntimeError('CONVERSATION_EXISTING_SCHEMA_INCOMPATIBLE')
    primary_keys = {'ai_conversations': 'conversation_id', 'ai_conversation_turns': 'turn_id'}
    for table, identifier in primary_keys.items():
        info = connection.execute('PRAGMA table_info(' + table + ')').fetchall()
        required_nonnull = expected[table] - {identifier, 'task_id'}
        if any(not row[3] for row in info if row[1] in required_nonnull):
            raise RuntimeError('CONVERSATION_EXISTING_NULLABILITY_INCOMPATIBLE')
        if [(row[1], row[5]) for row in info if row[5]] != [(identifier, 1)]:
            raise RuntimeError('CONVERSATION_EXISTING_PRIMARY_KEY_INCOMPATIBLE')
    unique_columns = set()
    for index in connection.execute('PRAGMA index_list(ai_conversation_turns)'):
        if index[2] and not index[4]:
            columns = tuple(row[0] for row in connection.execute(
                'SELECT name FROM pragma_index_info(?) ORDER BY seqno', (index[1],)))
            unique_columns.add(columns)
    if not {('conversation_id','idempotency_key'), ('conversation_id','sequence')}.issubset(unique_columns):
        raise RuntimeError('CONVERSATION_EXISTING_UNIQUENESS_INCOMPATIBLE')
    foreign_keys = connection.execute('PRAGMA foreign_key_list(ai_conversation_turns)').fetchall()
    if not any(row[2]=='ai_conversations' and row[3]=='conversation_id' and row[4]=='conversation_id' for row in foreign_keys):
        raise RuntimeError('CONVERSATION_EXISTING_FOREIGN_KEY_INCOMPATIBLE')
    required_checks = {
        'ai_conversations': ["check(revision>=1)", "check(statein('active','archived'))", "check(json_valid(scope_json))", "check(length(workspace_binding)=64)", "check(length(title)<=512)"],
        'ai_conversation_turns': ["check(sequence>=1)", "check(revision>=1)",
            "check(length(idempotency_key)between1and128)", "check(length(request_sha256)=64)",
            "check((origin_kind='task_projection'andtask_idisnotnull)or(origin_kind<>'task_projection'andtask_idisnull))",
            "check(rolein('user','assistant','system'))",
            "check(origin_kindin('user_input','model_output','task_projection','system_status'))",
            "check(statein('recorded','reserved','completed','unavailable','failed','interrupted'))",
            "check(json_valid(content_json)andlength(cast(content_jsonasblob))<=8388608)"],
    }
    for table, expressions in required_checks.items():
        sql = connection.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()[0]
        normalized = ''.join(sql.lower().split())
        if any(expression not in normalized for expression in expressions):
            raise RuntimeError('CONVERSATION_EXISTING_CHECKS_INCOMPATIBLE')

import hashlib
import json
import re
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

_SCOPE = {'scope_kind': 'shared_workspace', 'version': 1}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _json(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    if len(raw.encode('utf-8')) > TURN_MAX_BYTES:
        raise ValueError('CONVERSATION_TURN_TOO_LARGE')
    return raw


def _sha(value):
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _safe_content(value):
    from agent_runtime.durable_adapter import _CREDENTIAL_VALUE
    raw = _json(value)
    if _CREDENTIAL_VALUE.search(raw) or re.search(
            r'(?i)\b(?:password|api[_ -]?key|access[_ -]?token)["\s]*[:=]["\s]*[^\s,;"}]{4,}', raw):
        raise ValueError('CONVERSATION_CREDENTIAL_INPUT_REJECTED')
    return raw


def current_actor(action='read'):
    from lumenis.auth.service import get_current_user
    from lumenis.system.security.permission import resolve_local_workspace_principal
    actor = get_current_user(read_only=True)
    if not isinstance(actor, dict):
        actor = resolve_local_workspace_principal(module='conversation', action=action)
    if actor is None:
        raise PermissionError('CONVERSATION_IDENTITY_REQUIRED')
    return actor


def _identity(actor, action, connection):
    from lumenis.system.security.permission import authorize_shared_workspace
    from agent_runtime.task_binding import _workspace_binding
    context = authorize_shared_workspace(actor, _SCOPE, module='conversation', action=action, connection=connection)
    ref = ('actor:' + str(context['actor_id']) if 'actor_id' in context else context['principal_ref'])
    return ref, _workspace_binding()


def _authorize(connection, conversation_id, actor, action='read'):
    ref, workspace = _identity(actor, action, connection)
    row = connection.execute('SELECT * FROM ai_conversations WHERE conversation_id=?', (conversation_id,)).fetchone()
    if (not row or row['actor_ref'] != ref or row['workspace_binding'] != workspace
            or json.loads(row['scope_json']) != _SCOPE):
        raise PermissionError('CONVERSATION_ACCESS_DENIED')
    return dict(row)


def _connect():
    from lumenis.shared.database import get_repository
    return get_repository().connect()


def ensure_draft_schema(connection):
    if not connection.in_transaction:
        raise RuntimeError('CONVERSATION_SCHEMA_REQUIRES_MIGRATION_TRANSACTION')
    connection.execute('''CREATE TABLE IF NOT EXISTS ai_workspace_drafts (
        actor_ref TEXT NOT NULL,
        workspace_binding TEXT NOT NULL CHECK(length(workspace_binding)=64),
        scope_key TEXT NOT NULL CHECK(length(scope_key) BETWEEN 1 AND 512),
        text TEXT NOT NULL CHECK(length(text)<=4000),
        revision INTEGER NOT NULL CHECK(revision>=1),
        updated_at TEXT NOT NULL,
        PRIMARY KEY(actor_ref,workspace_binding,scope_key)
    )''')
    info = connection.execute('PRAGMA table_info(ai_workspace_drafts)').fetchall()
    columns = {'actor_ref', 'workspace_binding', 'scope_key', 'text', 'revision', 'updated_at'}
    if ({row[1] for row in info} != columns or any(not row[3] for row in info)
            or [(row[1], row[5]) for row in info if row[5]] != [
                ('actor_ref', 1), ('workspace_binding', 2), ('scope_key', 3)]):
        raise RuntimeError('WORKSPACE_DRAFT_EXISTING_SCHEMA_INCOMPATIBLE')
    sql = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='ai_workspace_drafts'",
    ).fetchone()[0]
    normalized = ''.join(sql.lower().split())
    checks = ['check(length(workspace_binding)=64)', 'check(length(scope_key)between1and512)',
              'check(length(text)<=4000)', 'check(revision>=1)']
    if any(expression not in normalized for expression in checks):
        raise RuntimeError('WORKSPACE_DRAFT_EXISTING_CHECKS_INCOMPATIBLE')


def _draft_scope(value):
    if (type(value) is not str or len(value) > 512
            or not re.fullmatch(r'GLOBAL_ALL::|FOCUS:(?:CTH|BMP):[^\x00-\x20:]{1,240}', value)):
        raise ValueError('WORKSPACE_DRAFT_SCOPE_INVALID')
    return value


def workspace_draft(actor, *, scope_key, text=None, expected_revision=None):
    scope_key = _draft_scope(scope_key)
    writing = text is not None
    if writing:
        if type(text) is not str or len(text) > 4000 or type(expected_revision) is not int or expected_revision < 0:
            raise ValueError('WORKSPACE_DRAFT_INVALID')
        _safe_content(text)
    con = _connect()
    try:
        if writing:
            con.execute('BEGIN IMMEDIATE')
        ref, workspace = _identity(actor, 'write' if writing else 'read', con)
        key = (ref, workspace, scope_key)
        row = con.execute('''SELECT text,revision,updated_at FROM ai_workspace_drafts
            WHERE actor_ref=? AND workspace_binding=? AND scope_key=?''', key).fetchone()
        current = dict(row) if row else {'text': '', 'revision': 0, 'updated_at': None}
        if writing:
            if expected_revision != current['revision']:
                if text != current['text']:
                    raise RuntimeError('WORKSPACE_DRAFT_REVISION_CONFLICT')
            elif text != current['text'] or row is None:
                current = {'text': text, 'revision': current['revision'] + 1, 'updated_at': _now()}
                con.execute('''INSERT INTO ai_workspace_drafts
                    (actor_ref,workspace_binding,scope_key,text,revision,updated_at) VALUES (?,?,?,?,?,?)
                    ON CONFLICT(actor_ref,workspace_binding,scope_key) DO UPDATE SET
                    text=excluded.text,revision=excluded.revision,updated_at=excluded.updated_at''',
                    (*key, current['text'], current['revision'], current['updated_at']))
            _identity(actor, 'write', con)
            con.commit()
        return {'draft': {**current, 'scope_key': scope_key}}
    except BaseException:
        if writing:
            con.rollback()
        raise
    finally:
        con.close()


@contextmanager
def _write(conversation_id, actor):
    connection = _connect()
    try:
        connection.execute('BEGIN IMMEDIATE')
        row = _authorize(connection, conversation_id, actor, 'write')
        yield connection, row
        _authorize(connection, conversation_id, actor, 'write')
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def _advance(connection, row, revision):
    if type(revision) is not int or revision != row['revision']:
        raise RuntimeError('CONVERSATION_REVISION_CONFLICT')
    if row['state'] != 'active':
        raise RuntimeError('CONVERSATION_ARCHIVED')
    changed = connection.execute('UPDATE ai_conversations SET revision=revision+1,updated_at=? WHERE conversation_id=? AND revision=?',
        (_now(), row['conversation_id'], revision)).rowcount
    if changed != 1:
        raise RuntimeError('CONVERSATION_REVISION_CONFLICT')


def _key(key):
    if type(key) is not str or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', key):
        raise ValueError('CONVERSATION_IDEMPOTENCY_KEY_INVALID')
    return key


def _existing(connection, conversation_id, key, digest):
    row = connection.execute('SELECT * FROM ai_conversation_turns WHERE conversation_id=? AND idempotency_key=?',
        (conversation_id, _key(key))).fetchone()
    if row and row['request_sha256'] != digest:
        raise RuntimeError('CONVERSATION_IDEMPOTENCY_CONFLICT')
    return dict(row) if row else None


def _insert_turn(connection, conversation, *, key, digest, role, origin, content, state, task_id=None):
    raw = _safe_content(content)
    size = connection.execute('SELECT COALESCE(SUM(length(CAST(content_json AS BLOB))),0) FROM ai_conversation_turns WHERE conversation_id=?',
        (conversation['conversation_id'],)).fetchone()[0]
    if size + len(raw.encode()) > CONVERSATION_MAX_BYTES:
        raise ValueError('CONVERSATION_STORAGE_LIMIT_REACHED')
    sequence = connection.execute('SELECT COALESCE(MAX(sequence),0)+1 FROM ai_conversation_turns WHERE conversation_id=?',
        (conversation['conversation_id'],)).fetchone()[0]
    now = _now(); identifier = 'turn_' + uuid.uuid4().hex
    connection.execute('''INSERT INTO ai_conversation_turns
        (turn_id,conversation_id,idempotency_key,request_sha256,sequence,role,origin_kind,content_json,task_id,state,revision,created_at,updated_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,1,?,?)''', (identifier, conversation['conversation_id'], key, digest, sequence,
        role, origin, raw, task_id, state, now, now))
    return dict(connection.execute('SELECT * FROM ai_conversation_turns WHERE turn_id=?', (identifier,)).fetchone())


def _task_projection(task_id):
    from ai_api import _get_engine, _task_row_read_allowed, _task_notification
    task = _get_engine().get_task(task_id)
    kind = 'TASK_ENGINE'
    if task is None:
        from lumenis.shared.agents.skills.execution import query_executions
        rows = query_executions(execution_id=task_id, limit=1, strict=True)
        task = rows[0] if rows else None
        kind = 'SKILL_EXECUTION'
    if not task or not _task_row_read_allowed(task, kind=kind):
        raise PermissionError('CONVERSATION_TASK_ACCESS_DENIED')
    return {'task_id': task_id, 'task_kind': kind, 'status': task['status'],
            'notification': _task_notification(task, kind),
            'result_ref': '/api/ai/tasks/' + task_id, 'truth_kind': 'task_derived_reference'}


def _public_turn(row):
    result = {key: row[key] for key in ('turn_id','conversation_id','sequence','role','origin_kind','state','revision','created_at','updated_at')}
    if row['origin_kind'] == 'task_projection':
        try:
            result['content'] = _task_projection(row['task_id'])
        except PermissionError:
            result['content'] = {'state': 'source_access_unavailable'}
    else:
        result['content'] = json.loads(row['content_json'])
    if row['state'] == 'reserved':
        result['recovery'] = 'RESULT_UNKNOWN_NO_AUTOMATIC_RETRY'
    result['training_admission'] = 'NOT_GRANTED'
    return result


def create_conversation(actor, *, title=''):
    if type(title) is not str or len(title) > 512:
        raise ValueError('CONVERSATION_TITLE_INVALID')
    _safe_content({'text': title})
    con = _connect()
    try:
        con.execute('BEGIN IMMEDIATE')
        ref, workspace = _identity(actor, 'write', con)
        identifier = 'conv_' + uuid.uuid4().hex; now = _now()
        con.execute('''INSERT INTO ai_conversations(conversation_id,actor_ref,workspace_binding,scope_json,title,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?)''', (identifier, ref, workspace, _json(_SCOPE), title, now, now))
        row = _authorize(con, identifier, actor, 'write')
        con.commit()
        return {key: row[key] for key in ('conversation_id','title','revision','state','created_at','updated_at')}
    except BaseException:
        con.rollback(); raise
    finally:
        con.close()


def list_conversations(actor, *, limit=30, offset=0):
    if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or offset < 0:
        raise ValueError('CONVERSATION_PAGINATION_INVALID')
    con = _connect()
    try:
        ref, workspace = _identity(actor, 'read', con)
        rows = con.execute('''SELECT conversation_id,title,revision,state,created_at,updated_at FROM ai_conversations
            WHERE actor_ref=? AND workspace_binding=? ORDER BY updated_at DESC,conversation_id LIMIT ? OFFSET ?''',
            (ref, workspace, limit+1, offset)).fetchall()
        _identity(actor, 'read', con)
        return {'conversations': [dict(row) for row in rows[:limit]], 'has_more': len(rows)>limit,
                'next_offset': offset+limit if len(rows)>limit else None}
    finally:
        con.close()


def read_conversation(actor, conversation_id, *, after_sequence=0, limit=30):
    if type(limit) is not int or not 1 <= limit <= PAGE_MAX_TURNS or type(after_sequence) is not int or after_sequence < 0:
        raise ValueError('CONVERSATION_PAGINATION_INVALID')
    con = _connect()
    try:
        row = _authorize(con, conversation_id, actor)
        turns = con.execute('SELECT * FROM ai_conversation_turns WHERE conversation_id=? AND sequence>? ORDER BY sequence LIMIT ?',
            (conversation_id, after_sequence, limit+1)).fetchall()
        _authorize(con, conversation_id, actor)
        result = {key: row[key] for key in ('conversation_id','title','revision','state','created_at','updated_at')}
        page, page_bytes = [], 0
        for turn in turns[:limit]:
            size = len(turn['content_json'].encode())
            if page and page_bytes + size > TURN_MAX_BYTES:
                break
            page.append(turn); page_bytes += size
        more = len(turns) > len(page)
        result.update(turns=[_public_turn(dict(turn)) for turn in page], has_more=more,
            next_sequence=page[-1]['sequence'] if more else None,
            storage={'turn_max_bytes': TURN_MAX_BYTES, 'conversation_max_bytes': CONVERSATION_MAX_BYTES,
                     'credential_handling': 'REJECT_RECOGNIZABLE_CREDENTIALS', 'training_admission': 'NOT_GRANTED'})
        return result
    finally:
        con.close()


def append_user_turn(actor, conversation_id, *, text, idempotency_key, expected_revision):
    if type(text) is not str or not text.strip():
        raise ValueError('CONVERSATION_MESSAGE_REQUIRED')
    content = {'text': text, 'source_kind': 'user_authored'}
    digest = _sha(content)
    with _write(conversation_id, actor) as (con, row):
        old = _existing(con, conversation_id, idempotency_key, digest)
        if old:
            return {'turn': _public_turn(old), 'revision': row['revision'], 'idempotent_hit': True}
        _advance(con, row, expected_revision)
        made = _insert_turn(con, row, key=idempotency_key, digest=digest, role='user', origin='user_input', content=content, state='recorded')
        return {'turn': _public_turn(made), 'revision': row['revision']+1, 'idempotent_hit': False}


def attach_task(actor, conversation_id, *, task_id, idempotency_key, expected_revision):
    if type(task_id) is not str:
        raise ValueError('CONVERSATION_TASK_REQUIRED')
    projection = _task_projection(task_id)
    digest = _sha({'task_id': task_id, 'owner': projection['task_kind']})
    with _write(conversation_id, actor) as (con, row):
        _task_projection(task_id)
        old = _existing(con, conversation_id, idempotency_key, digest)
        if old:
            return {'turn': _public_turn(old), 'revision': row['revision'], 'idempotent_hit': True}
        _advance(con, row, expected_revision)
        made = _insert_turn(con, row, key=idempotency_key, digest=digest, role='assistant', origin='task_projection',
            content={'owner': projection['task_kind'], 'source_policy': 'TASK_OWNER_RECHECK_ON_READ'}, state='recorded', task_id=task_id)
        _task_projection(task_id)
        return {'turn': _public_turn(made), 'revision': row['revision']+1, 'idempotent_hit': False}


def task_conversation_refs(actor, task_id):
    _task_projection(task_id)
    con = _connect()
    try:
        ref, workspace = _identity(actor, 'read', con)
        rows = con.execute('''SELECT t.conversation_id,t.turn_id,t.sequence FROM ai_conversation_turns t
            JOIN ai_conversations c ON c.conversation_id=t.conversation_id
            WHERE t.task_id=? AND c.actor_ref=? AND c.workspace_binding=? ORDER BY t.created_at,t.turn_id''',
            (task_id, ref, workspace)).fetchall()
        _identity(actor, 'read', con)
        return [{**dict(row), 'return_ref': '/v4/ai/conversations/' + row['conversation_id']} for row in rows]
    finally:
        con.close()


def update_conversation(actor, conversation_id, *, expected_revision, title=None, state=None):
    if title is not None and (type(title) is not str or len(title)>512):
        raise ValueError('CONVERSATION_TITLE_INVALID')
    if state is not None and state not in ('active','archived'):
        raise ValueError('CONVERSATION_STATE_INVALID')
    if title is not None:
        _safe_content({'text': title})
    with _write(conversation_id, actor) as (con, row):
        if type(expected_revision) is not int or expected_revision != row['revision']:
            raise RuntimeError('CONVERSATION_REVISION_CONFLICT')
        con.execute('UPDATE ai_conversations SET title=?,state=?,revision=revision+1,updated_at=? WHERE conversation_id=? AND revision=?',
            (row['title'] if title is None else title, row['state'] if state is None else state,
             _now(), conversation_id, expected_revision))
    return read_conversation(actor, conversation_id)


def update_context(actor, conversation_id, *, value, idempotency_key, expected_revision, source_references=None):
    """Save an explicit human correction; retain every original conversation turn.

    Source bodies and executed effects cannot be authored here. References
    reopen their original owner and grant no model use. Forgetting excludes user
    text from future model context; it does not delete the original transcript.
    """
    from .context_pack import validate_state
    value = validate_state(value)
    content = {'schema': 'conversation-human-context/v1', 'value': value,
               'truth_kind': 'user_authored', 'source_policy': 'source_free_conversation'}
    if source_references is not None:
        if type(source_references) is not list or len(source_references) > 100:
            raise ValueError('CONVERSATION_SOURCE_REFERENCES_INVALID')
        content['source_references'] = source_references
    digest = _sha(content)
    with _write(conversation_id, actor) as (con, row):
        old = _existing(con, conversation_id, idempotency_key, digest)
        if old:
            return {'turn': _public_turn(old), 'revision': row['revision'], 'idempotent_hit': True}
        if source_references is None:
            latest = con.execute("SELECT content_json FROM ai_conversation_turns WHERE conversation_id=? "
                "AND origin_kind='system_status' AND state='recorded' "
                "AND json_extract(content_json,'$.schema')='conversation-human-context/v1' "
                "ORDER BY sequence DESC LIMIT 1", (conversation_id,)).fetchone()
            references = json.loads(latest[0]).get('source_references', []) if latest else []
        else:
            from agent_memory.semantic import read_source_reference
            references = json.loads(_json(source_references))
            if len({_sha(reference) for reference in references}) != len(references):
                raise ValueError('CONVERSATION_SOURCE_REFERENCES_INVALID')
            for reference in references:
                read_source_reference(reference, actor=actor, scope=_SCOPE, connection=con)
        if references or source_references is not None:
            content['source_references_schema'] = 'conversation-source-references/v1'
            content['source_references'] = references
        for identity in value['excluded_turn_ids']:
            source = con.execute('SELECT origin_kind FROM ai_conversation_turns WHERE conversation_id=? AND turn_id=?',
                                 (conversation_id, identity)).fetchone()
            if source is None or source['origin_kind'] != 'user_input':
                raise ValueError('CONVERSATION_CONTEXT_EXCLUSION_USER_TURN_REQUIRED')
        _advance(con, row, expected_revision)
        made = _insert_turn(con, row, key=idempotency_key, digest=digest, role='user', origin='system_status',
                            content=content, state='recorded')
        if source_references is not None:
            for reference in references:
                read_source_reference(reference, actor=actor, scope=_SCOPE, connection=con)
        return {'turn': _public_turn(made), 'revision': row['revision'] + 1, 'idempotent_hit': False}


def read_context(actor, conversation_id, *, query=None, limit=30, offset=0, expected_snapshot=None, source_reference=None):
    """Reopen current human context with the same actor/workspace read gate."""
    con = _connect()
    try:
        row = _authorize(con, conversation_id, actor)
        latest = con.execute("SELECT * FROM ai_conversation_turns WHERE conversation_id=? AND origin_kind='system_status' "
            "AND state='recorded' AND json_extract(content_json,'$.schema')='conversation-human-context/v1' "
            "ORDER BY sequence DESC LIMIT 1", (conversation_id,)).fetchone()
        result = {'conversation_id': conversation_id, 'revision': row['revision'],
                'context': _public_turn(dict(latest)) if latest else None,
                'training_admission': 'NOT_GRANTED', 'effect_permission': 'NOT_GRANTED',
                'source_references_schema': 'conversation-source-references/v1', 'source_references': []}
        from agent_memory.semantic import (
            read_source_reference,
            search_authorized_sources,
        )
        references = json.loads(latest['content_json']).get('source_references', []) if latest else []
        for reference in references:
            try:
                projected = read_source_reference(reference, actor=actor, scope=_SCOPE, connection=con)
            except (ValueError, PermissionError, RuntimeError):
                projected = {'reference': reference, 'state': 'source_access_unavailable',
                             'model_source_use': 'NOT_GRANTED', 'training_admission': 'NOT_GRANTED'}
            result['source_references'].append(projected)
        if query is not None:
            result['search'] = search_authorized_sources(query, actor=actor, scope=_SCOPE, connection=con,
                limit=limit, offset=offset, expected_snapshot=expected_snapshot)
        if source_reference is not None:
            result['source_preview'] = read_source_reference(source_reference, actor=actor, scope=_SCOPE, connection=con)
        # Searching may be slow: a source projected before that work must still
        # be readable when the response leaves its conversation owner.
        for index, projected in enumerate(result['source_references']):
            if projected['state'] != 'available':
                continue
            try:
                result['source_references'][index] = read_source_reference(projected['reference'],
                    actor=actor, scope=_SCOPE, connection=con)
            except (ValueError, PermissionError, RuntimeError):
                result['source_references'][index] = {'reference': projected['reference'],
                    'state': 'source_access_unavailable', 'model_source_use': 'NOT_GRANTED',
                    'training_admission': 'NOT_GRANTED'}
        _authorize(con, conversation_id, actor)
        return result
    finally:
        con.close()


def _response_context(connection, conversation_id, user_turn_id):
    target = connection.execute('SELECT * FROM ai_conversation_turns WHERE conversation_id=? AND turn_id=?',
        (conversation_id, user_turn_id)).fetchone()
    if not target or target['origin_kind'] != 'user_input' or target['state'] != 'recorded':
        raise ValueError('CONVERSATION_RESPONSE_USER_TURN_REQUIRED')
    if connection.execute("""SELECT 1 FROM ai_conversation_turns WHERE conversation_id=? AND sequence<?
            AND (origin_kind='task_projection' OR (origin_kind='model_output' AND state='completed'
            AND COALESCE(json_extract(content_json,'$.source_policy'),'')<>'source_free_conversation')) LIMIT 1""",
            (conversation_id, target['sequence'])).fetchone():
        raise PermissionError('CONVERSATION_HISTORY_TYPED_SOURCE_USE_REQUIRED')
    predicate = "conversation_id=? AND sequence<? AND (origin_kind='user_input' OR (origin_kind='model_output' AND state='completed'))"
    params = (conversation_id, target['sequence'])
    chosen = [dict(row) for row in connection.execute('SELECT * FROM ai_conversation_turns WHERE ' +
        predicate + ' ORDER BY sequence', params)]
    latest = connection.execute("SELECT * FROM ai_conversation_turns WHERE conversation_id=? AND origin_kind='system_status' "
        "AND state='recorded' AND json_extract(content_json,'$.schema')='conversation-human-context/v1' "
        "ORDER BY sequence DESC LIMIT 1", (conversation_id,)).fetchone()
    latest = dict(latest) if latest else None
    for row in chosen:
        row['content'] = json.loads(row['content_json'])
    if latest:
        latest['content'] = json.loads(latest['content_json'])
        if user_turn_id in latest['content']['value']['excluded_turn_ids']:
            raise ValueError('CONVERSATION_RESPONSE_INPUT_EXCLUDED')
    from .context_pack import conversation_pack
    history, accounting = conversation_pack(chosen, context_turn=latest)
    return json.loads(target['content_json'])['text'], history, accounting


def task_working_context(connection, conversation_id, actor):
    """Reopen original conversation input for an explicitly linked Task.

    Task projections and source-bearing responses are references, not permission
    to read or send their bodies to a model. Keep the full source-free transcript
    and latest human correction, including the exclusion/dependency ledger.
    """
    from .context_pack import conversation_pack
    row = _authorize(connection, conversation_id, actor)
    turns = connection.execute('SELECT * FROM ai_conversation_turns WHERE conversation_id=? ORDER BY sequence',
                               (conversation_id,)).fetchall()
    chosen, omitted, latest = [], [], None
    for turn in turns:
        content = json.loads(turn['content_json'])
        if (turn['origin_kind'] == 'system_status' and turn['state'] == 'recorded'
                and content.get('schema') == 'conversation-human-context/v1'):
            latest = {**dict(turn), 'content': content}
        elif (turn['origin_kind'] == 'user_input' and turn['state'] == 'recorded'
                or turn['origin_kind'] == 'model_output' and turn['state'] == 'completed'
                and content.get('source_policy') == 'source_free_conversation'):
            chosen.append({**dict(turn), 'content': content})
        else:
            omitted.append({'turn_id': turn['turn_id'], 'revision': turn['revision'],
                'origin_kind': turn['origin_kind'], 'state': turn['state'],
                'reason': 'source_use_not_granted' if turn['origin_kind'] == 'task_projection'
                          or turn['state'] == 'completed' else 'not_completed_source_free_text'})
    history, accounting = conversation_pack(chosen, context_turn=latest)
    _authorize(connection, conversation_id, actor)
    return {'conversation_id': row['conversation_id'], 'state': row['state'],
            'context_turn_id': latest['turn_id'] if latest else None,
            'context_revision': latest['revision'] if latest else None,
            'human_state': latest['content']['value'] if latest else None,
            'history': history, 'context_accounting': accounting,
            'omitted_reference_turns': omitted,
            'source_policy': 'source_free_conversation', 'permission_grant': False}


def conversation_source_use_policy():
    descriptor = {'version': 'conversation-user-context/v1', 'operation': 'source_free_conversation',
        'scope': 'shared_workspace:v1', 'input': 'original_user_turns_and_explicit_human_state',
        'history': 'completed_source_free_outputs_with_exclusion_lineage',
        'external_sources': 'NOT_READ', 'task_source_permission': 'NOT_GRANTED',
        'effects': 'NOT_GRANTED', 'training': 'NOT_GRANTED', 'max_output_tokens': 1200}
    return {**descriptor, 'sha256': _sha(descriptor)}


def _conversation_owned_material(actor, conversation_id, response_turn_id):
    """Reopen the original owner's pending response; no Task or Source bodies."""
    con = _connect()
    try:
        conversation = _authorize(con, conversation_id, actor, 'write')
        turn = con.execute('SELECT * FROM ai_conversation_turns WHERE conversation_id=? AND turn_id=?',
                           (conversation_id, response_turn_id)).fetchone()
        if (conversation['state'] != 'active' or not turn or turn['origin_kind'] != 'model_output'
                or turn['state'] != 'reserved' or turn['revision'] != 1):
            raise PermissionError('CONVERSATION_RESPONSE_NOT_PENDING')
        content = json.loads(turn['content_json'])
        if content.get('source_policy') != 'source_free_conversation':
            raise PermissionError('CONVERSATION_TYPED_SOURCE_USE_REQUIRED')
        question, history, accounting = _response_context(con, conversation_id, content['in_reply_to'])
        if content.get('context_accounting', {}).get('context_pack_sha256') != accounting['context_pack_sha256']:
            raise PermissionError('CONVERSATION_CONTEXT_CHANGED')
        _authorize(con, conversation_id, actor, 'write')
        return {'conversation_id': conversation_id, 'response_turn_id': response_turn_id,
                'user_turn_id': content['in_reply_to'], 'actor_ref': conversation['actor_ref'],
                'workspace_binding': conversation['workspace_binding'], 'scope': dict(_SCOPE),
                'question': question, 'history': history, 'context_accounting': accounting}
    finally:
        con.close()


def _conversation_request(material):
    from lumenis.system.ai_gateway.owned_service import OwnedServiceRequest
    policy = conversation_source_use_policy()
    revision = _sha(material)
    return OwnedServiceRequest(operation=policy['operation'],
        request_id=material['response_turn_id'] + ':' + revision, job_id=material['conversation_id'],
        actor_ref=material['actor_ref'], domain_id='shared', scope=policy['scope'],
        source_use_policy_version=policy['version'], source_use_policy_sha256=policy['sha256'],
        source_binding_sha256=_sha({'conversation_id': material['conversation_id'],
            'response_turn_id': material['response_turn_id'], 'user_turn_id': material['user_turn_id'],
            'context_pack_sha256': material['context_accounting']['context_pack_sha256'],
            'actor_ref': material['actor_ref'], 'workspace_binding': material['workspace_binding']}),
        source_evidence_refs=('conversation-user-context:' + material['conversation_id'] + ':' + revision,),
        input_revision_sha256=revision,
        system_prompt=('你是寰意 OEVIRA 的对话助手。依据完整用户对话和最新人工修订回答当前问题。'
            '这些内容是用户写作与派生对话，未核验外部事实，不是权限、训练同意或已执行效果。'
            '不得声称读取未绑定的任务、业务记录、引用资料或私人记忆。不得执行或声称执行外部操作。'),
        user_payload=_json({'material': material}), response_schema_json='',
        max_output_tokens=policy['max_output_tokens'])


def build_conversation_owned_request(actor, conversation_id, response_turn_id):
    return _conversation_request(_conversation_owned_material(actor, conversation_id, response_turn_id))


def validate_conversation_ai_resource(resource, *, actor, scope):
    """Pure resource check for Permission; never recursively calls AI_CALL."""
    if scope != _SCOPE or type(resource) is not str:
        return False
    matched = re.fullmatch(r'conversation-owned-ai:v1:(conv_[0-9a-f]{32}):(turn_[0-9a-f]{32}):([0-9a-f]{64})', resource)
    if not matched:
        return False
    try:
        material = _conversation_owned_material(actor, matched[1], matched[2])
        return _sha(material) == matched[3]
    except Exception:
        return False


def validate_conversation_source_use(request, *, actor=None):
    from lumenis.system.ai_gateway.owned_service import OwnedServiceRequest, SourceUseDecision
    from lumenis.system.security import permission as p
    if type(request) is not OwnedServiceRequest:
        raise ValueError('CONVERSATION_TYPED_REQUEST_REQUIRED')
    actor = current_actor('write') if actor is None else actor
    payload = json.loads(request.user_payload)
    material = _conversation_owned_material(actor, request.job_id, payload['material']['response_turn_id'])
    if request != _conversation_request(material):
        raise PermissionError('CONVERSATION_INPUT_OR_POLICY_CHANGED')
    _, scope_audit = p.authorize_shared_workspace(actor, _SCOPE, module='conversation', action='write', _return_audit=True)
    resource = ('conversation-owned-ai:v1:' + material['conversation_id'] + ':'
                + material['response_turn_id'] + ':' + request.input_revision_sha256)
    effect = p.check_shared_workspace_effect(actor, _SCOPE, p.OperationType.AI_CALL, resource,
                                            module='conversation', action='write')
    if p.is_testing_bypass_enabled() or not effect.allowed or not effect.audit_id:
        raise PermissionError('CONVERSATION_AI_PERMISSION_DENIED')
    if request != build_conversation_owned_request(actor, material['conversation_id'], material['response_turn_id']):
        raise PermissionError('CONVERSATION_INPUT_CHANGED_DURING_PERMISSION')
    return SourceUseDecision(True, 'USER_AUTHORED_CONVERSATION_VERIFIED', request.actor_ref,
        request.domain_id, request.scope, request.source_use_policy_version, request.source_use_policy_sha256,
        request.source_binding_sha256, request.source_evidence_refs, scope_audit, effect.audit_id)


def respond(actor, conversation_id, user_turn_id, *, idempotency_key, expected_revision, retry_confirmed=False, external_approval=None):
    """Reserve before inference. Unknown prior effects are never auto-retried."""
    if external_approval is not None and (
            type(external_approval) is not dict
            or set(external_approval) != {'confirmed', 'confirmation_id', 'resource'}
            or external_approval.get('confirmed') is not True
            or any(type(external_approval.get(k)) is not str or not external_approval[k]
                   or len(external_approval[k]) > 256 for k in ('confirmation_id', 'resource'))):
        raise ValueError('CONVERSATION_EXTERNAL_APPROVAL_INVALID')
    request_binding = {'user_turn_id': user_turn_id, 'operation': 'explicit_model_response'}
    if external_approval is not None:
        # Idempotent replay cannot change consent or reuse a preview request key.
        request_binding['external_approval_sha256'] = _sha(external_approval)
    digest = _sha(request_binding)
    with _write(conversation_id, actor) as (con, conversation):
        old = _existing(con, conversation_id, idempotency_key, digest)
        if old:
            return {'turn': _public_turn(old), 'revision': conversation['revision'], 'idempotent_hit': True}
        previous = con.execute("SELECT content_json,state FROM ai_conversation_turns WHERE conversation_id=? AND origin_kind='model_output'",
            (conversation_id,)).fetchall()
        previous = [row for row in previous if json.loads(row['content_json']).get('in_reply_to') == user_turn_id]
        if any(row['state'] == 'reserved' for row in previous):
            raise RuntimeError('CONVERSATION_RESPONSE_PENDING_NO_RETRY')
        if previous and retry_confirmed is not True:
            raise ValueError('CONVERSATION_NEW_MODEL_ATTEMPT_REQUIRES_CONFIRMATION')
        question, history, accounting = _response_context(con, conversation_id, user_turn_id)
        context_digest = _sha({'question': question, 'history': history})
        if external_approval is not None:
            binding = {'confirmation_sha256': _sha(external_approval['confirmation_id']),
                       'resource': external_approval['resource'], 'context_sha256': context_digest}
            if not any(json.loads(row['content_json']).get('approval_binding') == binding
                       and row['state'] == 'unavailable' for row in previous):
                raise PermissionError('CONVERSATION_EXTERNAL_APPROVAL_NOT_BOUND')
        _advance(con, conversation, expected_revision)
        reserved = _insert_turn(con, conversation, key=idempotency_key, digest=digest,
            role='assistant', origin='model_output', state='reserved', content={
                'in_reply_to': user_turn_id, 'source_policy': 'source_free_conversation',
                'context_accounting': accounting, 'recovery': 'NO_AUTOMATIC_MODEL_RETRY'})
    # The existing unique Gateway service owns model selection and authorization.
    # No transaction/SQLite writer lock is held over an external call.
    from . import service
    approval_request = None
    try:
        kwargs = {'history': history, 'source_scope': None}
        if external_approval is not None:
            kwargs['external_approval'] = external_approval
        else:
            from lumenis.system.ai_gateway import user_api_adapter
            if not user_api_adapter.is_selected():
                owned_request = build_conversation_owned_request(actor, conversation_id, reserved['turn_id'])
                resource = ('conversation-owned-ai:v1:' + conversation_id + ':' + reserved['turn_id']
                            + ':' + owned_request.input_revision_sha256)
                kwargs['_owned_request'] = owned_request
                kwargs['is_cancelled'] = lambda: not validate_conversation_ai_resource(resource, actor=actor, scope=_SCOPE)
        outcome = service.chat(question, **kwargs)
        if type(outcome.get('context_accounting')) is dict:
            accounting = {**accounting, 'transport': outcome['context_accounting']}
        if type(outcome.get('model_budget')) is dict:
            accounting = {**accounting, 'model_budget': outcome['model_budget']}
            measured = outcome['model_budget'].get('measurement', {})
            if measured.get('ok') is True and measured.get('fits') is True:
                accounting['token_budget_verified'] = True
                accounting['token_count_status'] = 'ADMITTED_RUNTIME_TOKENIZER'
        if outcome.get('ok') is True and isinstance(outcome.get('reply'), str) and outcome['reply'].strip():
            content = {'text': outcome['reply'], 'in_reply_to': user_turn_id,
                'source_policy': 'source_free_conversation', 'context_accounting': accounting,
                'provider': outcome.get('provider'), 'model': outcome.get('model')}
            if type(outcome.get('owned_provenance')) is dict:
                content['owned_provenance'] = outcome['owned_provenance']
            _safe_content(content)
            state = 'completed'
        else:
            code = outcome.get('code')
            content = {'in_reply_to': user_turn_id, 'source_policy': 'source_free_conversation',
                'context_accounting': accounting, 'code': code if type(code) is str and re.fullmatch(r'[A-Z0-9_]{1,96}', code) else 'MODEL_UNAVAILABLE'}
            state = 'unavailable'
            preview = outcome.get('approval_request')
            if (code == 'USER_API_APPROVAL_REQUIRED' and external_approval is None
                    and type(preview) is dict and type(preview.get('confirmation_id')) is str
                    and type(preview.get('resource')) is str):
                # Preserve only non-authorizing hashes in conversation storage.
                # The live preview is returned once; replay never issues consent.
                content['approval_binding'] = {
                    'confirmation_sha256': _sha(preview['confirmation_id']),
                    'resource': preview['resource'], 'context_sha256': context_digest}
                content['recovery'] = 'NEW_ATTEMPT_WITH_EXACT_APPROVAL_AND_RETRY_CONFIRMATION'
                approval_request = preview
    except Exception:
        content = {'in_reply_to': user_turn_id, 'source_policy': 'source_free_conversation',
            'context_accounting': accounting, 'code': 'MODEL_RESULT_UNAVAILABLE_NO_AUTO_RETRY'}
        state = 'failed'
    raw = _safe_content(content)
    with _write(conversation_id, actor) as (con, current):
        if current['state'] != 'active':
            raise RuntimeError('CONVERSATION_RESPONSE_INTERRUPTED')
        # Authorization, membership and revision are checked again after inference.
        try:
            _, _, current_accounting = _response_context(con, conversation_id, user_turn_id)
            context_changed = current_accounting['context_pack_sha256'] != accounting['context_pack_sha256']
        except ValueError as exc:
            if str(exc) != 'CONVERSATION_RESPONSE_INPUT_EXCLUDED':
                raise
            context_changed = True
        if context_changed:
            content = {'in_reply_to': user_turn_id, 'source_policy': 'source_free_conversation',
                       'context_accounting': accounting, 'code': 'CONVERSATION_CONTEXT_CHANGED_NO_RESULT_ADOPTED',
                       'recovery': 'REVIEW_CURRENT_CONTEXT_AND_CONFIRM_NEW_ATTEMPT'}
            raw = _safe_content(content)
            state = 'interrupted'
            approval_request = None
        size = con.execute('SELECT COALESCE(SUM(length(CAST(content_json AS BLOB))),0) FROM ai_conversation_turns WHERE conversation_id=? AND turn_id<>?',
            (conversation_id, reserved['turn_id'])).fetchone()[0]
        if size + len(raw.encode()) > CONVERSATION_MAX_BYTES:
            raise ValueError('CONVERSATION_STORAGE_LIMIT_REACHED')
        changed = con.execute("UPDATE ai_conversation_turns SET content_json=?,state=?,revision=revision+1,updated_at=? WHERE turn_id=? AND state='reserved' AND revision=1",
            (raw, state, _now(), reserved['turn_id'])).rowcount
        if changed != 1:
            raise RuntimeError('CONVERSATION_RESPONSE_INTERRUPTED')
        _advance(con, current, current['revision'])
        made = dict(con.execute('SELECT * FROM ai_conversation_turns WHERE turn_id=?', (reserved['turn_id'],)).fetchone())
        result = {'turn': _public_turn(made), 'revision': current['revision']+1, 'idempotent_hit': False}
        if approval_request is not None:
            result['approval_request'] = approval_request
        return result


def interrupt_response(actor, conversation_id, turn_id, *, expected_revision, confirmed):
    """User acknowledges an unknown result; never claims an external call stopped."""
    if confirmed is not True:
        raise ValueError('CONVERSATION_INTERRUPTION_CONFIRMATION_REQUIRED')
    with _write(conversation_id, actor) as (con, row):
        current = con.execute('SELECT * FROM ai_conversation_turns WHERE conversation_id=? AND turn_id=?',
            (conversation_id, turn_id)).fetchone()
        if not current or current['origin_kind'] != 'model_output':
            raise ValueError('CONVERSATION_MODEL_TURN_REQUIRED')
        if current['state'] == 'interrupted':
            return {'turn': _public_turn(dict(current)), 'revision': row['revision'], 'idempotent_hit': True}
        if current['state'] != 'reserved':
            raise RuntimeError('CONVERSATION_RESPONSE_NOT_PENDING')
        _advance(con, row, expected_revision)
        con.execute("UPDATE ai_conversation_turns SET state='interrupted',revision=revision+1,updated_at=? WHERE turn_id=? AND state='reserved'",
            (_now(), turn_id))
        result = dict(con.execute('SELECT * FROM ai_conversation_turns WHERE turn_id=?', (turn_id,)).fetchone())
        return {'turn': _public_turn(result), 'revision': row['revision']+1,
                'external_call_stopped': False, 'prior_result_unknown': True}
