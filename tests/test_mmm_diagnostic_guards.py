"""Synthetic diagnostic tables only; no sampler/model or real-market acceptance."""
import ast
from pathlib import Path
import pandas as pd
import pytest
from lumenis.shared.reporting.statistics_mmm import _mmm_diagnostics

SIZES = {'intercept':None, 'channel_beta':2, 'season':2, 'macro_control_beta':1}
NAMES = ['intercept','channel_beta[0]','channel_beta[1]','season[0]','season[1]','macro_control_beta[0]']


def table():
    return pd.DataFrame({'r_hat':[1.01]*6,'ess_bulk':[400.0]*6},index=NAMES)


def test_complete_raw_diagnostics_pass():
    assert _mmm_diagnostics(table(),SIZES)=={'max_rhat':1.01,'min_ess_bulk':400.0,'diagnostic_failures':[]}


@pytest.mark.parametrize('column,value', [('r_hat',float('nan')),('ess_bulk',float('nan')),
    ('r_hat',float('inf')),('ess_bulk',-float('inf')),('r_hat',1.05001),('ess_bulk',199.999),('r_hat',0)])
def test_one_bad_parameter_cannot_hide_in_aggregate(column,value):
    frame=table();frame.loc['season[1]',column]=value
    result=_mmm_diagnostics(frame,SIZES)
    assert result['diagnostic_failures']==[{'parameter':'season[1]','reason':
        'DIAGNOSTICS_NOT_FINITE' if not pd.notna(value) or abs(value)==float('inf')
        else 'DIAGNOSTICS_THRESHOLD_NOT_PASSED'}]


@pytest.mark.parametrize('change',['row','column','duplicate','unexpected'])
def test_required_diagnostics_complete_and_unique(change):
    frame=table()
    if change=='row':frame=frame.drop('channel_beta[1]')
    elif change=='column':frame=frame.drop(columns='r_hat')
    elif change=='duplicate':frame=pd.concat([frame,frame.iloc[:1]])
    else:frame.loc['foreign']=[1,400]
    assert _mmm_diagnostics(frame,SIZES)['diagnostic_failures'][0]['reason']=='REQUIRED_PARAMETER_DIAGNOSTICS_MISSING_OR_DUPLICATED'


def test_thresholds_include_exact_boundary():
    frame=table();frame.loc['intercept']=[1.05,200]
    assert not _mmm_diagnostics(frame,SIZES)['diagnostic_failures']


def test_summary_requests_unrounded_values_and_guard_precedes_ready():
    import lumenis.shared.reporting.statistics_mmm as owner
    tree=ast.parse(Path(owner.__file__).read_text())
    call=next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)
              and isinstance(n.func.value,ast.Name) and n.func.value.id=='az' and n.func.attr=='summary')
    assert next(k.value.value for k in call.keywords if k.arg=='round_to')=='none'
    source=Path(owner.__file__).read_text()
    assert source.index('if diagnostics["diagnostic_failures"] or divergences:') < source.index('state="READY"')
