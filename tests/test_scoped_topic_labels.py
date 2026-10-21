"""Synthetic regressions for derived labels on the authorized graph-list boundary."""
from copy import deepcopy

import pytest
from flask import Flask


@pytest.fixture
def graph_list(monkeypatch):
    import event_graph as graph
    import experience_runtime as runtime

    actor, scope = object(), object()
    rows = [
        {'event_id': 'allowed', 'event_type': 'marketing_event',
         'title': 'Solar launch campaign', 'description': 'DESCRIPTION SECRET',
         'summary': 'UNVERIFIED SUMMARY', 'claim_type': 'user_statement',
         'source_ref': {'version': 'v1'}, 'count': 0, 'verified': False},
        {'event_id': 'other-type', 'event_type': 'propagation_event',
         'title': 'Excluded filter title'},
    ]
    result = {'events': rows, 'relations': [{'source_event_id': 'allowed',
              'target_event_id': 'other-type', 'claim_type': 'user_statement'}],
              'rejected': 2, 'legacy_scope': 'UNKNOWN'}
    original = deepcopy(result)
    monkeypatch.setattr(runtime, '_shared_work_actor_scope', lambda action: (actor, scope))

    def read(**kwargs):
        assert kwargs == {'actor': actor, 'scope': scope}
        return result

    monkeypatch.setattr(graph, 'read_scoped_graph', read)

    def forbidden(*args, **kwargs):
        raise AssertionError('List enrichment must not access legacy state or write')

    monkeypatch.setattr(graph, 'write_scoped_graph_command', forbidden)
    monkeypatch.setattr(graph, 'get_event_graph', forbidden)
    app = Flask(__name__)

    def call(query='', mode='list', event_id=None):
        with app.test_request_context('/api/event-graph/events' + query):
            response = graph.graph_http(mode, event_id=event_id)
            if isinstance(response, tuple):
                return response[0].get_json(), response[1]
            return response.get_json(), response.status_code

    return graph, call, result, original


def test_labels_after_authorization_and_type_filter_preserve_graph(graph_list, monkeypatch):
    import scripts.topic_cluster as helper
    graph, call, result, original = graph_list
    seen = []

    def enrich(rows, top_k):
        seen.append(deepcopy(rows))
        assert top_k == 4
        rows[0]['injected'] = 'must not escape'
        return [{**rows[0], 'topic_label': 'solar / launch'}]

    monkeypatch.setattr(helper, 'enrich_events_with_labels', enrich)
    data, status = call('?type=marketing_event')
    assert status == 200 and data['count'] == 1
    assert seen == [[{'title': 'Solar launch campaign'}]]
    row = data['events'][0]
    assert {k: row[k] for k in original['events'][0]} == original['events'][0]
    assert 'injected' not in row
    assert row['topic_label'] == 'solar / launch'
    assert row['topic_label_provenance'] == {
        'claim_type': 'derived', 'status': 'available', 'input_fields': ['title'],
        'method': 'scripts.topic_cluster.enrich_events_with_labels',
        'limitation': 'title_only', 'top_k': 4,
    }
    assert data['relations'] == original['relations']
    assert data['rejected'] == 2 and result == original


@pytest.mark.parametrize('title', [None, '', '   ', '123'])
def test_real_helper_explicit_unnamed_title(graph_list, title):
    graph, call, result, original = graph_list
    result['events'][0]['title'] = title
    data, status = call('?type=marketing_event')
    row = data['events'][0]
    assert status == 200 and row['topic_label'] == '未命名主题'
    assert row['topic_label_provenance']['status'] == 'unnamed'
    assert row['topic_label_provenance']['reason'] == 'no_extractable_title_terms'
    assert row['description'] == 'DESCRIPTION SECRET'


def test_real_helper_repeat_reads_are_deterministic_and_do_not_mutate(graph_list):
    graph, call, result, original = graph_list
    first, status = call()
    second, _ = call()
    assert status == 200 and first == second and result == original
    assert all(row['topic_label_provenance']['status'] == 'available' for row in first['events'])
    assert 'secret' not in first['events'][0]['topic_label'].lower()
    assert 'unverified' not in first['events'][0]['topic_label'].lower()


