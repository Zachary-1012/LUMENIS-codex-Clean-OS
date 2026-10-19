import math
import pytest
from flask import Flask
import podcast_routes
from podcast.intelligence.breakout import classify_breakout
from podcast.intelligence.content_yield import YieldSignal,plan_yield
@pytest.fixture
def client():
 app=Flask(__name__);app.register_blueprint(podcast_routes.podcast_bp);return app.test_client()
@pytest.mark.parametrize('body',[{}, {'current':None,'baseline':1},{'current':10,'baseline':0},{'current':0,'baseline':0}])
def test_no_baseline_not_normal(client,body):
 r=client.post('/api/podcast/breakout',json=body);assert r.status_code==200
 assert r.json['state']=='insufficient_data' and r.json['ratio'] is None
 assert r.json['baseline']==body.get('baseline')
@pytest.mark.parametrize('current,state',[(0,'decaying'),(80,'underperforming'),(100,'normal'),(130,'accelerating'),(200,'breakout'),(400,'viral')])
def test_actual_zero_and_positive_baseline(client,current,state):
 r=client.post('/api/podcast/breakout',json={'current':current,'baseline':100});assert r.status_code==200 and r.json['state']==state
 assert r.json['ratio']==current/100
@pytest.mark.parametrize('value',[-1,True,'1',math.nan,math.inf,[],{}])
@pytest.mark.parametrize('field',['current','baseline'])
def test_invalid_observations(client,field,value):
 body={'current':1,'baseline':1,field:value};r=client.post('/api/podcast/breakout',json=body);assert r.status_code==400 and r.json['state']=='invalid_input'
@pytest.mark.parametrize('body',[None,[],{'current':1,'baseline':1,'secret':1},{'current':1,'baseline':1,'breakout_ratio':3,'viral_ratio':2}])
def test_bad_breakout_body(client,body):assert client.post('/api/podcast/breakout',json=body).status_code==400

def test_overflow_ratio_not_nonfinite_json(client):
 r=client.post('/api/podcast/breakout',json={'current':1e308,'baseline':1e-308});assert r.status_code==200
 assert r.json['ratio'] is None and r.json['reason']=='ratio_out_of_numeric_range'

def test_missing_yield_vs_observed_zero(client):
 r=client.post('/api/podcast/content-yield',json={});assert r.status_code==200 and r.json['plan']['state']=='input_required' and r.json['plan']['assets']==[]
 body=dict.fromkeys(YieldSignal.__dataclass_fields__,0);r=client.post('/api/podcast/content-yield',json=body)
 assert r.status_code==200 and r.json['plan']['state']=='planned' and r.json['plan']['assets']==['full_episode'] and r.json['assets_created'] is False
 body['story_count']=2;body['insight_count']=1;r=client.post('/api/podcast/content-yield',json=body)
 assert r.status_code==200 and 'article' in r.json['plan']['assets']
@pytest.mark.parametrize('value',[-1,True,1.5,'2',math.nan,1000001,[],{}])
def test_invalid_yield_count(client,value):
 r=client.post('/api/podcast/content-yield',json={'story_count':value});assert r.status_code==400
@pytest.mark.parametrize('body',[None,[],{'unknown_count':2}])
def test_bad_yield_body(client,body):assert client.post('/api/podcast/content-yield',json=body).status_code==400
