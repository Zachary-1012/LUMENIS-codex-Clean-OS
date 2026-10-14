"""Isolated regressions for cross-owner defects; never product/user acceptance."""
import copy
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import sqlite3
from types import SimpleNamespace

import pytest

from tests.test_source_brief_job import job_db, _source, _document_row


def test_actual_cdp_projection_reaches_business_time_review():
    from tests.test_xhs_cdp_native_truth import collector_functions
    from lumenis.system.collector.adapters.secondary_collection import prepare_xhs_observations, _business_source_reviews
    raw = {'note_id': 'isolated-post', 'detail_publish_time': '2026-10-02T09:30:00+08:00',
           'desc': 'ExampleVenue event observation', 'url': 'https://source.example/post',
           'collected_at': '2026-10-03T00:00:00Z', 'publication_time_source': 'detail',
           'time_source_observations': [{'source': 'detail'}]}
    normalized = collector_functions()._norm_cdp_note(raw)
    projected = prepare_xhs_observations([normalized], keyword='ExampleVenue')
    assert projected[0]['time'] == raw['detail_publish_time']
    query = SimpleNamespace(business_context={'platform': 'xiaohongshu',
        'entity_aliases': ('ExampleVenue',), 'publication_since': '2026-10-01T00:00:00Z',
        'publication_until': '2026-10-04T00:00:00Z'})
    reviewed = _business_source_reviews(projected, query, '2026-10-03T00:00:00Z')
    assert reviewed[0]['status'] == 'CANDIDATE_TASK_RELEVANT'
    assert reviewed[0]['admitted'] is False
    assert projected[0]['captured_at'] != projected[0]['time']


@pytest.mark.parametrize('platform,unit', [('xiaohongshu', 1000), ('douyin', 1)])
def test_business_review_uses_existing_native_epoch_units(platform, unit):
    from lumenis.system.collector.adapters.secondary_collection import _business_source_reviews
    from lumenis.system.collector.adapters.platform_naming import get_platform_fields
    native = int(datetime(2026, 10, 2, tzinfo=timezone.utc).timestamp()) * unit
    record = {'content_id': 'post-epoch', 'url': 'https://source.example/post',
              'title': 'ExampleVenue', get_platform_fields(platform).published_at: native}
    query = SimpleNamespace(business_context={'platform': platform,
        'entity_aliases': ('ExampleVenue',), 'publication_since': '2026-10-01T00:00:00Z',
        'publication_until': '2026-10-04T00:00:00Z'})
    original = copy.deepcopy(record)
    reviewed = _business_source_reviews([record], query, '2026-10-03T00:00:00Z')
    assert reviewed[0]['status'] == 'CANDIDATE_TASK_RELEVANT'
    assert record == original


def test_capture_or_rejected_display_time_never_becomes_publication():
    from tests.test_xhs_cdp_native_truth import collector_functions
    from lumenis.system.collector.adapters.secondary_collection import prepare_xhs_observations
    raw = {'note_id': 'unknown-time', 'detail_publish_time': '2026-10-02T09:00:00+08:00',
           'publication_time_source': 'updated', 'time_source_observations': [],
           'collected_at': '2026-10-03T00:00:00Z'}
    normalized = collector_functions()._norm_cdp_note(raw)
    assert prepare_xhs_observations([normalized], keyword='fixture')[0]['time'] is None


def test_document_parent_and_rows_share_one_decision_source(job_db):
    from api_dual_domain import BusinessDecisionWorkflow
    from lumenis.shared.reporting.source_brief_job import create_source_brief_job
    scope = {'product_id': 'CTH', 'domain_id': 'cth', 'subject_id': 'SUBJECT-A', 'brand_focus_id': None}
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        evidence = _source(conn, source_id='doc-fixture', source_type='document')
        _document_row(conn, 'doc-fixture', evidence)
        conn.commit()
        report = create_source_brief_job(conn, product_id='CTH', subject_id='SUBJECT-A',
            global_scope=False, entity_label='Fixture', actor_id='workspace:local',
            permission_audit_ref='audit:fixture', trace_id='trace-fixture', job_id='job-document-fixture')
        assert report['artifact_outcome']['source_count'] == 1
        row = BusinessDecisionWorkflow._canonical_source(conn, 'doc-fixture', scope)
        assert row['source_type'] == 'document'
        assert row['scope_evidence_ref'] == str(evidence)