@pytest.mark.parametrize('bad_result', [None, [], [{}], [{'topic_label': ''}], [{'topic_label': 3}]])
def test_malformed_helper_is_explicit_unavailable(graph_list, monkeypatch, bad_result):
    import scripts.topic_cluster as helper
    monkeypatch.setattr(helper, 'enrich_events_with_labels', lambda *args, **kwargs: bad_result)
    _, call, result, original = graph_list
    data, status = call('?type=marketing_event')
    row = data['events'][0]
    assert status == 200 and row['topic_label'] is None
    assert row['topic_label_provenance']['status'] == 'unavailable'
    assert row['topic_label_provenance']['reason'] == 'topic_label_enrichment_failed'
    assert result == original


def test_helper_failure_does_not_poison_other_rows_or_expose_exception(graph_list, monkeypatch):
    import scripts.topic_cluster as helper
    real = helper.enrich_events_with_labels

    def enrich(rows, top_k):
        if rows[0]['title'].startswith('Solar'):
            raise RuntimeError('PRIVATE EXCEPTION CONTENT')
        return real(rows, top_k=top_k)

    monkeypatch.setattr(helper, 'enrich_events_with_labels', enrich)
    _, call, result, original = graph_list
    data, status = call()
    assert status == 200 and data['events'][0]['topic_label'] is None
    assert data['events'][1]['topic_label_provenance']['status'] == 'available'
    assert 'PRIVATE EXCEPTION CONTENT' not in str(data)
    assert result == original


@pytest.mark.parametrize('mode,query,event_id,expected', [
    ('list', '?type=invalid', None, 400),
    ('stats', '', None, 200),
    ('chain', '', 'allowed', 200),
])
def test_non_list_or_invalid_type_never_calls_enrichment(graph_list, monkeypatch, mode, query, event_id, expected):
    graph, call, _, _ = graph_list

    def forbidden(*args, **kwargs):
        raise AssertionError('Enrichment outside authorized filtered list')

    monkeypatch.setattr(graph, '_scoped_title_topic_labels', forbidden)
    _, status = call(query, mode=mode, event_id=event_id)
    assert status == expected


def test_authorization_denial_never_calls_enrichment(graph_list, monkeypatch):
    import experience_runtime as runtime
    graph, call, _, _ = graph_list

    def denied(action):
        raise PermissionError('SCOPE_DENIED')

    def forbidden(*args, **kwargs):
        raise AssertionError('No enrichment before authorization')

    monkeypatch.setattr(runtime, '_shared_work_actor_scope', denied)
    monkeypatch.setattr(graph, '_scoped_title_topic_labels', forbidden)
    data, status = call()
    assert status == 403 and data['code'] == 'SCOPE_DENIED'


from tests.test_saved_document_workflow import workspace

# SQLite's WAL-index is shared coordination/cache state, not persistent rows.
# See https://sqlite.org/walformat.html sections 1.3, 1.4 and 2.1. In particular,
# reopening a quiescent WAL can rebuild iChange/checksums/read marks without a
# data write. Do not suppress all sidecars: DB/WAL/journal stay byte-exact and
# the SHM payload, WAL binding and checkpoint progress remain checked below.
def _read_snapshot(path, copy_dir):
    import sqlite3
    copy_dir.mkdir()
    files = {}
    for suffix in ('', '-wal', '-shm', '-journal'):
        source = path.with_name(path.name + suffix)
        if source.exists():
            raw = source.read_bytes()
            files[suffix] = raw
            (copy_dir / source.name).write_bytes(raw)
    # Inspect an independent copy, not another connection to the measured DB.
    con = sqlite3.connect((copy_dir / path.name).as_uri() + '?mode=ro', uri=True)
    try:
        schema = con.execute('SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name').fetchall()
        rows = {}
        for kind, name, _, _ in schema:
            if kind == 'table':
                quoted = '"' + name.replace('"', '""') + '"'
                rows[name] = sorted(con.execute('SELECT * FROM ' + quoted).fetchall(), key=repr)
    finally:
        con.close()
    return {'files': files, 'schema': schema, 'rows': rows}


