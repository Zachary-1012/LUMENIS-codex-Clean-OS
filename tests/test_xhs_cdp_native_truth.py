"""Native browser observations and interrupted Raw recovery; no live identity."""
import ast
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace

import pytest
import xhs_cdp_collector as worker

ROOT = Path(__file__).resolve().parents[1]
_TEST_COLLECTION_USER_ID = 'synthetic-xhs-test-user'
_TEST_COLLECTION_IDENTITY_FINGERPRINT = hashlib.sha256(
    _TEST_COLLECTION_USER_ID.encode('utf-8')).hexdigest()


@pytest.mark.parametrize('target', [
    'https://www.xiaohongshu.com/explore/' + 'a' * 24,
    'https://www.rednote.com.evil.test/explore/' + 'a' * 24,
    'https://user@www.rednote.com/explore/' + 'a' * 24,
    'https://www.rednote.com:9222/explore/' + 'a' * 24,
    'https://www.rednote.com/explore/' + 'a' * 24 + '#other',
    None, 'not-a-note-id',
])
def test_independent_detail_rejects_other_identity_hosts_before_backend_load(target, monkeypatch):
    from lumenis.system.collector.adapters.xhs import XiaohongshuAdapter
    adapter = XiaohongshuAdapter()
    monkeypatch.setattr(adapter, '_load_backend', lambda: pytest.fail('invalid detail loaded backend'))
    assert adapter.detail(target).metadata['error_type'] == 'DETAIL_SOURCE_UNVERIFIED'


@pytest.mark.parametrize('identity', ['verified', 'wrong_note', 'unverified'])
def test_independent_detail_uses_existing_backend_and_requires_exact_verified_note(identity):
    from lumenis.system.collector.adapters.xhs import XiaohongshuAdapter
    calls = []
    note_id = 'a' * 24
    def read_detail(url, **kwargs):
        calls.append((url, kwargs))
        return {'notes': [{'note_id': 'b' * 24 if identity == 'wrong_note' else note_id,
                           'detail_fetched': True, 'detail_identity_verified': identity != 'unverified'}],
                'total': 1, 'identity_verified': True}
    adapter = XiaohongshuAdapter(backend=SimpleNamespace(detail_xiaohongshu=read_detail))
    result = adapter.detail(note_id, detail_media_mode='cover_only')
    assert len(calls) == 1 and calls[0][0] == 'https://www.rednote.com/explore/' + note_id
    assert calls[0][1]['region'] == 'intl' and calls[0][1]['account'] is None
    assert calls[0][1]['detail_media_mode'] == 'cover_only'
    assert result.ok is (identity == 'verified')
    if result.ok:
        assert result.metadata['acquisition_capability'] == 'detail'
    else:
        assert not result.items


def test_detail_locator_token_reaches_only_existing_private_worker_call():
    from lumenis.system.collector.adapters.xhs import XiaohongshuAdapter
    url = 'https://www.rednote.com/explore/' + 'a' * 24
    calls = []
    def read(reference, **kwargs):
        calls.append((reference, kwargs['source_url']))
        return {'identity_verified': True, 'notes': [{'note_id': 'a' * 24,
            'detail_fetched': True, 'detail_identity_verified': True}]}
    result = XiaohongshuAdapter(backend=SimpleNamespace(detail_xiaohongshu=read)).detail(url + '?xsec_token=synthetic-private-locator')
    assert result.ok and calls == [(url, url + '?xsec_token=synthetic-private-locator')]
    assert result.metadata['continuation']['keyword'] == url
    assert 'synthetic-private-locator' not in json.dumps(result.metadata)


