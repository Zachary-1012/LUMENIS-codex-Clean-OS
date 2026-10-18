"""Synthetic timestamp contract tests, not ASR accuracy evidence."""
import copy
import pytest
from tests.test_content_project_storage import media_store
from tests.test_local_content_source_routes import local_client
from lumenis.shared.content_creation.video_editing import Timeline,fingerprint_local_media,VideoEditingError,_apply_edl_operations
from lumenis.shared.content_creation.transcript_editing import word_deletion_candidate
from shared_artifacts import _parse_content_edl

@pytest.fixture
def sample(media_store):
 a=fingerprint_local_media(str(media_store['source']))
 t=Timeline.from_assets([a]).add_audio_track('voice',audio_role='voiceover').add_clip(a.asset_id,track_id='voice',source_out=.5)
 r={'original_source_sha256':a.sha256,'selected_audio_stream_index':0,'transcript':{'segments':[{'id':0,'words':[{'word':'one','start':0.,'end':.1},{'word':' two','start':.1,'end':.2},{'word':' three','start':.3,'end':.4}]}]}}
 return t,r

def candidate(t,r,ids):return word_deletion_candidate(t,r,word_ids=ids,transcript_artifact_id='ART-test',transcript_sha256='a'*64)

@pytest.mark.parametrize('ids,duration',[(['0:1'],.4),(['0:0'],.4),(['0:0','0:1'],.3),(['0:1','0:2'],.3)])
def test_explicit_word_mapping_preview_immutable(sample,ids,duration):
 t,r=sample;original=t.to_dict();out=candidate(t,r,ids)
 revised=_apply_edl_operations(t,_parse_content_edl(out['edl']))
 assert revised.duration_sec==pytest.approx(duration)
 assert t.to_dict()==original and out['automatic_application'] is False
 assert out['boundary_rounding_seconds']==0 and out['human_alignment_accuracy']=='NOT_VERIFIED'

@pytest.mark.parametrize('ids',[[],['bad'],['0:0','0:0'],[None],'0:1'])
def test_invalid_selection(sample,ids):
 with pytest.raises(VideoEditingError):candidate(*sample,ids)

@pytest.mark.parametrize('mutation',['hash','overlap','nan','missing'])
def test_source_and_time_rejected(sample,mutation):
 t,r=sample;r=copy.deepcopy(r)
 if mutation=='hash':r['original_source_sha256']='b'*64
 if mutation=='overlap':r['transcript']['segments'][0]['words'][1]['start']=.05
 if mutation=='nan':r['transcript']['segments'][0]['words'][1]['end']=float('nan')
 if mutation=='missing':r['transcript']['segments'][0]['words']=[]
 with pytest.raises(VideoEditingError):candidate(t,r,['0:1'])


def test_project_candidate_requires_verified_original_transcript(sample,monkeypatch,tmp_path):
 import json,hashlib,zipfile
 from contextlib import contextmanager
 import shared_artifacts as owner
 from lumenis.shared.content_creation.transcript_editing import project_word_deletion_candidate
 t,r=sample;r={**r,'owner':'SYSTEM AI Gateway','source_annotation':'model_estimated_unreviewed_derivative'}
 data=json.dumps(r).encode();digest=hashlib.sha256(data).hexdigest();path=tmp_path/'project.zip'
 with zipfile.ZipFile(path,'w') as z:z.writestr('transcription.json',data)
 project={'timeline':t.to_dict(),'source_artifact_refs':['source'],'delivery_manifest':{'transcription.json':{'sha256':digest}}}
 monkeypatch.setattr(owner,'_verified_content_project',lambda *a,**k:(project,{}, {'sha256':'b'*64},path))
 @contextmanager
 def sources(*a,**k):yield [{'asset':t.assets[0]}]
 monkeypatch.setattr(owner,'resolve_content_source_assets',sources)
 args=dict(actor={},scope={},source_artifact_refs=['source'],word_ids=['0:1'])
 out=project_word_deletion_candidate('project',**args)
 assert out['parent_sha256']=='b'*64 and out['transcript_sha256']==digest
 filler_args=dict(actor={},scope={},source_artifact_refs=['source'],filler_terms=['two'],expected_transcript_sha256=digest)
 assert project_word_deletion_candidate('project',**filler_args)['selected_words'][0]['id']=='0:1'
 with pytest.raises(VideoEditingError,match='STALE'):project_word_deletion_candidate('project',**{**filler_args,'expected_transcript_sha256':'0'*64})
 with pytest.raises(VideoEditingError,match='BINDING_REQUIRED'):project_word_deletion_candidate('project',**{**filler_args,'word_ids':['0:1']})
 with pytest.raises(VideoEditingError,match='SCOPE'):project_word_deletion_candidate('project',**{**args,'source_artifact_refs':['other']})
 with zipfile.ZipFile(path,'w') as z:z.writestr('transcription.json',b'{}')
 with pytest.raises(VideoEditingError,match='HASH'):project_word_deletion_candidate('project',**args)
 project['delivery_manifest']={}
 with pytest.raises(VideoEditingError,match='VERIFIED_TRANSCRIPT'):project_word_deletion_candidate('project',**args)