def _check_shm_binding(shm, wal):
    import struct
    assert len(shm) >= 32768 and len(shm) % 32768 == 0
    assert shm[:48] == shm[48:96], 'SHM header copies disagree'
    u32 = lambda offset: struct.unpack_from('=I', shm, offset)[0]
    assert u32(0) == 3007000 and u32(4) == 0 and shm[12] == 1
    page_size = struct.unpack_from('>I', wal, 8)[0]
    assert struct.unpack_from('=H', shm, 14)[0] == (1 if page_size == 65536 else page_size)
    mx_frame = u32(16)
    assert mx_frame > 0 and 32 + mx_frame * (24 + page_size) <= len(wal)
    frame = 32 + (mx_frame - 1) * (24 + page_size)
    assert u32(20) == struct.unpack_from('>I', wal, frame + 4)[0]
    assert tuple(struct.unpack_from('=2I', shm, 24)) == tuple(struct.unpack_from('>2I', wal, frame + 16))
    assert shm[32:40] == wal[16:24], 'SHM points to a different WAL generation'
    s1 = s2 = 0
    words = struct.unpack_from('=10I', shm)
    for i in range(0, len(words), 2):
        s1 = (s1 + words[i] + s2) & 0xffffffff
        s2 = (s2 + words[i + 1] + s1) & 0xffffffff
    assert (s1, s2) == struct.unpack_from('=2I', shm, 40), 'Invalid SHM header checksum'
    assert u32(96) <= u32(128) <= mx_frame
    assert all(mark == 0xffffffff or mark <= mx_frame for mark in struct.unpack_from('=5I', shm, 100))


def _assert_read_snapshot_unchanged(before, after):
    persistent = lambda snapshot: {k: v for k, v in snapshot['files'].items() if k != '-shm'}
    assert persistent(before) == persistent(after), 'Persistent DB/WAL/journal bytes changed'
    assert before['schema'] == after['schema'], 'Schema changed during a read'
    assert before['rows'] == after['rows'], 'Logical rows changed during a read'
    left, right = before['files'].get('-shm'), after['files'].get('-shm')
    if left == right:
        return
    assert left is not None and right is not None, 'Unexpected SHM creation/removal'
    assert len(left) == len(right), 'Unexpected SHM resize'
    wal = before['files']['-wal']
    _check_shm_binding(left, wal)
    _check_shm_binding(right, wal)
    # iChange and its two header checksums, read marks and recovery's
    # nBackfillAttempted may change. nBackfill (96..99), mxFrame, WAL identity,
    # hash tables and all other bytes must remain unchanged. No checkpoint is
    # allowed to advance merely because a graph list was requested.
    allowed = set()
    for start, stop in ((8, 12), (40, 48), (56, 60), (88, 96), (100, 120), (128, 132)):
        allowed.update(range(start, stop))
    changed = {i for i, (a, b) in enumerate(zip(left, right)) if a != b}
    assert changed <= allowed, f'Unexpected SHM mutation at offsets {sorted(changed - allowed)}'


def _observe_readonly_connections(monkeypatch, path):
    import sqlite3
    from pathlib import Path
    from urllib.parse import parse_qs, urlsplit
    from urllib.request import url2pathname
    original = sqlite3.connect
    observed = []

    def connect(database, *args, **kwargs):
        target = str(database)
        parts = urlsplit(target)
        actual_path = Path(url2pathname(parts.path) if target.startswith('file:') else target).resolve()
        con = original(database, *args, **kwargs)
        if actual_path != path.resolve():
            return con
        try:
            assert kwargs.get('uri') is True and parse_qs(parts.query).get('mode') == ['ro']
            # Prove native read-only mode before attaching the SQL write guard;
            # a SQL authorizer denial alone would not prove a read-only handle.
            with pytest.raises(sqlite3.OperationalError) as denied:
                con.execute('CREATE TABLE forbidden_readonly_probe(value TEXT)')
            assert denied.value.sqlite_errorcode == sqlite3.SQLITE_READONLY
            assert con.total_changes == 0 and not con.in_transaction
            record = {'target': target, 'sql': [], 'denied': []}
            observed.append(record)
            con.set_trace_callback(record['sql'].append)

            def authorizer(action, arg1, arg2, database, trigger):
                allowed = action in (sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION)
                if action == sqlite3.SQLITE_PRAGMA:
                    pragma = str(arg1).lower()
                    allowed = (pragma in {'busy_timeout', 'foreign_keys'}
                               or (pragma in {'database_list', 'read_uncommitted'} and arg2 is None))
                if not allowed:
                    record['denied'].append((action, arg1, arg2))
                    return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK

            con.set_authorizer(authorizer)
        except BaseException:
            con.close()
            raise
        return con

    monkeypatch.setattr(sqlite3, 'connect', connect)
    return observed