def test_independent_detail_and_search_share_native_parser_and_only_close_owned_tab(monkeypatch):
    from playwright import sync_api
    from contextlib import nullcontext
    note_id = 'c' * 24
    url = 'https://www.rednote.com/explore/' + note_id
    native = {'detail_present': True, 'source_note_ids': [note_id], 'source_page_url': url,
              'title': 'Permitted fixture detail', 'desc': 'Complete fixture body',
              'time_raw': '2026-10-01T08:00:00Z', 'time_kind': 'publication',
              'time_locator': '.author-container .time',
              'engage': {'like_raw': '0'}, 'comment_list': [{'content': 'Fixture comment'}],
              'image_list': ['https://source.example/cover.png']}
    class Page:
        closed = False
        def __init__(self):
            self.url = url
        def evaluate(self, expression):
            assert expression == worker._DETAIL_JS
            return dict(native)
        def wait_for_selector(self, *args, **kwargs):
            pass
        def close(self):
            self.closed = True
    page = Page()
    calls = []
    monkeypatch.setattr(sync_api, 'sync_playwright', lambda: nullcontext(object()))
    def approved_context(playwright, endpoint):
        calls.append(endpoint)
        return object(), SimpleNamespace(new_page=lambda: page)
    monkeypatch.setattr(worker, '_connect_verified_collection_context', approved_context)
    monkeypatch.setattr(worker, 'robust_goto', lambda p, target: calls.append(target))
    monkeypatch.setattr(worker, '_risk_check', lambda *a: False)
    monkeypatch.setattr(worker, 'human_reading_profile', lambda: ('fixture', 0.5))
    monkeypatch.setattr(worker, 'human_consume_detail', lambda *a: {
        'video_watched': False, 'comments_seen': 1, 'images_swiped': 0, 'dwell_sec': 1})
    snapshots = []
    result = worker.collect(url, cdp_url='https://owned-worker.example', detail_url=url,
                            detail_media_mode='cover_only', progress=lambda value: snapshots.append(json.loads(json.dumps(value))))
    assert calls == ['https://owned-worker.example', url]
    assert result['ok'] and result['identity_verified'] and page.closed
    assert snapshots[0]['summary']['pending_note_ids'] == [note_id]
    assert snapshots[-1]['summary']['pending_note_ids'] == []
    note = result['notes'][0]
    assert note['likes'] == 0 and note['comments'] is None and note['shares'] is None
    assert note['desc'] == native['desc'] and note['detail_identity_verified']
    assert note['comment_list'] == native['comment_list']
    assert note['image_list'] == native['image_list']
    assert note['publish_time'] == native['time_raw']


def collector_functions():
    """Execute the real functions without collector's runtime/DB import effects."""
    tree = ast.parse((ROOT / 'collector.py').read_text('utf-8'))
    selected = [node for node in tree.body
                if (isinstance(node, ast.FunctionDef)
                    and node.name in {'_norm_cdp_note', '_search_via_cdp'})
                or (isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name)
                            and target.id == '_XHS_MAX_WORKER_CHUNK_SECONDS'
                            for target in node.targets))]
    namespace = {'re': re, 'datetime': datetime, 'hashlib': hashlib, 'subprocess': subprocess,
                 'os': os, 'sys': sys, 'json': json, 'SCRIPT_DIR': str(ROOT),
                 'CDP_SCRIPT': str(ROOT / 'xhs_cdp_collector.py'),
                 '_resolve_server_cdp_url': lambda *a, **k: ('https://worker.example', ''),
                 '_collection_env': lambda **k: dict(os.environ)}
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(ROOT / 'collector.py'), 'exec'), namespace)
    return SimpleNamespace(**namespace)


@pytest.mark.parametrize('value', [None, '', 'unknown', True, False, -1, '-1', 'not 12', '12+', '1.5', float('nan')])
def test_unknown_or_invalid_metric_never_becomes_zero(value):
    assert worker.parse_count(value) is None
    assert collector_functions()._norm_cdp_note({'likes': value})['likes'] is None


@pytest.mark.parametrize(('value', 'expected'), [('0', 0), (0, 0), ('1,234', 1234), ('1.2万', 12000), ('2.5k', 2500)])
def test_labeled_display_metric_preserves_zero_and_units(value, expected):
    assert worker.parse_count(value) == expected


