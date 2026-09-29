from __future__ import annotations

import inspect

import pytest


def _registry_rows():
    return [
        {
            'subject_id': 'CTH-NORTH-1',
            'domain_id': 'CTH',
            'subject_type': 'company',
            'name_en': 'North Star Mall',
            'name_zh': '北辰商业',
            'keywords': ['North Star'],
            'status': 'configured',
        },
        {
            'subject_id': 'BMP-NORTH-1',
            'brand_focus_id': 'BRAND-NORTH-1',
            'domain_id': 'BMP',
            'subject_type': 'brand',
            'name_en': 'North Star Brand',
            'name_zh': '北辰品牌',
            'keywords': ['North Brand'],
            'status': 'configured',
        },
    ]


def test_global_plan_uses_registered_cth_and_bmp_entries_with_exact_scope():
    from lumenis.system.collector.acquisition_plan import build_acquisition_plan

    plan = build_acquisition_plan(registry_loader=_registry_rows, max_queries=32)

    assert plan.status == 'READY'
    assert plan.is_runnable is True
    assert plan.registry_counts == {'CTH': 1, 'BMP': 1}
    assert {query.domain_id for query in plan.queries} == {'CTH', 'BMP'}
    assert all(query.scope['global_scope'] is False for query in plan.queries)
    assert all(query.scope['domain_id'] in {'cth', 'zbmp'} for query in plan.queries)
    assert all(query.provenance['source'] == 'lumenis_subject_registry' for query in plan.queries)
    assert all('account' not in query.provenance for query in plan.queries)


def test_focus_prioritizes_selected_brand_but_keeps_background_queries():
    from lumenis.system.collector.acquisition_plan import build_acquisition_plan

    plan = build_acquisition_plan(
        context_mode='FOCUS',
        domain_id='BMP',
        # Compatibility Subject id is resolved to the canonical BrandFocus.
        subject_id='BMP-NORTH-1',
        registry_loader=_registry_rows,
    )

    assert plan.status == 'READY'
    assert plan.focus_scope == {
        'domain_id': 'zbmp',
        'product_id': 'ZBMP',
        'subject_id': None,
        'brand_focus_id': 'BRAND-NORTH-1',
        'scope_key': 'BRAND-NORTH-1',
    }
    selected = [query for query in plan.queries if query.brand_focus_id == 'BRAND-NORTH-1']
    background = [query for query in plan.queries if query.subject_id == 'CTH-NORTH-1']
    assert selected and all(query.priority == 0 for query in selected)
    assert background and all(query.priority == 10 for query in background)
    assert plan.to_dict()['background_collection_continues'] is True


def test_plan_deduplicates_and_bounds_queries():
    from lumenis.system.collector.acquisition_plan import build_acquisition_plan

    rows = _registry_rows()
    rows[0]['keywords'] = ['North Star', 'North Star', 'North Star Mall']
    plan = build_acquisition_plan(registry_loader=lambda: rows, max_queries=2)

    assert len(plan.queries) == 2
    assert plan.truncated is True
    assert len({(query.keyword.casefold(), query.domain_id, query.scope_key)
                for query in plan.queries}) == 2


def test_empty_registry_is_honestly_blocked_and_never_uses_a_subject_fallback():
    from lumenis.system.collector.acquisition_plan import build_acquisition_plan

    plan = build_acquisition_plan(registry_loader=lambda: [])

    assert plan.status == 'BLOCKED'
    assert plan.reason_code == 'REGISTRY_EMPTY'
    assert plan.is_runnable is False
    assert plan.queries == ()
    assert plan.keywords == ()


def test_explicit_keywords_require_registered_aliases_and_focus_aliases():
    from lumenis.system.collector.acquisition_plan import build_acquisition_plan

    registered = build_acquisition_plan(['North Star'], registry_loader=_registry_rows)
    assert registered.status == 'READY'
    assert {query.scope_key for query in registered.queries} == {'CTH-NORTH-1'}

    unknown = build_acquisition_plan(['unregistered phrase'], registry_loader=_registry_rows)
    assert unknown.status == 'BLOCKED'
    assert unknown.reason_code == 'KEYWORD_SCOPE_UNRESOLVED'

    focus_unknown = build_acquisition_plan(
        ['North Star'],
        context_mode='FOCUS',
        domain_id='BMP',
        brand_focus_id='BRAND-NORTH-1',
        registry_loader=_registry_rows,
    )
    assert focus_unknown.status == 'BLOCKED'
    assert focus_unknown.reason_code == 'KEYWORD_SCOPE_UNRESOLVED'