@pytest.mark.parametrize('conflict', ['different_evidence', 'duplicate_parent'])
def test_document_identity_conflicts_are_not_hidden(job_db, conflict):
    from api_dual_domain import BusinessDecisionWorkflow
    scope = {'product_id': 'CTH', 'domain_id': 'cth', 'subject_id': 'SUBJECT-A', 'brand_focus_id': None}
    with sqlite3.connect(job_db) as conn:
        conn.row_factory = sqlite3.Row
        evidence = _source(conn, source_id='conflict-doc', source_type='document')
        _document_row(conn, 'conflict-doc', evidence)
        if conflict == 'different_evidence':
            conn.execute("UPDATE canonical_data SET scope_evidence_ref='different-proof' WHERE source_type='document_row'")
        else:
            row = dict(conn.execute("SELECT * FROM canonical_data WHERE source_type='document'").fetchone())
            row['canonical_id'] = 'duplicate-parent'
            conn.execute('INSERT INTO canonical_data (' + ','.join(row) + ') VALUES (' + ','.join('?' for _ in row) + ')', tuple(row.values()))
        with pytest.raises(PermissionError, match='BUSINESS_WORK_SOURCE_SCOPE_INVALID'):
            BusinessDecisionWorkflow._canonical_source(conn, 'conflict-doc', scope)


def test_export_scope_failure_never_opens_database(monkeypatch):
    from lumenis.shared.reporting import export_api
    calls = []
    def unavailable(_action='read'):
        raise RuntimeError('REPORT_SCOPE_REQUIRED')
    monkeypatch.setattr(export_api, '_request_report_scope', unavailable)
    monkeypatch.setattr(export_api, 'get_db', lambda: calls.append('opened') or sqlite3.connect(':memory:'))
    with pytest.raises(PermissionError):
        export_api.filter_notes_by_period('daily', '2026-10-02')
    assert calls == []


def test_export_uses_resolved_scope_and_rechecks_source_use(monkeypatch):
    from lumenis.shared.reporting import export_api
    actor = object()
    scope = {'domain_id': 'cth', 'product_id': 'CTH', 'subject_id': 'SUBJECT-A',
             'brand_focus_id': None, 'global_scope': False}
    rows = [{'source_type': 'note', 'source_id': 'a', 'subject_id': 'SUBJECT-A'}]
    reads, verified = [], []
    monkeypatch.setattr(export_api, '_request_report_scope',
                        lambda action='read': (actor, scope, [], None))
    def scoped_read(actual_scope, **kwargs):
        reads.append((actual_scope, kwargs))
        return {'sources': rows, 'truncated': False, 'rejected_count': 0, 'state': 'AVAILABLE'}
    monkeypatch.setattr(export_api.db, 'get_scoped_event_source_rows', scoped_read)
    monkeypatch.setattr(export_api, '_verify_report_source_use',
                        lambda actual_actor, actual_scope, notes, events:
                        verified.append((actual_actor, actual_scope, notes, events)) or 1)

    selected, start, end = export_api.filter_notes_by_period('daily', '2026-10-02')

    assert selected == rows
    assert start.strftime('%Y-%m-%d') == end.strftime('%Y-%m-%d') == '2026-10-02'
    assert reads[0][0]['subject_id'] == 'SUBJECT-A'
    assert reads[0][1]['date_start'] == reads[0][1]['date_end'] == '2026-10-02'
    assert verified == [(actor, scope, rows, [])]


@pytest.mark.parametrize('output', [None, {}, [], ''])
def test_missing_content_has_no_quality_score(output):
    import content_generation as generation
    result = generation.evaluate_content(output, {'brand': 'Fixture'}, 'ad_copy')
    assert result['overall'] is None
    assert all(score is None for score in result['scores'].values())
    assert result['status'] == 'NOT_EVALUATED'


