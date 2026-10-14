from contextlib import contextmanager
from types import SimpleNamespace

import xhs_cookie_bridge as bridge


def _query(keyword, subject_id):
    return SimpleNamespace(
        keyword=keyword,
        product_id='CTH',
        scope={
            'domain_id': 'cth',
            'subject_id': subject_id,
            'brand_focus_id': None,
            'global_scope': False,
        },
    )


def test_xhs_analysis_and_events_are_isolated_per_admitted_scope(monkeypatch):
    plan = SimpleNamespace(queries=(
        _query('North Star', 'SUBJECT-A'),
        _query('North Star launch', 'SUBJECT-A'),
        _query('South Star', 'SUBJECT-B'),
    ))
    scope_a = bridge._canonical_query_scope(plan.queries[0])
    scope_b = bridge._canonical_query_scope(plan.queries[2])
    row_a = {'id': 20, 'note_id': 'note-a', 'subject_id': 'SUBJECT-A'}
    row_b = {'id': 19, 'note_id': 'note-b', 'subject_id': 'SUBJECT-B'}
    statements = []

    class _Connection:
        def execute(self, sql, params):
            statements.append((sql, params))
            assert "scope_status='VERIFIED'" in sql
            assert 'product_id=?' in sql and 'domain_id=?' in sql
            assert "COALESCE(subject_id,'')=?" in sql
            assert "COALESCE(brand_focus_id,'')=?" in sql
            assert 'source_keyword IN (' in sql
            assert 'LIMIT ?' in sql
            subject_id = params[2]
            assert params[0:2] == ('CTH', 'cth')
            assert params[3] == ''
            return SimpleNamespace(fetchall=lambda: [row_a] if subject_id == 'SUBJECT-A' else [row_b])

    class _Database:
        @staticmethod
        @contextmanager
        def get_db():
            yield _Connection()

    groups, rows_by_scope, skipped, failures = bridge._load_scoped_pending_analysis(
        plan, database_module=_Database, limit=20,
    )
    assert skipped == 0
    assert failures == []
    assert len(statements) == 2
    assert rows_by_scope[bridge._scope_key(scope_a)][1] == [row_a]
    assert rows_by_scope[bridge._scope_key(scope_b)][1] == [row_b]

    analysis_calls = []
    event_calls = []

    class _Reprocess:
        @staticmethod
        def analyze_note_row(row, *, translate, scope):
            assert translate is False
            assert row['subject_id'] == scope['subject_id']
            analysis_calls.append((row['note_id'], scope))
            if row['note_id'] == 'note-a':
                raise RuntimeError('isolated analysis failure')

        @staticmethod
        def build_cross_platform_events(*, limit, scope):
            assert limit == 100
            event_calls.append(scope)
            if scope['subject_id'] == 'SUBJECT-A':
                raise RuntimeError('isolated event failure')
            return {'status': 'COMPLETED'}

    monkeypatch.setattr(
        bridge, '_run_search',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('collection must not run')),
    )
    monkeypatch.setattr(
        bridge, 'create_task',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('browser/task must not run')),
    )
    results = []
    scopes = {key: group['scope'] for key, group in groups.items()}
    bridge._run_scoped_postprocess(rows_by_scope, scopes, _Reprocess, results)

    assert [(note_id, scope['subject_id']) for note_id, scope in analysis_calls] == [
        ('note-a', 'SUBJECT-A'), ('note-b', 'SUBJECT-B'),
    ]
    assert {scope['subject_id'] for scope in event_calls} == {'SUBJECT-A', 'SUBJECT-B'}
    assert len(event_calls) == 2
    assert any(item.get('stage') == 'analysis' and item.get('scope') == bridge._scope_key(scope_a)
               and item.get('status') == 'FAILED' for item in results)
    assert any(item.get('stage') == 'event_aggregation'
               and item.get('scope') == bridge._scope_key(scope_a)
               and item.get('status') == 'FAILED' for item in results)
    assert any(item.get('stage') == 'event_aggregation'
               and item.get('scope') == bridge._scope_key(scope_b)
               and item.get('status') == 'COMPLETED' for item in results)