@pytest.mark.parametrize('body',[
 {'project_id':'ART-test','word_ids':['0:1'],'timestamps':[0,1]},
 {'project_id':'ART-test','word_ids':['0:1'],'actor_id':2},
 {'word_ids':['0:1']},None])
def test_api_rejects_client_timestamp_or_identity_injection(local_client,body):
 client,store,_=local_client
 from tests.test_local_content_source_routes import SHARED_HEADERS
 response=client.post('/api/experience/shared-skills/shared.content_project/inspect',headers=SHARED_HEADERS,
  json={'action_type':'READ','input':{'asset_paths':[str(store['source'])],'transcript_edit':body}})
 assert response.status_code!=200
 assert response.get_json()['code'] in {'WORD_EDIT_OPTIONS_INVALID','CONTENT_SOURCE_REFERENCE_REQUIRED'}

def test_literal_terms_unicode_context_and_no_substrings(sample):
 from lumenis.shared.content_creation.transcript_editing import filler_word_deletion_candidate
 t,r=sample;r=copy.deepcopy(r);r['transcript']['segments'][0]['words'][1]['word']=' ＵＭ，'
 args=dict(transcript_artifact_id='ART-test',transcript_sha256='a'*64)
 out=filler_word_deletion_candidate(t,r,filler_terms=['um'],**args)
 assert [w['id'] for w in out['selected_words']]==['0:1']
 assert len(out['candidate_contexts'][0]['context'])==3
 assert out['semantic_filler_classification'] is False and out['automatic_application'] is False
 assert filler_word_deletion_candidate(t,r,filler_terms=['u'],**args)['state']=='no_matches'
 r['transcript']['segments'][0]['words'][1]['word']='嗯啊'
 assert filler_word_deletion_candidate(t,r,filler_terms=['嗯'],**args)['state']=='no_matches'
 assert filler_word_deletion_candidate(t,r,filler_terms=['嗯啊'],**args)['state']=='candidate'

@pytest.mark.parametrize('terms',[[],[''],['...'],['two words'],['UM','um'],[None],['\x00']])
def test_invalid_literal_terms(sample,terms):
 from lumenis.shared.content_creation.transcript_editing import filler_word_deletion_candidate
 with pytest.raises(VideoEditingError):filler_word_deletion_candidate(*sample,filler_terms=terms,transcript_artifact_id='ART-test',transcript_sha256='a'*64)

def test_no_word_times_cannot_be_successful_empty_match(sample):
 from lumenis.shared.content_creation.transcript_editing import filler_word_deletion_candidate
 t,r=sample;r=copy.deepcopy(r);r['transcript']['segments'][0]['words']=[]
 with pytest.raises(VideoEditingError,match='WORD_TIMES_REQUIRED'):filler_word_deletion_candidate(t,r,filler_terms=['um'],transcript_artifact_id='ART-test',transcript_sha256='a'*64)
