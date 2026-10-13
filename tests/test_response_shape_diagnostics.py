"""Offline injected-response regressions, not live collection or Evidence acceptance."""
from copy import deepcopy
from dataclasses import asdict
import json
from types import SimpleNamespace

import pytest

from lumenis.adapters.base import AdapterResult
from lumenis.system.collector.adapters import response_shape as shapes
from lumenis.system.collector.adapters.douyin import DouyinAdapter as SystemAdapter
from tests.test_douyin_search_capture_page import _Page, _Worker


def _partial_search_bag():
    # Synthetic response shared by main and local-candidate verification.
    return {'status_code': 0, 'data': [{'aweme_info': {
        'aweme_id': 'partial-aweme', 'desc': 'Already observed search caption',
        'create_time': 1789171200, 'statistics': {'digg_count': 0}}}]}



def observation(value):
    observer = shapes.SearchShapeDiagnostics()
    observer.response_observed()
    observer.observe_json(value)
    return observer.snapshot()


def run_search(monkeypatch, *, bag=None, state='SUCCESS', stream=False,
               no_response=False, malformed=False, observer_failure=False):
    from lumenis.adapters import douyin
    page = _Page()
    reads = []
    original = deepcopy(bag)

    def read():
        assert page.request_finished
        reads.append('text' if stream else 'json')
        if malformed:
            raise ValueError('PRIVATE_SECRET_BODY')
        return json.dumps(bag) if stream else bag

    if not no_response:
        page.request = SimpleNamespace(
            url='https://www.douyin.com/aweme/v1/web/general/search/' + ('stream/' if stream else 'single/'),
            resource_type='xhr', response=lambda: SimpleNamespace(json=read, text=read))
    worker = _Worker(page, states=[state])
    monkeypatch.setattr(douyin, '_new_browser_worker', lambda: worker)
    monkeypatch.setattr(douyin, 'inject_into_context', lambda *_args: 0)
    monkeypatch.setattr(douyin.DouyinAdapter, '_parse_dom', lambda *_args: [])
    if observer_failure:
        monkeypatch.setattr(shapes, 'summarize', lambda *_a, **_k: (_ for _ in ()).throw(ValueError('PRIVATE_SECRET_BODY')))
    result = douyin.DouyinAdapter().search('approved synthetic query', max_results=1)
    assert bag == original
    assert page.closed and worker.closed
    assert reads == ([] if no_response else ['text' if stream else 'json'])
    assert shapes.validate_acquisition_diagnostics(result.diagnostics) == result.diagnostics
    return result


def test_adapter_result_positional_compatibility_and_independent_defaults():
    result = AdapterResult(True, [], '', 0, 0.5)
    assert result.diagnostics == {} and result.duration_seconds == 0.5
    other = AdapterResult(False)
    result.diagnostics['marker'] = 1
    assert other.diagnostics == {}


@pytest.mark.parametrize('stream', [False, True])
def test_same_response_once_notes_native_metrics_and_source_unchanged(monkeypatch, stream):
    bag = _partial_search_bag()
    result = run_search(monkeypatch, bag=bag, stream=stream)
    assert result.success and result.raw_count == len(result.notes) == 1
    assert result.notes[0].likes == 0 and result.notes[0].comments is None
    assert result.notes[0].raw_data['aweme_id'] == 'partial-aweme'
    assert 'diagnostics' not in result.notes[0].raw_data
    assert result.diagnostics['counters'] == {
        'matching_responses_observed': 1, 'json_objects_observed': 1,
        'parse_failures': 0, 'shape_samples': 1}
    old = deepcopy(result)
    old.diagnostics = {}
    calls = []
    def upper(item):
        def detail(**kw):
            calls.append(kw)
            return item
        return SystemAdapter(backend=SimpleNamespace(search=lambda *_a, **_k: item, detail=detail)).search('query')
    prior, current = upper(old), upper(result)
    assert len(calls) == 2
    new_metadata = current.metadata.pop('acquisition_diagnostics')
    assert new_metadata == result.diagnostics
    assert asdict(current) == asdict(prior)


@pytest.mark.parametrize(('no_response', 'malformed', 'state', 'success', 'parse_count'), [
    (True, False, 'SUCCESS', False, 0),
    (False, True, 'SUCCESS', False, 1),
    (False, False, 'EMPTY', True, 0),
    (False, False, 'CAPTCHA', False, 0),
    (False, False, 'AUTH_FAILED', False, 0),
    (False, False, 'BLOCKED', False, 0),
    (False, False, 'NETWORK_ERROR', False, 0),
])
def test_empty_missing_parse_failure_and_risk_paths_remain_distinct(
        monkeypatch, no_response, malformed, state, success, parse_count):
    result = run_search(monkeypatch, bag={'status_code': 0, 'data': []},
                        no_response=no_response, malformed=malformed, state=state)
    assert result.success is success and result.raw_count == 0
    assert result.diagnostics['counters']['parse_failures'] == parse_count
    assert result.diagnostics['counters']['json_objects_observed'] == int(not no_response and not malformed)
    assert 'PRIVATE_SECRET_BODY' not in json.dumps(result.diagnostics)


def test_observer_failure_does_not_change_success(monkeypatch):
    result = run_search(monkeypatch, bag=_partial_search_bag(), observer_failure=True)
    assert result.success and result.raw_count == 1
    assert result.diagnostics['status'] == 'DIAGNOSTIC_UNAVAILABLE'
    assert 'PRIVATE_SECRET_BODY' not in json.dumps(result.diagnostics)


