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


def test_repeated_source_requires_occurrence_selection_and_preserves_other_use(sample):
 t,r=sample;a=t.assets[0]
 t=t.add_clip(a.asset_id,track_id='voice',source_out=.5,timeline_start=2)
 with pytest.raises(VideoEditingError,match='CLIP_SELECTION_REQUIRED'):candidate(t,r,['0:1'])
 first=t.tracks[-1].clips[0]
 out=word_deletion_candidate(t,r,word_ids=['0:1'],clip_ids=[first.clip_id],
     transcript_artifact_id='ART-test',transcript_sha256='a'*64)
 revised=_apply_edl_operations(t,_parse_content_edl(out['edl']))
 retained=[c for c in revised.tracks[-1].clips if c.source_in==0 and c.source_out==.5]
 assert len(retained)==1 and retained[0].timeline_start==pytest.approx(1.9)
 assert out['word_mappings'][0]['clip_id']==first.clip_id


def test_nonzero_speed_source_samples_synchronize_secondary_track_and_captions(sample):
 t,r=sample;a=t.assets[0]
 t=t.move_audio_clip(t.tracks[-1].clips[0].clip_id,timeline_start=1)
 t=t.set_playback_rate(t.tracks[-1].clips[0].clip_id,playback_rate=2)
 t=t.add_audio_track('music',audio_role='bgm').add_clip(a.asset_id,track_id='music',source_out=.5,timeline_start=1)
 t=t.add_caption(1,1.25,'Caption wording is independent')
 r=copy.deepcopy(r);r['audio_normalization']={'source_clock':{'source_sample_rate':48000}}
 out=word_deletion_candidate(t,r,word_ids=['0:1'],clip_ids=[t.tracks[1].clips[0].clip_id],
     transcript_artifact_id='ART-test',transcript_sha256='a'*64)
 assert out['word_mappings'][0]['timeline_start']==pytest.approx(1.05)
 assert out['word_mappings'][0]['timeline_end_exact']=={'numerator':11,'denominator':10}
 assert out['word_mappings'][0]['source_start_sample']==4800
 assert len(out['affected_clip_ids'])==2 and len(out['affected_caption_ids'])==1
 revised=_apply_edl_operations(t,_parse_content_edl(out['edl']))
 assert revised.version==t.version+1
 assert revised.undo().to_dict()['tracks']==t.to_dict()['tracks']
 assert revised.overlays[-1].end_sec==pytest.approx(1.2)
 assert all(c.playback_rate==2 for c in revised.tracks[1].clips)
 assert out['transcript_text_modified'] is False and out['redub_performed'] is False
 assert Timeline.from_dict(revised.to_dict(),assets=[a]).to_dict()==revised.to_dict()


def test_short_word_boundaries_and_large_batch_are_not_frame_rounded(sample):
 t,r=sample
 r=copy.deepcopy(r);r['transcript']['segments'][0]['words']=[
   {'word':str(i),'start':i/1000,'end':i/1000+.0004} for i in range(150)]
 out=candidate(t,r,[f'0:{i}' for i in range(150)])
 assert len(out['edl']['decisions'])==1 and len(out['word_mappings'])==150
 revised=_apply_edl_operations(t,_parse_content_edl(out['edl']))
 assert revised.duration_sec==pytest.approx(.44)
 assert len(revised.tracks[-1].clips)==150


def test_speed_word_cut_renders_actual_audio_and_reopens(sample,tmp_path):
 from lumenis.shared.content_creation.rendering import render_timeline
 t,r=sample
 t=t.set_playback_rate(t.tracks[-1].clips[0].clip_id,playback_rate=2)
 out=candidate(t,r,['0:1'])
 revised=_apply_edl_operations(t,_parse_content_edl(out['edl']))
 reopened=Timeline.from_dict(revised.to_dict(),assets=list(t.assets))
 result=render_timeline(reopened,tmp_path/'speed-word-cut.wav',output_kind='audio')
 assert result['state']=='rendered_verified'
 import wave
 with wave.open(str(tmp_path/'speed-word-cut.wav')) as audio:
  assert audio.getnframes()==9600 and audio.getframerate()==48000