def test_failed_generation_preserves_failure_without_positive_evaluation(tmp_path, monkeypatch):
    import content_generation as generation
    from lumenis.shared.database.repository import DatabaseRepository
    db = tmp_path / 'generation.sqlite3'
    monkeypatch.setattr(generation, 'get_repository', lambda: DatabaseRepository(str(db)))
    monkeypatch.setattr(generation, 'build_research_context', lambda *args: '')
    monkeypatch.setattr(generation, '_call_ai', lambda *args, **kwargs: (None, 'provider_disabled', {}))
    generation.init_db()
    result = generation.generate_content('ad_copy', brand='Fixture')
    assert result['ok'] is False
    assert result['evaluation_id'] is None
    assert result['evaluation']['overall'] is None
    with sqlite3.connect(db) as conn:
        assert conn.execute('SELECT count(*) FROM content_generation_evidence WHERE status=?', ('failed',)).fetchone()[0] == 1
        assert conn.execute('SELECT count(*) FROM content_evaluation').fetchone()[0] == 0


@pytest.mark.parametrize('payload', [{'ok': False, 'error': 'SOURCE_FAILED'}, {'success': True, 'ok': False}, {'ok': 'false'}, {'success': False, 'error': 'DENIED'}])
def test_formed_handler_failure_never_becomes_success(payload):
    from agent_capability.router import CapabilityRouter
    from tests.agent_runtime.test_formation_dispatch import tool, plan
    router = CapabilityRouter(enabled=True)
    router.register_tool(tool(lambda: copy.deepcopy(payload)))
    step = plan().steps[0]
    formed = router.form_step(step, {})
    assert formed.invoke(step, {})['success'] is False


def test_formed_handler_success_keeps_real_result():
    from agent_capability.router import CapabilityRouter
    from tests.agent_runtime.test_formation_dispatch import tool, plan
    router = CapabilityRouter(enabled=True)
    router.register_tool(tool(lambda: {'ok': True, 'data': {'count': 0}}))
    step = plan().steps[0]
    result = router.form_step(step, {}).invoke(step, {})
    assert result['success'] is True
    assert result['result']['data']['count'] == 0


@pytest.mark.parametrize('failure', ['trace_false', 'evidence_exception'])
def test_executed_handler_without_durable_evidence_requires_reconciliation(monkeypatch, failure):
    from agent_capability.router import CapabilityRouter, ToolActorContext
    import lumenis.shared.agents.skills.execution as execution
    from tests.agent_runtime.test_formation_dispatch import tool
    monkeypatch.setattr(execution, 'check_permission', lambda *args, **kwargs: {'allowed': True})
    monkeypatch.setattr(execution, 'action_firewall', lambda *args, **kwargs: {'allowed': True})
    monkeypatch.setattr(execution, 'effect_fence', lambda *args, **kwargs: {'allowed': True})
    monkeypatch.setattr(execution, 'write_trace', lambda *args, **kwargs: failure != 'trace_false')
    if failure == 'evidence_exception':
        def broken(*args): raise RuntimeError('fixture evidence unavailable')
        monkeypatch.setattr(execution, 'build_evidence', broken)
    called = []
    router = CapabilityRouter(enabled=True, actor_authorizer=lambda *args: True)
    router.register_tool(tool(lambda: called.append('executed') or {'identity': 'original'}))
    result = router.execute_tool('source_read', {}, actor_context=ToolActorContext(7, 'user', 'CTH', 'cth', 'cth_analyst'))
    assert called == ['executed']
    assert result.success is False
    assert result.reconciliation_required is True


@pytest.fixture
def task_engine(tmp_path, monkeypatch):
    import ai_task_engine as engine
    monkeypatch.setenv('ZBC_DB_PATH', str(tmp_path / 'tasks.sqlite3'))
    return engine.TaskEngine()


@pytest.mark.parametrize('terminal', ['succeeded', 'cancelled', 'unknown'])
def test_cancel_preserves_committed_terminal_result(task_engine, terminal):
    task = task_engine.create_task('isolated terminal cancellation')
    task_engine._db_update_task(task['task_id'], status=terminal, result_json=json.dumps({'artifact_id': 'fixture-result'}), finished_at='2026-10-02T00:00:00Z')
    before = task_engine.get_task(task['task_id'])
    assert task_engine.cancel_task(task['task_id']) == before
    assert task_engine.get_task(task['task_id']) == before