def test_legacy_default_symbols_are_non_authoritative_and_bridge_blocks_before_identity(monkeypatch):
    import collector
    import xhs_cookie_bridge as bridge
    from lumenis.system.collector.acquisition_plan import build_acquisition_plan

    assert collector.MONITOR_KEYWORDS is None
    assert bridge.DEFAULT_KEYWORDS is None
    assert '广州太古汇' not in inspect.getsource(
        __import__('lumenis.system.collector.acquisition_plan', fromlist=['*'])
    )

    blocked_plan = build_acquisition_plan(registry_loader=lambda: [])
    monkeypatch.setattr(bridge, '_resolve_acquisition_plan', lambda *args, **kwargs: blocked_plan)
    monkeypatch.setattr(bridge, 'collection_policy_gate', lambda *args, **kwargs: {'ok': True})
    for name in ('select_account', 'cookie_configured', 'get_identity_status'):
        monkeypatch.setattr(bridge, name, lambda *args, _name=name, **kwargs: (_ for _ in ()).throw(
            AssertionError(f'{_name} reached before acquisition plan')))

    result = bridge.sync(keywords=None)

    assert result['task_state'] == 'BLOCKED'
    assert result['query_plan']['reason_code'] == 'REGISTRY_EMPTY'


def test_collector_none_blocks_before_guard_or_search(monkeypatch):
    import collector

    class _Policy:
        human_cadence = {'status': 'NOT_VERIFIED'}
        auto_run_enabled = False

        @staticmethod
        def can_run_kind(_kind):
            return True

    monkeypatch.setattr(collector, '_collection_policy_gate',
                        lambda **kwargs: {'ok': True, 'account': 'XHS_RETINAUT'})
    monkeypatch.setattr(collector._rednote_policy, 'effective_policy', lambda: _Policy())
    monkeypatch.setattr('subject_registry.list_subjects', lambda: [])
    monkeypatch.setattr(collector, '_get_xhs_guard',
                        lambda: (_ for _ in ()).throw(AssertionError('guard reached')))
    monkeypatch.setattr(collector, 'search_xiaohongshu',
                        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('search reached')))

    notes, results = collector.collect_all(keywords=None)

    assert notes == []
    assert results[0]['error'] == 'ACQUISITION_PLAN_BLOCKED'
    assert results[0]['plan_reason_code'] == 'REGISTRY_EMPTY'


def test_automation_empty_registry_blocks_before_runtime_preflight(monkeypatch):
    import collector_automation
    import xhs_cookie_bridge as bridge

    monkeypatch.setattr('subject_registry.list_subjects', lambda: [])
    monkeypatch.setattr(bridge, 'runtime_preflight_check',
                        lambda *args, **kwargs: (_ for _ in ()).throw(
                            AssertionError('runtime preflight reached')))
    automation = collector_automation.CollectorAutomation()

    result = automation.start_collection(keywords=None, force=True)

    assert result['ok'] is False
    assert result['query_plan']['reason_code'] == 'REGISTRY_EMPTY'


def test_create_task_blocks_before_account_selection_when_plan_is_empty(monkeypatch):
    import xhs_cookie_bridge as bridge
    from lumenis.system.collector.acquisition_plan import build_acquisition_plan

    blocked_plan = build_acquisition_plan(registry_loader=lambda: [])
    monkeypatch.setattr(bridge, 'collection_policy_gate',
                        lambda *args, **kwargs: {'ok': True})
    monkeypatch.setattr(bridge, '_resolve_acquisition_plan', lambda *args, **kwargs: blocked_plan)
    monkeypatch.setattr(bridge, 'select_account',
                        lambda *args, **kwargs: (_ for _ in ()).throw(
                            AssertionError('account selection reached')))

    with pytest.raises(RuntimeError, match='采集计划未就绪'):
        bridge.create_task(keywords=None)


def test_live_engine_empty_registry_blocks_before_cdp_resolution(monkeypatch):
    import xhs_cookie_bridge as bridge
    from lumenis.system.collector.runtime.xhs import live_engine

    monkeypatch.setattr(bridge, 'collection_policy_gate',
                        lambda *args, **kwargs: {'ok': True, 'account': 'XHS_RETINAUT'})
    monkeypatch.setattr('subject_registry.list_subjects', lambda: [])
    monkeypatch.setattr(bridge, 'cdp_url_for',
                        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('CDP resolved')))
    monkeypatch.setattr(live_engine.subprocess, 'run',
                        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('process reached')))
    monkeypatch.setattr(live_engine.Path, 'mkdir',
                        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('persistence reached')))

    result = live_engine.run_live('unregistered phrase', account='XHS_RETINAUT')

    assert result['code'] == 'ACQUISITION_PLAN_BLOCKED'
    assert result['query_plan']['reason_code'] == 'REGISTRY_EMPTY'