def test_human_search_submits_only_after_exact_field_readback(monkeypatch):
    calls = []

    class SearchBox:
        value = ""
        def fill(self, value, timeout):
            calls.append(("fill", value, timeout))
            self.value = value
        def input_value(self, timeout):
            calls.append(("read", timeout))
            return self.value
        def press(self, key, timeout):
            calls.append(("press", key, timeout))

    monkeypatch.setattr(worker, "_find_first", lambda *args, **kwargs: SearchBox())
    monkeypatch.setattr(worker, "log", lambda *_args, **_kwargs: None)
    worker.human_search_keyword(object(), "品牌活动")
    assert calls == [("fill", "品牌活动", 6000), ("read", 6000), ("press", "Enter", 6000)]


def test_human_search_does_not_submit_when_field_readback_differs(monkeypatch):
    class SearchBox:
        def fill(self, value, timeout):
            pass
        def input_value(self, timeout):
            return "wrong"
        def press(self, *_args, **_kwargs):
            raise AssertionError("query must not be submitted")

    monkeypatch.setattr(worker, "_find_first", lambda *args, **kwargs: SearchBox())
    with pytest.raises(RuntimeError, match="SEARCH_INPUT_VALUE_MISMATCH"):
        worker.human_search_keyword(object(), "品牌活动")


def test_xhs_search_diagnostics_bound_untrusted_counts_and_require_timestamp_zone():
    from lumenis.system.collector.adapters.xhs import XiaohongshuAdapter

    projected = XiaohongshuAdapter._safe_search_diagnostics({
        "version": "xhs-search-state-v1",
        "observations": [{
            "phase": "search_ready", "observed_at": "2026-10-22T10:00:00",
            "selector_counts": {"section.note-item": 1_000_001, "a.cover": 3},
            "note_link_count": 10**30, "body_character_count": 12,
            "loading_element_count": 0,
        }],
    })
    row = projected["observations"][0]
    assert "observed_at" not in row
    assert row["selector_counts"] == {
        "section.note-item": None, "a.cover": 3, ".feeds-container": None,
    }
    assert row["note_link_count"] is None
    assert row["body_character_count"] == 12


def test_zero_note_metrics_are_not_replaced_by_comment_likes():
    detail = {'engage': {'like_raw': '0', 'collect_raw': '0', 'comment_raw': '0'},
              'all_counts': ['17', '23', '88'], 'comment_list': [{'likes_raw': '88'}]}
    assert worker._detail_metrics(detail, {'likes_raw': '9'}) == {
        'likes': 0, 'collects': 0, 'comments': 0, 'shares': None}
    assert worker._detail_metrics({'all_counts': ['17', '23', '88']}, {}) == {
        'likes': None, 'collects': None, 'comments': None, 'shares': None}


def test_native_time_media_body_and_capture_survive_normalization():
    raw = {'note_id': 'n1', 'detail_publish_time': '2026-10-02T09:30:05+08:00',
           'time_raw': '2026-10-02T09:30:05+08:00', 'collected_at': '2026-10-03T01:00:00+00:00',
           'desc': '完整正文\n第二行', 'likes': None, 'collects': 0, 'comments': None, 'shares': None,
           'is_video': True, 'image_count': 2, 'image_list': ['https://source.example/image.jpg'],
           'video_list': [{'url': 'https://source.example/video.mp4'}], 'comment_list': [{'content': '公开评论'}]}
    normalized = collector_functions()._norm_cdp_note(raw)
    assert normalized['publish_time'] == raw['detail_publish_time']
    assert normalized['publish_date'] == '2026-10-02'
    assert normalized['captured_at'] == raw['collected_at']
    assert normalized['content'] == raw['desc']
    for key in ('time_raw', 'likes', 'collects', 'comments', 'shares', 'is_video',
                'image_count', 'image_list', 'video_list', 'comment_list'):
        assert normalized[key] == raw[key]