def test_cancel_pending_task_remains_available(task_engine):
    task = task_engine.create_task('isolated pending cancellation')
    assert task_engine.cancel_task(task['task_id'])['status'] == 'cancelled'


class Tags(HTMLParser):
    def __init__(self): super().__init__(); self.tags = []
    def handle_starttag(self, tag, attrs): self.tags.append(tag)


def test_kos_report_treats_source_text_as_text():
    from lumenis.shared.reporting.kos import _render_html, _render_channel_roi
    unsafe = '</script><img src=x onerror=alert(1)><script>'
    source = {'brand_name': unsafe, 'generated_at': '2026-10-10', 'top_notes': [{'title': unsafe}], 'top_kos': [{'author_nickname': unsafe}], 'overview': {'by_lifecycle': {unsafe: 1}}}
    before = copy.deepcopy(source)
    html = _render_html(source)
    baseline = Tags(); baseline.feed(_render_html({**source, 'brand_name': 'Fixture'}))
    parsed = Tags(); parsed.feed(html)
    assert 'img' not in parsed.tags
    assert parsed.tags.count('script') == baseline.tags.count('script')
    assert unsafe not in html
    assert source == before
    channel = _render_channel_roi({'channels': [{'label': unsafe, 'cpl': None}]})
    tags = Tags(); tags.feed(channel)
    assert 'img' not in tags.tags and 'script' not in tags.tags


@pytest.mark.parametrize('issuer', ['missing', 'exception', 'empty'])
def test_failed_approval_issuer_cannot_mark_task_approved(task_engine, monkeypatch, issuer):
    task = task_engine.create_task('isolated approval receipt failure')
    task_engine._db_update_task(task['task_id'], status='awaiting_approval')
    def grant(**kwargs):
        if issuer == 'exception': raise RuntimeError('fixture issuer failure')
        return ''
    gate = None if issuer == 'missing' else SimpleNamespace(grant_approval=grant)
    monkeypatch.setattr(type(task_engine), 'permission_gate', property(lambda self: gate))
    before = task_engine.get_task(task['task_id'])
    with pytest.raises(PermissionError, match='TASK_APPROVAL_'):
        task_engine.approve_task(task['task_id'], approved_by='isolated-approver')
    assert task_engine.get_task(task['task_id']) == before


def test_cancel_cannot_win_over_concurrent_completion(task_engine, monkeypatch):
    task = task_engine.create_task('isolated concurrent completion')
    original_get = task_engine._db_get_task
    first = True
    def stale_read(task_id):
        nonlocal first
        value = original_get(task_id)
        if first:
            first = False
            task_engine._db_update_task(task_id, status='succeeded', result_json=json.dumps({'artifact_id': 'committed'}))
        return value
    monkeypatch.setattr(task_engine, '_db_get_task', stale_read)
    assert task_engine.cancel_task(task['task_id'])['status'] == 'succeeded'
    assert original_get(task['task_id'])['result']['artifact_id'] == 'committed'


def test_failed_generation_route_returns_unavailable_not_http_success(monkeypatch):
    import content_generation as generation
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(generation.content_bp)
    monkeypatch.setattr(generation, 'generate_content', lambda **kwargs: {
        'ok': False, 'meta': {'status': 'failed'}, 'evaluation': {'overall': None}})
    response = app.test_client().post('/api/content/generate', json={'content_type': 'ad_copy'})
    assert response.status_code == 503
    assert response.get_json()['ok'] is False


def test_source_keys_are_encoded_before_dynamic_html_interpolation():
    from lumenis.shared.reporting.kos import _html_display
    value = {'by_lifecycle': {'<img src=x onerror=alert(1)>': 1}}
    escaped = _html_display(value)
    assert list(escaped['by_lifecycle']) == ['&lt;img src=x onerror=alert(1)&gt;']
    assert list(value['by_lifecycle']) == ['<img src=x onerror=alert(1)>']
