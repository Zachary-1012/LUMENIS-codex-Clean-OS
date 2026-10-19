import pytest
from lumenis.system.collector.guard.resource_guard import ResourceGuard, NORMAL, RESOURCE_GUARDED, HIGH_EFFICIENCY
from lumenis.system.collector.guard.schedule_adapter import advice,should_stop_schedule
@pytest.mark.parametrize('value',[None,True,'20',float('nan'),float('inf'),-1,101,10**400])
def test_unknown_cpu_cannot_accelerate(value):
 d=ResourceGuard().decide(cpu_pct=value,ram_pct=20,queue_lag=0)
 assert d['state']==NORMAL and d['worker_scale']<=1
 assert not d['resource_observation_complete']
@pytest.mark.parametrize('action',[None,'', 'unknown',[],{}])
def test_unknown_lifecycle_stops(action):
 assert should_stop_schedule(action)
 d=advice(action)
 assert not d['allow_new'] and d['queue_policy']=='queue'
def test_missing_queue_does_not_mean_measured_zero():
 assert ResourceGuard().decide(cpu_pct=20,ram_pct=20)['state']==NORMAL
def test_freeze_never_becomes_allow_new_under_load():
 d=ResourceGuard().decide('freeze_and_recover',cpu_pct=99,ram_pct=99,queue_lag=900)
 assert d['queue_policy']=='queue' and not d['allow_new']
def test_known_high_load_then_observed_recovery():
 g=ResourceGuard()
 assert g.decide(cpu_pct=99,ram_pct=10,queue_lag=0)['state']==RESOURCE_GUARDED
 assert g.decide('ramp_up',cpu_pct=20,ram_pct=20,queue_lag=0)['worker_scale']<1
 assert g.decide(cpu_pct=20,ram_pct=20,queue_lag=0)['state']==HIGH_EFFICIENCY
 assert g.decide()['worker_scale']<=1
@pytest.mark.parametrize('metric,value',[('ram_pct',float('nan')),('ram_pct',False),('ram_pct',101),('queue_lag',None),('queue_lag',False),('queue_lag',-1),('queue_lag',1.5)])
def test_other_invalid_metrics_never_accelerate(metric,value):
 args=dict(cpu_pct=20,ram_pct=20,queue_lag=0);args[metric]=value
 d=ResourceGuard().decide(**args)
 assert d['worker_scale']<=1 and not d['resource_observation_complete']
def test_unknown_sleep_never_uses_normal_interval():
 from lumenis.system.collector.guard.schedule_adapter import schedule_sleep_seconds
 assert schedule_sleep_seconds(None,6)>schedule_sleep_seconds('schedule_normal',6)
def test_known_acceleration_keeps_configured_ceiling():
 assert ResourceGuard(max_worker_scale=1.05).decide(cpu_pct=20,ram_pct=20,queue_lag=0)['worker_scale']<=1.05

def test_actual_diagnostic_route_missing_queue_is_unknown():
 import ast
 from pathlib import Path
 from flask import Flask,request,jsonify
 source=Path(__file__).resolve().parents[1]/'data_query_api.py'
 tree=ast.parse(source.read_text())
 node=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='api_resource_guard')
 node.decorator_list=[]
 namespace={'request':request,'jsonify':jsonify,'_resource_guard':ResourceGuard()}
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),namespace)
 app=Flask(__name__)
 with app.test_request_context('/?cpu=20&ram=20'):
  result=namespace['api_resource_guard']().get_json()
  assert result['resource_guard_state']==NORMAL
  assert result['resource_guard_decision']['resource_observation_complete'] is False
 with app.test_request_context('/?cpu=20&ram=20&queue_lag=0'):
  assert namespace['api_resource_guard']().get_json()['resource_guard_state']==HIGH_EFFICIENCY