@pytest.mark.parametrize(('raw', 'expected'), [
    ('2026-10-02T09:30:05+08:00', '2026-10-02T09:30:05+08:00'),
    ('2026-10-02 09:30', '2026-10-02 09:30'), ('2026/10/2', '2026-10-02'),
    ('编辑于 2026-10-02', ''), ('10-02', ''), ('2026-13-99', ''), ('未知', '')])
def test_publication_keeps_precision_and_does_not_use_edit_or_ambiguous_date(raw, expected):
    assert worker.normalize_publish_time(raw) == expected


@pytest.mark.parametrize('card', [
    {'time_raw': '2025-11-30'},
    {'time_raw': '2025-11-30', 'time_kind': 'publication'},
    {'time_raw': '2025-11-30', 'time_kind': 'unclassified', 'time_locator': '.time'},
])
def test_edit_detail_never_falls_back_to_unproven_card_publication(card):
    detail = {'time_raw': '编辑于2025-11-30', 'time_kind': 'publication', 'time_locator': '.author-container .time'}
    pub, observations, origin = worker._source_publication_time(detail, card)
    assert pub == '' and origin == 'unknown'
    assert observations[0]['kind'] == 'edit'
    assert observations[0]['raw'] == detail['time_raw']


def test_independent_native_publication_locator_can_coexist_with_edit_observation():
    detail = {'time_raw': '编辑于2026-10-02', 'time_kind': 'edit', 'time_locator': '.author-container .time'}
    card = {'time_raw': '2026-09-28T07:20:30+08:00', 'time_kind': 'publication',
            'time_locator': {'selector': '[itemprop="datePublished"]', 'note_id': 'n1'}}
    pub, observations, origin = worker._source_publication_time(detail, card)
    assert pub == card['time_raw'] and origin == 'card'
    normalized = collector_functions()._norm_cdp_note({'detail_publish_time': pub,
        'time_raw': detail['time_raw'], 'time_source_observations': observations,
        'publication_time_source': origin, 'collected_at': '2026-10-03T01:00:00Z'})
    assert normalized['time_source_observations'] == observations
    assert normalized['captured_at'] == '2026-10-03T01:00:00Z'
    assert normalized['publish_time'] == card['time_raw']


def test_normalizer_rejects_stale_publication_with_explicit_unknown_provenance():
    normalized = collector_functions()._norm_cdp_note({'publish_time': '2025-11-30',
        'publication_time_source': 'unknown', 'time_source_observations': [
            {'origin': 'detail', 'kind': 'edit', 'raw': '编辑于2025-11-30', 'locator': '.time'}]})
    assert normalized['publish_time'] == '' and normalized['publish_date'] == ''


def test_native_time_javascript_carries_kind_locator_and_excludes_other_notes():
    assert '...observedTime' in worker._LIST_JS and '...observedTime' in worker._DETAIL_JS
    assert 'datePublished' in worker._LIST_JS and 'datePublished' in worker._DETAIL_JS
    assert 'time_locator' in worker._LIST_JS and 'time_locator' in worker._DETAIL_JS
    assert "e.closest('section.note-item,.comment-item,.parent-comment" in worker._DETAIL_JS


def test_atomic_checkpoint_retains_full_previous_observation_on_write_failure(tmp_path, monkeypatch):
    output = tmp_path / 'raw.json'
    initial = {'keyword': 'query', 'ok': False, 'notes': [{'note_id': 'n1', 'desc': 'saved body'}], 'summary': {}}
    worker._write_checkpoint(str(output), initial, 'run1')
    previous = output.read_bytes()
    monkeypatch.setattr(worker.os, 'replace', lambda *a: (_ for _ in ()).throw(OSError('fixture failure')))
    with pytest.raises(worker.RawCheckpointError):
        worker._write_checkpoint(str(output), {**initial, 'notes': []}, 'run1')
    assert output.read_bytes() == previous
    assert not list(tmp_path.glob('.xhs-raw-*'))


