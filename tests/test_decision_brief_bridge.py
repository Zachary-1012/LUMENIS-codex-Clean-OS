from copy import deepcopy
import pytest
from tests.test_growth_research_shared import research,upload,start,poll,BASE,SHARED
from tests.test_shared_work_owner_routes import route_workspace
from tests.test_saved_document_workflow import workspace
from agent_research.source_bound import analyze_source_records

def spec(a,b):
 def anchor(s,q): return {'source_id':s,'start':0,'end':len(q),'quote':q}
 text='Cotton jacket. Outfit includes jacket and trousers. https://example.org/look.jpg'
 other='Linen trousers.'
 return {'requirements':['breathable','budget known'],'candidates':[
  {'id':'jacket','label':'Jacket proposal','evidence':anchor(a,text),'requirement_evidence':{'breathable':anchor(a,text)},'images':[{'url':'https://example.org/look.jpg','evidence':anchor(a,text)}]},
  {'id':'trousers','label':'Trousers proposal','evidence':anchor(b,other),'requirement_evidence':{},'images':[]}],
  'combinations':[{'label':'Two-piece proposal','candidate_ids':['jacket','trousers'],'evidence':anchor(a,text)}]}

def test_real_sources_task_save_reopen_selection_draft(research):
 ws=research
 a=upload(ws,'Cotton jacket. Outfit includes jacket and trousers. https://example.org/look.jpg');b=upload(ws,'Linen trousers.')
 decision=spec(a,b)
 task=poll(ws,start(ws,source_ids=[a,b],business_question='Compare materials and possible outfits',research={'decision_brief':decision}))
 assert task['state']=='succeeded',task
 report=task['result']; draft=report['business_analysis']['decision_brief']
 assert draft['available_candidate_count']==2 and draft['coverage']=='PARTIAL'
 assert draft['candidates'][0]['unknown_requirements']==['budget known']
 assert draft['candidates'][0]['images'][0]['media_status']=='NOT_READ'
 assert draft['combinations'][0]['official_set_status']=='NOT_VERIFIED'
 assert draft['business_execution_authorized'] is False
 saved=ws['api'].post(BASE+'/jobs/'+report['job_id']+'/save',headers=SHARED,json={'request_id':'save-decision-0001','title':'Evidence-linked alternatives'})
 assert saved.status_code==200,saved.get_json()
 work=saved.get_json()['result'];assert 'Jacket proposal' in work['document']['markdown']
 assert work['document']['payload']['research_result']['decision_brief']==draft
 reopened=ws['api'].get('/api/experience/saved-work/'+work['artifact']['artifact_id'],headers=SHARED)
 assert reopened.status_code==200,reopened.get_json()
 assert reopened.get_json()['result']['document']==work['document']
 assert '![' not in work['document']['markdown']
 with ws['repo'].transaction() as con:
  con.execute('DELETE FROM lumenis_shared_artifacts WHERE artifact_id=?',(b,))
 assert ws['api'].get('/api/experience/saved-work/'+work['artifact']['artifact_id'],headers=SHARED).status_code != 200

def records():
 a='Cotton jacket. Outfit includes jacket and trousers. https://example.org/look.jpg';b='Linen trousers.'
 return [{'source_id':sid,'evidence_id':sid,'scope_evidence_ref':sid,'content_excerpt':text} for sid,text in [('a',a),('b',b)]]

def test_missing_sources_and_partial_do_not_become_complete():
 result=analyze_source_records('outfits',[],decision_brief=spec('a','b'))['decision_brief']
 assert result['status']=='needs_sources' and result['coverage']=='UNKNOWN'
 assert all(c['selection_status']=='UNAVAILABLE' for c in result['candidates'])
 assert result['candidates'][0]['images'][0]['source_url'] is None
 assert analyze_source_records('outfits',records()[:1],decision_brief=spec('a','b'))['decision_brief']['available_candidate_count']==1

def test_wrong_quote_rejected():
 proposal=spec('a','b');proposal['candidates'][0]['evidence']['quote']='fake'
 with pytest.raises(ValueError,match='QUOTE_MISMATCH'):
  analyze_source_records('outfits',records(),decision_brief=proposal)

def test_unquoted_image_rejected():
 proposal=spec('a','b');proposal['candidates'][0]['images'][0]['url']='https://example.org/other.jpg'
 with pytest.raises(ValueError,match='URL_NOT_IN_SOURCE'):
  analyze_source_records('outfits',records(),decision_brief=proposal)

def test_challenged_evidence_cannot_support_candidates():
 initial=analyze_source_records('outfits',records(),decision_brief=spec('a','b'))
 h=next(h for h in initial['hypotheses'] if h['evidence_refs']==['a'])
 review={'review_id':'r1','hypothesis_id':h['hypothesis_id'],'disposition':'challenge','rationale':'needs verification','evidence_refs':['a']}
 result=analyze_source_records('outfits',records(),decision_brief=spec('a','b'),hypothesis_reviews=[review])['decision_brief']
 assert result['candidates'][0]['selection_status']=='UNAVAILABLE'
 assert result['combinations'][0]['relation_status']=='UNKNOWN'

@pytest.mark.parametrize('kind',['official_look','editorial_styling','recommended_combo','sellable_bundle','related_case','combined_proposal'])
def test_relationship_types_stay_distinct_and_unverified(kind):
 proposal=spec('a','b');proposal['combinations'][0]['relationship_type']=kind
 combo=analyze_source_records('compare alternatives',records(),decision_brief=proposal)['decision_brief']['combinations'][0]
 assert combo['requested_relationship_type']==kind
 assert not combo['relationship_type_verified'] and combo['official_set_status']=='NOT_VERIFIED'

@pytest.mark.parametrize('question',['选择适合活动的租户与场地','比较品牌营销创意案例','规划播客素材与引用','选择文档视觉设计参考'])
def test_cross_scenario_contract_is_not_clothing_specific(question):
 proposal=spec('a','b');proposal['requirements']=['来源时间已知'];proposal['candidates'][0]['requirement_evidence']={}
 result=analyze_source_records(question,records(),decision_brief=proposal)['decision_brief']
 assert result['requirements']==['来源时间已知'] and result['available_candidate_count']==2
 assert result['candidates'][0]['unknown_requirements']==['来源时间已知']

def test_anchor_end_cannot_exceed_resolved_excerpt():
 proposal=spec('a','b');proposal['candidates'][0]['evidence']['end']=10**100
 with pytest.raises(ValueError,match='QUOTE_MISMATCH'):
  analyze_source_records('outfits',records(),decision_brief=proposal)

@pytest.mark.parametrize('bad',[[],{}])
def test_relationship_kind_malformed_is_controlled_input_error(bad):
 proposal=spec('a','b');proposal['combinations'][0]['relationship_type']=bad
 with pytest.raises(ValueError,match='COMBINATION_INVALID'):
  analyze_source_records('outfits',records(),decision_brief=proposal)
