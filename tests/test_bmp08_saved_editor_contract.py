"""Synthetic HTTP contract used by BMP08; no model, remote API or live DB."""
from copy import deepcopy
import json
import pytest
from tests.test_saved_document_workflow import workspace
from tests.test_shared_work_owner_routes import route_workspace, WORKS

SHARED = {'X-Lumenis-Workspace-Scope': json.dumps({'scope_kind':'shared_workspace','version':1},separators=(',',':'))}


def seed(ws):
    from podcast.intelligence.episode_runtime import PodcastPlan, PodcastSegment
    plan = PodcastPlan(title='Owned episode', description='Synthetic original episode.', language='en', segments=(
        PodcastSegment(segment_id='stable-a', media_asset_id='MEDIA-owned', source_in=1, source_out=3.25,
                       original_text='Original words', corrected_text='Reviewed words', speaker='Host', chapter_title='Opening'),
        PodcastSegment(segment_id='stable-b', media_asset_id='MEDIA-owned', source_in=4, source_out=7,
                       original_text='Other words', corrected_text='Other reviewed words', speaker='Guest', chapter_title='Interview'),
    ))
    body={'title':plan.title,'markdown':plan.script_text(),'kind':'podcast_episode',
          'payload':{'podcast_plan':plan.to_dict(), 'retained_user_note':'Retained'},'citations':[],
          'contract':{'id':'lumenis.podcast-plan','version':'1','required_payload_paths':['podcast_plan']},
          'request_id':'bmp08-first-version'}
    response=ws['api'].post(WORKS,headers=SHARED,json=body)
    assert response.status_code==200,response.get_json()
    return response.get_json()['result']


def revision(parent):
    doc=deepcopy(parent['document']); plan=doc['payload']['podcast_plan']
    plan['revision']+=1
    plan['segments'][1]['corrected_text']='Changed by stable identity'
    return {'title':doc['title'],'markdown':'Owned episode\nSynthetic original episode.\n\n[00:00:00.000] Host Reviewed words\n[00:00:02.250] Guest Changed by stable identity',
            'kind':'podcast_episode','payload':doc['payload'],'citations':doc['citations'],'contract':doc['contract'],
            'request_id':'bmp08-revised-version','work_id':doc['work_id'],
            'previous_artifact_id':parent['artifact']['artifact_id'],'expected_draft_digest':doc['draft_digest']}


def test_bmp08_exact_revision_payload_readback_and_replay(route_workspace):
    ws=route_workspace; first=seed(ws); body=revision(first)
    saved=ws['api'].post(WORKS,headers=SHARED,json=body)
    assert saved.status_code==200,saved.get_json()
    second=saved.get_json()['result']
    assert second['document']['version']==2
    assert second['document']['parent_artifact_id']==first['artifact']['artifact_id']
    assert second['document']['payload']==body['payload']
    assert second['document']['payload']['podcast_plan']['segments'][1]['original_text']=='Other words'
    assert second['receipt']['constraint_observations']['media_lineage']=='W4_W6_NOT_VERIFIED'
    reopened=ws['api'].get(WORKS+'/'+second['artifact']['artifact_id'],headers=SHARED)
    assert reopened.status_code==200
    assert reopened.get_json()['result']['document']==second['document']
    replay=ws['api'].post(WORKS,headers=SHARED,json=body)
    assert replay.status_code==200 and replay.get_json()['result']['replayed'] is True
    assert replay.get_json()['result']['artifact']['artifact_id']==second['artifact']['artifact_id']
    old=ws['api'].get(WORKS+'/'+first['artifact']['artifact_id'],headers=SHARED)
    assert old.get_json()['result']['document']==first['document']
    listing=ws['api'].get(WORKS,headers=SHARED,query_string={'kind':'podcast_episode','latest_only':'true','limit':'30'})
    assert listing.status_code==200
    assert [r['artifact']['artifact_id'] for r in listing.get_json()['result']['items']]==[second['artifact']['artifact_id']]


def test_bmp08_stale_digest_fails_without_commit(route_workspace):
    ws=route_workspace; body=revision(seed(ws)); body['expected_draft_digest']='0'*64
    before=ws['repo'].query_one('SELECT COUNT(*) FROM lumenis_shared_artifacts')[0]
    response=ws['api'].post(WORKS,headers=SHARED,json=body)
    assert response.status_code in (400,409),response.get_json()
    assert 'CONFLICT' in str(response.get_json())
    assert ws['repo'].query_one('SELECT COUNT(*) FROM lumenis_shared_artifacts')[0]==before


def test_bmp08_denied_read_and_save_do_not_commit(route_workspace):
    ws=route_workspace; first=seed(ws); body=revision(first)
    before=ws['repo'].query_one('SELECT COUNT(*) FROM lumenis_shared_artifacts')[0]
    ws['app'].config['LUMENIS_OPEN_WORKSPACE']=False
    for response in (ws['api'].post(WORKS,headers=SHARED,json=body),ws['api'].get(WORKS+'/'+first['artifact']['artifact_id'],headers=SHARED)):
        assert response.status_code in (401,403),response.get_json()
    assert ws['repo'].query_one('SELECT COUNT(*) FROM lumenis_shared_artifacts')[0]==before


def test_bmp08_invalid_segment_does_not_commit(route_workspace):
    ws=route_workspace; body=revision(seed(ws));body['payload']['podcast_plan']['segments'][1]['segment_id']='stable-a'
    before=ws['repo'].query_one('SELECT COUNT(*) FROM lumenis_shared_artifacts')[0]
    response=ws['api'].post(WORKS,headers=SHARED,json=body)
    assert response.status_code==400,response.get_json()
    assert ws['repo'].query_one('SELECT COUNT(*) FROM lumenis_shared_artifacts')[0]==before


def test_bmp08_brand_revision_retains_reauthorized_source_citation(route_workspace):
    from tests.test_shared_work_owner_routes import approved_upload, MATERIALS
    from tests.test_source_brief_job_routes import GLOBAL
    ws=route_workspace
    material,text=approved_upload(ws,filename='bmp08-source.txt')
    response=ws['api'].get(MATERIALS+'/'+str(material['evidence_id'])+'/quote',headers=GLOBAL,
                           query_string={'start':0,'end':len('Owned material 中文.')})
    assert response.status_code==200
    citation=response.get_json()['result']['citation']
    first=seed(ws)
    body=revision(first)
    for key in ['work_id','previous_artifact_id','expected_draft_digest']:
        body.pop(key)
    body['request_id']='bmp08-brand-initial'
    body['citations']=[citation]
    body['payload']['podcast_plan']['segments'][0]['evidence_refs']=['evidence:'+str(material['evidence_id'])]
    response=ws['api'].post(WORKS,headers=GLOBAL,json=body)
    assert response.status_code==200,response.get_json()
    cited=response.get_json()['result']
    next_body=revision(cited)
    next_body['request_id']='bmp08-brand-revised'
    response=ws['api'].post(WORKS,headers=GLOBAL,json=next_body)
    assert response.status_code==200,response.get_json()
    assert response.get_json()['result']['document']['citations']==cited['document']['citations']
    assert response.get_json()['result']['receipt']['constraint_observations']['source_count']==1