def _synthetic_quiescent_wal(path):
    import sqlite3
    writer = sqlite3.connect(path)
    reader = None
    try:
        assert writer.execute('PRAGMA journal_mode=WAL').fetchone()[0] == 'wal'
        writer.execute('CREATE TABLE business_rows(id INTEGER PRIMARY KEY, value TEXT NOT NULL)')
        writer.commit()
        for i in range(13):
            writer.execute('INSERT INTO business_rows(value) VALUES(?)', (f'synthetic-{i}',))
            writer.commit()
        reader = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
        reader.execute('BEGIN')
        assert len(reader.execute('SELECT * FROM business_rows').fetchall()) == 13
        writer.close()
    finally:
        writer.close()
        if reader is not None:
            reader.close()


def test_readonly_quiescent_wal_preserves_persistent_state(tmp_path, monkeypatch):
    import sqlite3
    path = tmp_path / 'rebuild.sqlite3'
    _synthetic_quiescent_wal(path)
    before = _read_snapshot(path, tmp_path / 'before')
    with monkeypatch.context() as scoped:
        observed = _observe_readonly_connections(scoped, path)
        con = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
        try:
            rows = con.execute('SELECT * FROM business_rows ORDER BY id').fetchall()
            assert con.total_changes == 0 and not con.in_transaction
        finally:
            con.close()
    after = _read_snapshot(path, tmp_path / 'after')
    assert len(rows) == 13 and observed and not any(r['denied'] for r in observed)
    # SQLite 3.53.1 on the recorded Linux host rebuilds iChange 14 -> 0 here.
    # A different supported VFS may retain its cache; change is not required.
    _assert_read_snapshot_unchanged(before, after)


@pytest.mark.parametrize('effect', ['wal_write', 'checkpoint'])
def test_read_snapshot_guard_rejects_real_write_or_checkpoint(tmp_path, effect):
    import sqlite3
    path = tmp_path / 'negative.sqlite3'
    _synthetic_quiescent_wal(path)
    before = _read_snapshot(path, tmp_path / 'before')
    con = sqlite3.connect(path)
    try:
        if effect == 'wal_write':
            con.execute('INSERT INTO business_rows(value) VALUES(?)', ('must-be-detected',))
            con.commit()
        else:
            result = con.execute('PRAGMA wal_checkpoint(FULL)').fetchone()
            assert result[0] == 0 and result[1] == result[2]
        after = _read_snapshot(path, tmp_path / 'after')
        changed_file = '-wal' if effect == 'wal_write' else ''
        assert before['files'][changed_file] != after['files'][changed_file]
        with pytest.raises(AssertionError, match='Persistent DB/WAL/journal bytes changed'):
            _assert_read_snapshot_unchanged(before, after)
    finally:
        con.close()


@pytest.mark.parametrize('offset', [16, 96, 136, 20000])
def test_read_snapshot_guard_does_not_ignore_other_shm_mutations(tmp_path, offset):
    path = tmp_path / 'negative-shm.sqlite3'
    _synthetic_quiescent_wal(path)
    before = _read_snapshot(path, tmp_path / 'before')
    mutated = bytearray(before['files']['-shm'])
    mutated[offset] ^= 1
    after = {**before, 'files': {**before['files'], '-shm': bytes(mutated)}}
    with pytest.raises(AssertionError):
        _assert_read_snapshot_unchanged(before, after)