@pytest.mark.parametrize('mismatch', [None, 'run_id', 'keyword', 'source_host', 'missing', 'invalid'])
def test_parent_timeout_recovers_only_exact_current_checkpoint(tmp_path, monkeypatch, mismatch):
    monkeypatch.setenv('XHS_EXPECTED_COLLECTION_USER_ID', _TEST_COLLECTION_USER_ID)
    output = tmp_path / 'raw.json'

    def timed_out(command, **kwargs):
        run_id = command[command.index('--run-id') + 1]
        raw = {'keyword': 'query', 'identity_verified': True, 'ok': False,
               'notes': [{'note_id': 'n1', 'desc': 'saved body', 'likes': None, 'collected_at': '2026-10-03T01:00:00Z'}],
               'summary': {}, 'checkpoint': {'run_id': run_id, 'source_host': 'www.rednote.com',
                   'verified_identity_fingerprint': _TEST_COLLECTION_IDENTITY_FINGERPRINT}}
        if mismatch == 'run_id':
            raw['checkpoint']['run_id'] = 'old invocation'
        if mismatch == 'keyword':
            raw['keyword'] = 'another query'
        if mismatch == 'source_host':
            raw['checkpoint']['source_host'] = 'another.example'
        if mismatch == 'invalid':
            output.write_text('{', encoding='utf-8')
        elif mismatch != 'missing':
            output.write_text(json.dumps(raw), encoding='utf-8')
        raise subprocess.TimeoutExpired(command, kwargs['timeout'])

    monkeypatch.setattr(subprocess, 'run', timed_out)
    result = collector_functions()._search_via_cdp('query', 3, str(output))
    assert result['ok'] is False
    if mismatch is None:
        assert result['notes'][0]['content'] == 'saved body'
        assert result['notes'][0]['likes'] is None
        assert result['notes'][0]['captured_at'] == '2026-10-03T01:00:00Z'
        assert result['error'] == 'CDP_TIMEOUT_PARTIAL'
        assert result['partial'] is True
    else:
        assert result['notes'] == []
        assert result['error'] == 'CDP_TIMEOUT_NO_CHECKPOINT'


def test_risk_status_takes_precedence_over_partial_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv('XHS_EXPECTED_COLLECTION_USER_ID', _TEST_COLLECTION_USER_ID)
    output = tmp_path / 'raw.json'
    def timed_out(command, **kwargs):
        run_id = command[command.index('--run-id') + 1]
        output.write_text(json.dumps({'keyword': 'query', 'identity_verified': True,
            'ok': False, 'notes': [],
            'summary': {'verification_required': True},
            'checkpoint': {'run_id': run_id, 'source_host': 'www.rednote.com',
                'verified_identity_fingerprint': _TEST_COLLECTION_IDENTITY_FINGERPRINT}}), encoding='utf-8')
        raise subprocess.TimeoutExpired(command, kwargs['timeout'])
    monkeypatch.setattr(subprocess, 'run', timed_out)
    assert collector_functions()._search_via_cdp('query', 3, str(output))['error'] == 'NEED_VERIFY'


def test_worker_exception_reopens_saved_body_instead_of_emptying_raw(tmp_path, monkeypatch, capsys):
    output = tmp_path / 'raw.json'
    def interrupted(keyword, max_scroll, max_details, cdp_url, human, progress, deadline, resume_ids,
                    resume_cards=None, budget_kind='worker_chunk', detail_media_mode='legacy'):
        assert budget_kind == 'worker_chunk'
        assert detail_media_mode == 'legacy'
        progress({'keyword': keyword, 'ok': False, 'notes': [{'note_id': 'n1', 'desc': 'full body'}], 'summary': {}})
        raise RuntimeError('COLLECTOR_IDENTITY_MISMATCH')
    monkeypatch.setattr(worker, 'collect', interrupted)
    monkeypatch.setattr(sys, 'argv', ['worker', '--keyword', 'query', '--output', str(output), '--run-id', 'run1'])
    with pytest.raises(SystemExit) as stopped:
        worker.main()
    assert stopped.value.code == 1
    raw = json.loads(output.read_text('utf-8'))
    assert raw['notes'][0]['desc'] == 'full body'
    assert raw['ok'] is False
    assert raw['checkpoint']['complete'] is False
    assert raw['error'] == 'CDP_EXCEPTION: COLLECTOR_IDENTITY_MISMATCH'


