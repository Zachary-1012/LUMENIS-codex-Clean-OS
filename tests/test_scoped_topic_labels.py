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

    def snapshot():
        return {p.name: p.read_bytes() for p in ws['root'].iterdir()
                if p.is_file() and (p.name.endswith('.sqlite3') or
                                   '.sqlite3-' in p.name)}

    before = snapshot()
    assert 'isolated.sqlite3' in before
    responses = []
    for _ in range(2):
        with ws['app'].test_request_context('/api/event-graph/events?type=marketing_event', headers={'Host':'localhost'}, environ_overrides={'REMOTE_ADDR':'127.0.0.1'}):
            response = graph.graph_http('list')
            assert response.status_code == 200
            responses.append(response.get_json())
        assert snapshot() == before
    assert responses[0] == responses[1]
    data = responses[0]
    assert data['count'] == 1 and data['events'][0]['event_id'] == allowed
    assert seen == [{'title': 'Solar launch campaign'}] * 2
    row = next(r for r in original['events'] if r['event_id'] == allowed)
    assert {key: data['events'][0][key] for key in row} == row
    assert data['relations'] == original['relations']
    assert data['events'][0]['topic_label_provenance']['claim_type'] == 'derived'
    assert other_scope not in str(data['events']) and invalid not in str(data['events'])