def test_real_scoped_list_filters_before_labels_and_repeat_reads_preserve_database(workspace, monkeypatch):
    """Real signed graph rows, real authorization/filtering, and byte-for-byte reads."""
    import event_graph as graph
    import experience_runtime as runtime
    import scripts.topic_cluster as helper

    ws = workspace
    actor, scope = ws['actor'], ws['scope']
    monkeypatch.setattr(graph, 'get_repository', lambda: ws['repo'])

    def write(command, payload, request_id, target_scope=scope):
        prepared = graph.prepare_scoped_graph_command(
            command, payload, actor=actor, scope=target_scope, request_id=request_id)
        ws['gate'].grant_approval('db_write', resource=prepared['resource'],
                                 granted_by='synthetic-topic-label-test')
        return graph.write_scoped_graph_command(command, payload, actor=actor,
            scope=target_scope, request_id=request_id, resource=prepared['resource'])['output']

    allowed = write('create', {'event_type': 'marketing_event',
        'title': 'Solar launch campaign', 'description': 'Description must stay separate'},
        'topic-real-allowed')[0]
    other_type = write('create', {'event_type': 'propagation_event',
        'title': 'Filtered propagation secret'}, 'topic-real-other-type')[0]
    other_scope = write('create', {'event_type': 'marketing_event',
        'title': 'Other domain secret'}, 'topic-real-other-scope',
        {**scope, 'domain_id': 'zbmp'})[0]
    invalid = write('create', {'event_type': 'marketing_event',
        'title': 'Original integrity title'}, 'topic-real-integrity')[0]
    write('relation', {'source_event_id': allowed, 'target_event_id': other_type,
        'relation_type': 'follow', 'evidence': 'Synthetic user statement'},
        'topic-real-relation')
    with ws['repo'].transaction() as con:
        con.execute('UPDATE event_graph_events SET title=? WHERE event_id=?',
                    ('Tampered integrity secret', invalid))
    original = graph.read_scoped_graph(actor=actor, scope=scope)
    assert {r['event_id'] for r in original['events']} == {allowed, other_type}
    assert original['rejected'] == 1
    seen = []
    real = helper.enrich_events_with_labels

    def observe(rows, top_k):
        seen.extend(deepcopy(rows))
        return real(rows, top_k=top_k)

    monkeypatch.setattr(helper, 'enrich_events_with_labels', observe)
    # Only HTTP principal transport is substituted; saved_work.authorize and
    # read_scoped_graph perform their actual context/integrity checks.
    monkeypatch.setattr(runtime, '_shared_work_actor_scope', lambda action: (actor, scope))

    path = ws['root'] / 'isolated.sqlite3'
    before = _read_snapshot(path, ws['root'] / 'read-snapshot-before')
    responses = []
    for index in range(2):
        with monkeypatch.context() as scoped:
            observed = _observe_readonly_connections(scoped, path)
            with ws['app'].test_request_context('/api/event-graph/events?type=marketing_event', headers={'Host':'localhost'}, environ_overrides={'REMOTE_ADDR':'127.0.0.1'}):
                response = graph.graph_http('list')
                assert response.status_code == 200
                responses.append(response.get_json())
            assert observed and not any(record['denied'] for record in observed)
            assert all(any(sql.lstrip().upper().startswith('SELECT') for sql in record['sql'])
                       for record in observed)
        after = _read_snapshot(path, ws['root'] / f'read-snapshot-after-{index}')
        _assert_read_snapshot_unchanged(before, after)
    assert responses[0] == responses[1]
    data = responses[0]
    assert data['count'] == 1 and data['events'][0]['event_id'] == allowed
    assert seen == [{'title': 'Solar launch campaign'}] * 2
    row = next(r for r in original['events'] if r['event_id'] == allowed)
    assert {key: data['events'][0][key] for key in row} == row
    assert data['relations'] == original['relations']
    assert data['events'][0]['topic_label_provenance']['claim_type'] == 'derived'
    assert other_scope not in str(data['events']) and invalid not in str(data['events'])