def test_time_budget_preserves_collected_body_and_explicit_partial_state():
    result = {'ok': True, 'notes': [{'note_id': 'n1', 'desc': 'saved'}], 'summary': {}}
    assert worker._budget_reached(result, 0, budget_kind='time_budget') is True
    assert result['notes'][0]['desc'] == 'saved'
    assert result['partial'] is True
    assert result['ok'] is False
    assert result['error'] == 'CDP_TIME_BUDGET_PARTIAL'


def test_resume_skips_only_successful_details_for_exact_identity_and_keyword(tmp_path, monkeypatch):
    monkeypatch.setenv('XHS_EXPECTED_COLLECTION_USER_ID', 'a' * 24)
    output = tmp_path / 'raw.json'
    raw = {'keyword': 'query', 'identity_verified': True, 'ok': False, 'summary': {'resumed_note_ids': ['older']},
           'notes': [{'note_id': 'n1', 'detail_fetched': True}, {'note_id': 'n2', 'detail_fetched': False}]}
    worker._write_checkpoint(str(output), raw, 'previous')
    assert worker._resume_note_ids(str(output), 'query') == {'n1', 'older'}
    with pytest.raises(RuntimeError, match='RESUME_INPUT_MISMATCH'):
        worker._resume_note_ids(str(output), 'another keyword')
    monkeypatch.setenv('XHS_EXPECTED_COLLECTION_USER_ID', 'b' * 24)
    with pytest.raises(RuntimeError, match='RESUME_INPUT_MISMATCH'):
        worker._resume_note_ids(str(output), 'query')


def test_unverified_initial_checkpoint_cannot_supply_resume_ids(tmp_path, monkeypatch):
    monkeypatch.setenv('XHS_EXPECTED_COLLECTION_USER_ID', 'a' * 24)
    output = tmp_path / 'raw.json'
    worker._write_checkpoint(str(output), {'keyword': 'query', 'notes': [], 'summary': {}}, 'previous')
    with pytest.raises(RuntimeError, match='RESUME_INPUT_MISMATCH'):
        worker._resume_note_ids(str(output), 'query')


def test_pending_depth_stays_explicit_after_a_bounded_batch():
    raw = {'notes': [{'note_id': 'n1', 'detail_fetched': True}, {'note_id': 'n2', 'detail_fetched': False}],
           'summary': {'resumed_note_ids': ['older']},
           'discovered_cards': [{'note_id': 'n1'}, {'note_id': 'n2'}, {'note_id': 'n3'}, {'note_id': 'older'}]}
    worker._update_detail_progress(raw)
    assert raw['summary']['pending_note_ids'] == ['n2', 'n3']
    assert raw['summary']['pagination_exhausted'] is False


