"""Persisted Task dimension counts, exact custody and SQLite snapshot tests."""
import json
import os
import sqlite3
from contextlib import contextmanager
import pytest
import ai_task_engine as module
from database import get_db
from agent_research.taxonomy import RESEARCH_DIMENSIONS
from tests.test_managed_report_tasks import engine, _context
from tests.test_saved_document_workflow import workspace
from tests.test_shared_work_owner_routes import route_workspace
from tests.test_growth_research_shared import research, start, BASE, SHARED

STATES = ('pending', 'running', 'interrupted', 'failed', 'cancelled', 'succeeded')


def seed(engine, dimension='business', state='pending', **context):
    task = engine.create_report_task(_context(research={'dimension': dimension}, **context))
    with get_db() as con:
        con.execute('UPDATE ai_task SET status=? WHERE task_id=?', (state, task['task_id']))
    return task


def listing(engine, **options):
    return engine.list_report_tasks(actor_ref=_context()['actor_ref'], scope=_context()['scope'], **options)


def test_full_matrix_zero_dimensions_totals_labels_and_filtered_paging(engine):
    dimensions = [d['key'] for d in RESEARCH_DIMENSIONS[:8]]
    for dimension in dimensions:
        for state in STATES:
            seed(engine, dimension, state)
    seed(engine, actor_ref='actor:2')
    seed(engine, scope={**_context()['scope'], 'subject_id': 'other-subject'})
    seed(engine, scope={**_context()['scope'], 'entity_label': 'other-full-scope-label'})
    first = listing(engine, limit=3)
    assert first['total'] == first['summary']['total'] == 48
    assert first['summary']['basis'] == 'persisted_task_state_same_sqlite_snapshot'
    assert first['summary']['business_outcome'] == 'NOT_ESTABLISHED'
    summary = first['summary']['dimensions']
    assert len(summary) == 9 and sum(d['task_count'] for d in summary) == 48
    for item, expected in zip(summary, RESEARCH_DIMENSIONS):
        assert all(item[k] == expected[k] for k in ('key', 'zh', 'en', 'ko'))
        assert set(item['states']) == set(STATES)
        if item['key'] in dimensions:
            assert item['task_count'] == 6 and item['open'] == 4 and item['completed'] == 1
            assert set(item['states'].values()) == {1}
        else:
            assert item['task_count'] == item['open'] == item['completed'] == 0
            assert set(item['states'].values()) == {0}
    seen = []
    page = first
    while True:
        seen += [task['task_id'] for task in page['items']]
        if not page['has_more']:
            break
        page = listing(engine, limit=3, cursor=page['next_cursor'])
        assert page['summary'] == first['summary'] and page['total'] == 48
    assert len(seen) == len(set(seen)) == 48
    filtered = listing(engine, dimension=dimensions[0], state='succeeded', limit=1)
    assert filtered['total'] == 1 and filtered['summary'] == first['summary']


@pytest.mark.parametrize('field,value', [('dimension', 'unknown'), ('status', 'unknown')])
def test_unknown_persisted_classification_fails_even_outside_requested_page(engine, field, value):
    task = seed(engine)
    seed(engine, 'technology')
    with get_db() as con:
        if field == 'dimension':
            context = {**task['context'], 'research': {'dimension': value}}
            con.execute('UPDATE ai_task SET context_json=? WHERE task_id=?', (json.dumps(context), task['task_id']))
        else:
            con.execute('UPDATE ai_task SET status=? WHERE task_id=?', (value, task['task_id']))
    with pytest.raises(RuntimeError, match='SUMMARY_UNKNOWN_CLASSIFICATION'):
        listing(engine, dimension='technology', limit=1)


def test_unknown_dimension_parameter_rejected(engine):
    with pytest.raises(ValueError):
        listing(engine, dimension='not-a-dimension')


def test_wal_writer_between_aggregate_and_page_cannot_split_snapshot(engine, monkeypatch):
    seed(engine)
    second = seed(engine, 'technology')
    db_path = os.environ['ZBC_DB_PATH']
    with sqlite3.connect(db_path) as con:
        assert con.execute('PRAGMA journal_mode=WAL').fetchone()[0] == 'wal'
    original = module.get_db
    written = []
    @contextmanager
    def interleaved_db():
        with original() as con:
            def trace(sql):
                if sql.startswith('SELECT COUNT(*) FROM ai_task') and not written:
                    with sqlite3.connect(db_path) as writer:
                        writer.execute('DELETE FROM ai_task WHERE task_id=?', (second['task_id'],))
                    written.append(True)
            con.set_trace_callback(trace)
            yield con
    monkeypatch.setattr(module, 'get_db', interleaved_db)
    result = listing(engine)
    assert written == [True]
    assert result['total'] == result['summary']['total'] == len(result['items']) == 2
    assert second['task_id'] in [item['task_id'] for item in result['items']]
    current = listing(engine)
    assert current['total'] == current['summary']['total'] == len(current['items']) == 1


def test_http_summary_pages_and_anonymous_denial(research):
    for dimension in ('business', 'business', 'technology'):
        start(research, defer=True, research={'dimension': dimension})
    response = research['api'].get(BASE + '/tasks', headers=SHARED, query_string={'limit': 1})
    assert response.status_code == 200, response.get_json()
    result = response.get_json()['result']
    assert result['total'] == result['summary']['total'] == 3 and len(result['items']) == 1
    assert len(result['summary']['dimensions']) == 9
    assert research['api'].get(BASE + '/tasks', headers=SHARED,
        query_string={'dimension': 'unknown'}).status_code == 400
    research['app'].config['LUMENIS_OPEN_WORKSPACE'] = False
    denied = research['api'].get(BASE + '/tasks', headers=SHARED)
    assert denied.status_code in (401, 403) and 'summary' not in str(denied.get_json())


def test_http_revocation_after_database_read_does_not_release_summary(research, monkeypatch):
    from lumenis.shared.reporting import source_brief_tasks
    start(research, defer=True)
    task_engine = source_brief_tasks.engine()
    original = task_engine.list_report_tasks
    def revoke_after_read(**kwargs):
        result = original(**kwargs)
        research['app'].config['LUMENIS_OPEN_WORKSPACE'] = False
        return result
    monkeypatch.setattr(task_engine, 'list_report_tasks', revoke_after_read)
    monkeypatch.setattr(source_brief_tasks, 'engine', lambda: task_engine)
    denied = research['api'].get(BASE + '/tasks', headers=SHARED)
    assert denied.status_code in (401, 403), denied.get_json()
    assert 'summary' not in str(denied.get_json())
