"""F03: actual signed Collector consumer, synthetic engine only, no network."""
import sqlite3
from tests.test_collector_transaction_truth import collector_case, REGISTERED_NAME
from tests.test_purpose_collector_integration import _setup, isolated_business_task_store
from tests.test_instagram_main_adapter import _make_engine, _native_note
from lumenis.adapters.base import AdapterResult
from lumenis.system.collector.adapters.instagram import InstagramAdapter
from lumenis.system.collector.adapters.base import CollectionResult, CollectionStatus
from lumenis.system.collector.adapters.scheduling.prelaunch_baseline import run_due_prelaunch_baseline
from lumenis.system.collector.adapters.scheduling.store import ScheduleDecisionStore


def test_detail_failure_observations_read_back_from_actual_collector_evidence(collector_case, tmp_path, monkeypatch):
    case = collector_case
    path, *_ = _setup(case, tmp_path, monkeypatch, 'instagram')
    note = _native_note('SYNTHETIC1', content=REGISTERED_NAME + ' service opening information')
    engine = _make_engine(AdapterResult(success=True, notes=[note], raw_count=1))
    engine.detail.side_effect = TimeoutError('synthetic transport timeout')
    adapter = InstagramAdapter(engine=engine)
    monkeypatch.setattr(adapter, 'health_check', lambda **kw: CollectionResult(CollectionStatus.SUCCESS, 'instagram'))
    monkeypatch.setattr(case['surface'], '_get_runtime_adapter', lambda _: adapter)
    result = run_due_prelaunch_baseline(config_path=str(path),
        store=ScheduleDecisionStore(str(tmp_path / 'schedule.db')))
    actual = next(r['result'] for r in result['runs'] if r.get('result'))
    assert actual['ok'] is False, actual
    assert actual['returned_count'] == 1, actual
    assert actual['evidence_recorded'] is True, actual
    assert actual['refresh_verified'] is False
    # Independent DB connection reads the persisted observation, not adapter memory.
    with sqlite3.connect(case['db_path']) as conn:
        rows = conn.execute('SELECT inputs_json, outputs_json FROM app_evidence_records').fetchall()
        persisted = '\n'.join(value or '' for row in rows for value in row)
        assert 'SYNTHETIC1' in persisted
        assert 'search_summary_observation' in persisted
        assert REGISTERED_NAME in persisted
        assert 'PROVIDER_UNAVAILABLE' in persisted
        assert conn.execute('SELECT COUNT(*) FROM canonical_data').fetchone()[0] == 0