def test_unopened_feed_card_does_not_become_successful_detail(monkeypatch):
    card = {'note_id': 'n1', 'url': 'https://www.rednote.com/explore/n1', 'title': 'feed title', 'likes_raw': '12'}
    class Page:
        closed = False
        url = 'https://www.rednote.com/search_result?keyword=query'
        first = property(lambda self: self)
        mouse = SimpleNamespace(wheel=lambda *a: None)
        def goto(self, *a, **k):
            pass
        def wait_for_url(self, predicate, **kwargs):
            assert predicate(self.url)
        def locator(self, selector):
            assert selector == 'section.note-item'
            return self
        def wait_for(self, **kwargs):
            assert kwargs['state'] == 'visible'
        def wait_for_selector(self, selector, **k):
            if selector == 'section.note-item':
                return object()
            raise RuntimeError('no detail loaded')
        def evaluate(self, script, arg=None):
            if script == worker._SEARCH_STATE_JS:
                assert arg == 'query'
                return {'host_matches': True, 'route_is_search': True, 'query_matches': True,
                        'input_matches': True, 'document_ready_state': 'complete',
                        'selector_counts': {'section.note-item': 1, 'a.cover': 1, '.feeds-container': 1},
                        'note_link_count': 1, 'body_character_count': 200,
                        'native_empty_indicators': [], 'loading_element_count': 0}
            if script == worker._LIST_JS:
                return [card]
            if script == worker._DETAIL_JS:
                return {'detail_present': False, 'desc': '', 'engage': {}}
            return 'public search results with loaded native feed cards'
        def close(self):
            self.closed = True
    page = Page()
    class Runtime:
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
    monkeypatch.setattr('playwright.sync_api.sync_playwright', lambda: Runtime())
    monkeypatch.setattr(worker, '_connect_verified_collection_context', lambda *a: (object(), SimpleNamespace(new_page=lambda: page)))
    monkeypatch.setattr(worker, 'human_sleep', lambda *a: None)
    result = worker.collect_direct('query', max_scroll=0, max_details=1, cdp_url='fixture-only')
    assert result['ok'] is False
    assert result['notes'][0]['detail_fetched'] is False
    assert result['notes'][0]['desc'] == ''
    assert result['notes'][0]['collects'] is None
    assert result['error'] == 'NO_DETAIL'
    assert page.closed is True


def test_resume_never_overwrites_its_input_artifact(tmp_path, monkeypatch):
    output = tmp_path / 'raw.json'
    output.write_text('preserved prior Raw', encoding='utf-8')
    previous = output.read_bytes()
    monkeypatch.setattr(sys, 'argv', ['worker', '--keyword', 'query', '--output', str(output), '--resume-from', str(output)])
    with pytest.raises(SystemExit) as stopped:
        worker.main()
    assert stopped.value.code == 2
    assert output.read_bytes() == previous