def test_limits_eight_objects_four_shapes_and_64k(monkeypatch):
    calls = []
    original = shapes.summarize
    def counted(value, *args, **kwargs):
        calls.append(value)
        return original(value, *args, **kwargs)
    monkeypatch.setattr(shapes, 'summarize', counted)
    observer = shapes.SearchShapeDiagnostics()
    values = [None, False, 0, 1.2, 'secret', [], {}, {'data': []}, {'data': 2}]
    for _ in range(3):
        for value in values:
            observer.response_observed()
            observer.observe_json(value)
    output = observer.snapshot()
    assert len(calls) == 8 and len(output['shape_samples']) == 4
    assert output['status'] == 'LIMIT_REACHED'
    assert len(json.dumps(output, ensure_ascii=True).encode('ascii')) <= 65536
    assert shapes.validate_acquisition_diagnostics(output) == output


def test_total_size_limit_and_depth_truncation():
    node = None
    for _ in range(9):
        node = {k: node for k in sorted(shapes.DEFAULT_KEYS)}
    output = observation(node)
    assert output['status'] == 'LIMIT_REACHED'
    assert len(json.dumps(output, ensure_ascii=True).encode('ascii')) <= 65536
    assert shapes.validate_acquisition_diagnostics(output) == output


def test_scalar_privacy_mixed_types_cycles_and_allowlist():
    bag = {'data': [None, 0, False, {'desc': 'PRIVATE_SECRET_BODY',
        'password': {'value': 'PRIVATE_SECRET_BODY'}, 'header': 'PRIVATE_SECRET_BODY',
        'cursor': 'PRIVATE_SECRET_BODY', 'PRIVATE_KEY_VALUE': 'PRIVATE_SECRET_BODY'}]}
    output = observation(bag)
    serialized = json.dumps(output)
    assert 'PRIVATE_' not in serialized and 'password' not in serialized and 'header' not in serialized
    assert output['shape_samples'][0]['paths']['/data/[]'] == ['boolean', 'integer', 'null', 'object']
    assert output['pagination_state'] == 'HINT_ONLY_NO_FETCH'
    cycle = []; cycle.append(cycle)
    cycle_output = observation(cycle)
    assert cycle_output['status'] == 'LIMIT_REACHED'
    assert 'CYCLE' in cycle_output['shape_samples'][0]['limits_hit']


@pytest.mark.parametrize('mutation', [
    lambda d: d.update(body='PRIVATE_SECRET_BODY'),
    lambda d: d.update(schema='different'),
    lambda d: d.update(values_included=True),
    lambda d: d['counters'].update(parse_failures=True),
    lambda d: d['shape_samples'][0].update(shape_sha256='0'*64),
    lambda d: d['shape_samples'][0]['paths'].update({'/PRIVATE_SECRET_BODY': ['string']}),
    lambda d: d['shape_samples'][0].update(extra='PRIVATE_SECRET_BODY'),
    lambda d: d.update(shape_samples=[d['shape_samples'][0]]*5),
])
def test_upper_validation_rejects_forged_or_oversize_fields(mutation):
    value = observation({'data': []})
    mutation(value)
    assert shapes.validate_acquisition_diagnostics(value) == {}
    backend = SimpleNamespace(search=lambda *_a, **_k: AdapterResult(True, diagnostics=value))
    result = SystemAdapter(backend=backend).search('query')
    assert result.status.value == 'NO_NEW_DATA'
    assert 'acquisition_diagnostics' not in result.metadata


def test_custom_primitive_subclasses_are_rejected_without_leaking_values():
    class FakeString(str):
        def __eq__(self, other):
            return True
        def __ne__(self, other):
            return False
        __hash__ = str.__hash__
    value = observation({'data': []})
    value['schema'] = FakeString('PRIVATE_SECRET_BODY')
    assert shapes.validate_acquisition_diagnostics(value) == {}
    value = observation({'data': []})
    value['shape_samples'][0]['classification'] = FakeString('PRIVATE_SECRET_BODY')
    assert shapes.validate_acquisition_diagnostics(value) == {}


def test_invocation_isolation_and_snapshot_detachment():
    one, two = shapes.SearchShapeDiagnostics(), shapes.SearchShapeDiagnostics()
    one.response_observed(); one.observe_json({'data': []})
    first = one.snapshot(); first['counters']['parse_failures'] = 99
    assert one.snapshot()['counters']['parse_failures'] == 0
    assert two.snapshot()['status'] == 'NOT_OBSERVED'
    assert two.snapshot()['shape_samples'] == []


def test_old_backend_object_without_new_field_keeps_existing_contract():
    backend = SimpleNamespace(search=lambda *_a, **_k: SimpleNamespace(
        success=True, notes=[], error='', raw_count=0, duration_seconds=0))
    result = SystemAdapter(backend=backend).search('query')
    assert result.status.value == 'NO_NEW_DATA'
    assert 'acquisition_diagnostics' not in result.metadata


def test_raising_optional_diagnostic_property_does_not_change_business_success():
    class OldBackendResult:
        success = True
        notes = []
        error = ''
        raw_count = 0
        duration_seconds = 0

        @property
        def diagnostics(self):
            raise ValueError('PRIVATE_SECRET_BODY')

    result = SystemAdapter(backend=SimpleNamespace(
        search=lambda *_a, **_k: OldBackendResult())).search('query')
    assert result.status.value == 'NO_NEW_DATA'
    assert 'acquisition_diagnostics' not in result.metadata
