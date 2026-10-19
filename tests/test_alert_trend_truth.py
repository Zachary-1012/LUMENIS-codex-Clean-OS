"""G145: no invented default; authenticated source read is not alert approval."""
from copy import deepcopy
from datetime import date, timedelta
import sqlite3
import pytest
import alert_engine as ae
from tests.test_cth_temporal_metrics import (signed_scope_db, _persist_signed_record,
    _binding, _patch_snapshot, _snapshot, _record)

@pytest.fixture
def alerts():
    connection = sqlite3.connect(':memory:')
    connection.row_factory = sqlite3.Row
    ae.init_alert_tables(connection)
    yield connection
    connection.close()

def notes():
    return [{'sentiment': 'positive', 'risk_level': 'low'} for _ in range(30)]

def test_unconfigured_surge_does_not_invent_two_hundred_percent(alerts):
    result = ae.evaluate_alerts(notes(), mention_baseline=1, conn=alerts)
    assert not result['alerts']
    assert result['mention_surge_rule']['state'] == 'CONFIGURATION_REQUIRED'
    assert ae.get_config(alerts)['mention_surge_pct'] is None
    assert alerts.execute('SELECT count(*) FROM alert_records').fetchone()[0] == 0

@pytest.mark.parametrize('source', ['DEFAULT-IC020', 'DEFAULT', '', None])
def test_historical_default_is_not_operator_approval(alerts, source):
    alerts.execute('INSERT OR REPLACE INTO alert_configs(key,value,source) VALUES (?,?,?)', ('mention_surge_pct',200,source))
    result = ae.evaluate_alerts(notes(), mention_baseline=1, conn=alerts)
    assert not result['alerts']
    assert result['mention_surge_rule']['threshold_pct'] is None
    # The historical row is preserved, not overwritten or silently deleted.
    assert alerts.execute("SELECT value FROM alert_configs WHERE key='mention_surge_pct'").fetchone()[0] == 200

@pytest.mark.parametrize('value', [-1, 0, float('inf'), None])
def test_invalid_explicit_threshold_is_configuration_required(alerts, value):
    alerts.execute('INSERT OR REPLACE INTO alert_configs(key,value,source) VALUES (?,?,?)', ('mention_surge_pct',value,'MANUAL'))
    result = ae.evaluate_alerts(notes(), mention_baseline=1, conn=alerts)
    assert not result['alerts']
    assert result['mention_surge_rule']['state'] == 'CONFIGURATION_REQUIRED'


def test_explicit_legacy_threshold_and_cooldown_remain_compatible(alerts):
    alerts.execute('INSERT OR REPLACE INTO alert_configs(key,value,source) VALUES (?,?,?)', ('mention_surge_pct',250,'MANUAL'))
    first = ae.evaluate_alerts(notes(), mention_baseline=1, conn=alerts)
    second = ae.evaluate_alerts(notes(), mention_baseline=1, conn=alerts)
    assert len(first['alerts']) == 1 and second['alerts'] == []
    assert first['mention_surge_rule']['method'] == 'legacy_heuristic'
    assert first['mention_surge_rule']['threshold_pct'] == 250
    row = alerts.execute('SELECT * FROM alert_records').fetchone()
    assert '非趋势模型' in row['message'] and row['state'] == 'DETECTED'


def test_real_signed_source_flows_through_original_alert_owner_without_writes(signed_scope_db):
    day = (date.today()-timedelta(days=1)).isoformat()
    with sqlite3.connect(signed_scope_db) as connection:
        _persist_signed_record(connection, source_id='scope-a', subject_id='SUBJ-A', publish_datetime=day)
        _persist_signed_record(connection, source_id='scope-b', subject_id='SUBJ-B', publish_datetime=day)
        before = connection.total_changes
        result = ae.read_cth_temporal_alerts(connection, start_date=day, end_date=day, authorize=lambda: _binding())
        assert connection.total_changes == before
        assert connection.execute("SELECT name FROM sqlite_master WHERE name='alert_records'").fetchone() is None
    evaluation = result['alert_evaluation']
    assert result['read']['returned_count'] == 1
    assert evaluation['context']['binding'] == result['binding']
    assert evaluation['context']['window'] == result['window']
    assert evaluation['context']['snapshot_sha256'] == result['snapshot_sha256']
    assert evaluation['state'] == 'CONFIGURATION_REQUIRED'
    assert evaluation['rule'] is None and evaluation['threshold'] is None
    assert evaluation['model_state'] == 'INSUFFICIENT'
    assert evaluation['alerts'] == [] and evaluation['write_state'] == 'NOT_PERFORMED'

@pytest.mark.parametrize('change', [{'read_allowed':False},{'subject_id':'SUBJ-B'}])
def test_revocation_or_scope_change_cannot_return_analysis(monkeypatch, change):
    _patch_snapshot(monkeypatch, _snapshot([_record()]))
    calls=[]
    def authorize():
        calls.append(True)
        return _binding(**change) if len(calls)>1 else _binding()
    with pytest.raises(PermissionError):
        ae.read_cth_temporal_alerts(object(), start_date='2026-03-04', end_date='2026-03-04', authorize=authorize)


def test_claimed_model_ready_is_never_a_business_rule(monkeypatch):
    import trend_api
    _patch_snapshot(monkeypatch, _snapshot([_record()]))
    monkeypatch.setattr(trend_api, 'analyze_observed_series', lambda *a,**k: {'state':'READY','method':'stl-arima-pelt-ewma-cusum@1','monitoring':{'state':'READY','points':[{'ewma_alarm':True,'cusum_alarm':True}]}})
    result=ae.read_cth_temporal_alerts(object(),start_date='2026-03-04',end_date='2026-03-04',authorize=lambda:_binding())
    assert result['alert_evaluation']['model_state']=='READY'
    assert result['alert_evaluation']['state']=='CONFIGURATION_REQUIRED'
    assert result['alert_evaluation']['alerts']==[]


def test_caller_cannot_supply_pass_or_series():
    with pytest.raises(TypeError):
        ae.read_cth_temporal_alerts(object(), start_date='2026-03-04', end_date='2026-03-04', authorize=lambda:_binding(), analysis={'state':'READY'})


def test_revocation_after_model_analysis_is_checked_again(monkeypatch):
    import trend_api
    _patch_snapshot(monkeypatch, _snapshot([_record()]))
    revoked = [False]
    def model(*args, **kwargs):
        revoked[0] = True
        return {'state':'INSUFFICIENT','reason':'fixture'}
    monkeypatch.setattr(trend_api, 'analyze_observed_series', model)
    def authorize():
        return _binding(read_allowed=not revoked[0])
    with pytest.raises(PermissionError, match='after analysis'):
        ae.read_cth_temporal_alerts(object(),start_date='2026-03-04',end_date='2026-03-04',authorize=authorize)