def test_completed_resume_replays_terminal_result_without_collect_or_receipt_change(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setenv('XHS_EXPECTED_COLLECTION_USER_ID', 'a' * 24)
    resume_from = tmp_path / 'completed.json'
    output = tmp_path / 'replayed.json'
    worker._write_checkpoint(str(resume_from), {
        'keyword': 'query', 'identity_verified': True, 'ok': True, 'partial': False,
        'elapsed': 3.5, 'notes': [{'note_id': 'b' * 24, 'detail_fetched': True, 'desc': 'saved result'}],
        'summary': {'detail_success': 1, 'detail_total': 1},
    }, 'original-run', complete=True)
    terminal_result = json.loads(resume_from.read_text('utf-8'))
    original_receipt = dict(terminal_result['checkpoint'])
    original_bytes = resume_from.read_bytes()
    collect_calls = []

    def unexpected_collect(*args, **kwargs):
        collect_calls.append((args, kwargs))
        return {'keyword': 'query', 'ok': True, 'partial': False, 'notes': [], 'summary': {}}

    monkeypatch.setattr(worker, 'collect', unexpected_collect)
    monkeypatch.setattr(sys, 'argv', [
        'worker', '--keyword', 'query', '--output', str(output),
        '--resume-from', str(resume_from), '--run-id', 'new-run',
    ])

    with pytest.raises(SystemExit) as stopped:
        worker.main()

    assert stopped.value.code == 0
    assert collect_calls == []
    replayed = json.loads(output.read_text('utf-8'))
    printed = json.loads(capsys.readouterr().out.split('---RESULT_JSON---\n', 1)[1])
    assert replayed == terminal_result
    assert printed == terminal_result
    assert replayed['checkpoint'] == original_receipt
    assert resume_from.read_bytes() == original_bytes


def test_partial_resume_preserves_pending_native_card_and_completed_ids(
        tmp_path, monkeypatch):
    monkeypatch.setenv('XHS_EXPECTED_COLLECTION_USER_ID', 'a' * 24)
    resume_from = tmp_path / 'partial.json'
    output = tmp_path / 'continued.json'
    completed_id = 'b' * 24
    pending_id = 'c' * 24
    pending_card = {
        'note_id': pending_id,
        'url': f'https://{worker.COLLECTION_HOST}/explore/{pending_id}',
        'title': 'pending native card',
    }
    worker._write_checkpoint(str(resume_from), {
        'keyword': 'query', 'identity_verified': True, 'ok': False, 'partial': True,
        'notes': [
            {'note_id': completed_id, 'detail_fetched': True},
            {**pending_card, 'detail_fetched': False},
        ],
        'discovered_cards': [pending_card],
        'summary': {'pending_note_ids': [pending_id], 'resumed_note_ids': ['d' * 24]},
    }, 'partial-run', complete=False)
    original_receipt = json.loads(resume_from.read_text('utf-8'))['checkpoint']
    original_bytes = resume_from.read_bytes()
    calls = []

    def fake_collect(keyword, max_scroll, max_details, cdp_url, human, progress,
                     deadline, resume_ids, resume_cards=None, budget_kind='worker_chunk',
                     detail_media_mode='legacy'):
        calls.append({
            'keyword': keyword,
            'resume_ids': set(resume_ids),
            'resume_cards': resume_cards,
            'budget_kind': budget_kind,
            'detail_media_mode': detail_media_mode,
        })
        return {
            'keyword': keyword, 'identity_verified': True, 'ok': True, 'partial': False,
            'notes': [{'note_id': pending_id, 'detail_fetched': True}], 'summary': {},
        }

    monkeypatch.setattr(worker, 'collect', fake_collect)
    monkeypatch.setattr(sys, 'argv', [
        'worker', '--keyword', 'query', '--output', str(output),
        '--resume-from', str(resume_from), '--run-id', 'continued-run',
    ])

    with pytest.raises(SystemExit) as stopped:
        worker.main()

    assert stopped.value.code == 0
    assert calls == [{
        'keyword': 'query',
        'resume_ids': {completed_id, 'd' * 24},
        'resume_cards': [pending_card],
        'budget_kind': 'worker_chunk',
        'detail_media_mode': 'legacy',
    }]
    assert json.loads(resume_from.read_text('utf-8'))['checkpoint'] == original_receipt
    assert resume_from.read_bytes() == original_bytes


def test_completed_resume_rejects_mismatched_identity_before_collect(
        tmp_path, monkeypatch, capsys):
    monkeypatch.setenv('XHS_EXPECTED_COLLECTION_USER_ID', 'a' * 24)
    resume_from = tmp_path / 'completed.json'
    output = tmp_path / 'rejected.json'
    worker._write_checkpoint(str(resume_from), {
        'keyword': 'query', 'identity_verified': True, 'ok': True, 'partial': False,
        'notes': [{'note_id': 'b' * 24, 'detail_fetched': True}], 'summary': {},
    }, 'original-run', complete=True)
    original_bytes = resume_from.read_bytes()
    monkeypatch.setenv('XHS_EXPECTED_COLLECTION_USER_ID', 'c' * 24)
    collect_calls = []
    monkeypatch.setattr(worker, 'collect', lambda *args, **kwargs: collect_calls.append((args, kwargs)))
    monkeypatch.setattr(sys, 'argv', [
        'worker', '--keyword', 'query', '--output', str(output),
        '--resume-from', str(resume_from), '--run-id', 'new-run',
    ])

    with pytest.raises(SystemExit) as stopped:
        worker.main()

    assert stopped.value.code == 1
    assert collect_calls == []
    result = json.loads(output.read_text('utf-8'))
    assert result['error'] == 'CDP_EXCEPTION: RESUME_INPUT_MISMATCH'
    assert result['partial'] is True
    assert resume_from.read_bytes() == original_bytes
    assert 'CDP_EXCEPTION: RESUME_INPUT_MISMATCH' in capsys.readouterr().out
