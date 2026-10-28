"""Synthetic timestamp contract tests, not ASR accuracy evidence."""
import copy
import pytest
from tests.test_content_project_storage import media_store as media_store
from tests.test_local_content_source_routes import local_client as local_client
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


@pytest.fixture
def manual_project(local_client,tmp_path,monkeypatch):
 import io,math,struct,wave
 from tests.test_local_content_source_routes import SHARED_HEADERS,export_shared_project
 from lumenis.system.ai_gateway import owned_speech
 client,store,app=local_client
 def no_inference(*args,**kwargs):raise AssertionError('manual editing must not run or download a model')
 monkeypatch.setattr(owned_speech,'transcribe_audio',no_inference)
 second=tmp_path/'take-two'/'voice.wav';second.parent.mkdir()
 with wave.open(str(second),'wb') as audio:
  audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(32000)
  audio.writeframes(b''.join(struct.pack('<h',round(6000*math.sin(index/13))) for index in range(24000)))
 originals=[store['source'],second];source_ids=[]
 for path in originals:
  options=dict(headers=SHARED_HEADERS,data=path.read_bytes(),content_type='application/octet-stream')
  pending=client.post('/api/experience/content-sources?filename=voice.wav',**options)
  assert pending.status_code==403,pending.get_json()
  identifier=pending.get_json()['confirmation']['confirmation_id']
  confirmed=client.post('/api/experience/content-source-confirmations/'+identifier,
      headers=SHARED_HEADERS,json={'confirmed':True})
  assert confirmed.status_code==200,confirmed.get_json()
  result=client.post('/api/experience/content-sources?filename=voice.wav',**options)
  assert result.status_code==201,result.get_json()
  source_ids.append(result.get_json()['result']['artifact']['artifact_id'])
 assets=[fingerprint_local_media(path) for path in originals]
 timeline=Timeline.from_assets(assets).add_audio_track('first',audio_role='voiceover')
 timeline=timeline.add_clip(assets[0].asset_id,track_id='first',source_out=.4,timeline_start=1)
 timeline=timeline.set_playback_rate(timeline.tracks[-1].clips[0].clip_id,playback_rate=2)
 timeline=timeline.add_audio_track('second',audio_role='voiceover')
 timeline=timeline.add_clip(assets[1].asset_id,track_id='second',source_out=.6,timeline_start=1.1)
 segments=[
  [{'id':0,'start':0,'end':.2,'text':'not a','speaker_id':'human-label-A','words':[
      {'word':'not','start':0,'end':.1},{'word':'a','start':.1,'end':.2}]},
   {'id':1,'start':.2,'end':.4,'text':'verified recording','speaker_id':'human-label-A','words':[
      {'word':'verified','start':.2,'end':.3},{'word':'recording','start':.3,'end':.4}]}],
  [{'id':0,'start':0,'end':.3,'text':'second take','speaker_id':'human-label-B','words':[
      {'word':'second','start':0,'end':.15},{'word':'take','start':.15,'end':.3}]},
   {'id':1,'start':.3,'end':.6,'text':'declared annotations','speaker_id':'human-label-B','words':[
      {'word':'declared','start':.3,'end':.45},{'word':'annotations','start':.45,'end':.6}]}]]
 annotations=[{'asset_id':asset.asset_id,'audio_stream_index':0,'language':'en','segments':part}
     for asset,part in zip(assets,segments)]
 payload={'asset_refs':source_ids,'timeline':timeline.to_dict(),'output_kind':'audio','title':'Manual multi-source edit',
     'render_media':False,'delivery_options':{'manual_transcripts':annotations}}
 first=export_shared_project(client,payload)
 assert first.status_code==200,first.get_json()
 return dict(client=client,store=store,app=app,assets=assets,source_ids=source_ids,timeline=timeline,
     payload=payload,first=first.get_json()['result'],originals={path:path.read_bytes() for path in originals},
     io=io)


@pytest.fixture
def manual_project_with_repeated_clip(manual_project):
 import copy
 from tests.test_local_content_source_routes import export_shared_project
 case=manual_project
 timeline=case['timeline'].add_clip(case['assets'][0].asset_id,track_id='first',source_out=.4,timeline_start=2.5)
 payload=copy.deepcopy(case['payload'])
 payload.update(title='Repeated source clip transcript project',timeline=timeline.to_dict())
 payload['delivery_options']['manual_transcripts'][0]['segments'].append(
     {'id':2,'start':.3,'end':.4,'text':'overlapping speaker','speaker_id':'human-label-C',
      'words':[{'word':'overlapping','start':.3,'end':.4}]})
 result=export_shared_project(case['client'],payload)
 assert result.status_code==200,result.get_json()
 return {**case,'timeline':timeline,'payload':payload,'first':result.get_json()['result']}


def test_manual_multi_source_draft_review_word_cut_render_export_and_cold_reopen(manual_project):
 import hashlib,json,os,subprocess,sys,wave,zipfile
 from pathlib import Path
 from tests.test_local_content_source_routes import SHARED_HEADERS,SHARED_SCOPE,export_shared_project
 case=manual_project;client=case['client'];first=case['first'];assets=case['assets']
 first_id=first['artifact']['artifact_id']
 detail=client.get('/api/experience/content-projects/'+first_id,headers=SHARED_HEADERS)
 assert detail.status_code==200,detail.get_json()
 assert detail.get_json()['project']['render']['state']=='not_rendered'
 first_package=client.get(detail.get_json()['package_url'],headers=SHARED_HEADERS)
 assert first_package.status_code==200
 member='transcription-'+assets[0].asset_id+'.json'
 with zipfile.ZipFile(case['io'].BytesIO(first_package.data)) as archive:
  original_transcript=archive.read(member)
  mapped=json.loads(archive.read('transcript-timeline.json'))
 assert mapped['rendered_sha256'] is None and mapped['render_binding']=='PROJECT_DRAFT_NOT_RENDERED'
 assert len(mapped['sources'])==2 and mapped['overlapping_cues'] and mapped['new_model_execution']=='NOT_RUN'
 preview=client.post('/api/experience/shared-skills/shared.content_project/inspect',headers=SHARED_HEADERS,
     json={'action_type':'READ','input':{'asset_refs':case['source_ids'],'transcript_edit':{
       'project_id':first_id,'word_ids':['1:0'],'transcript_asset_id':assets[0].asset_id,
       'expected_transcript_sha256':hashlib.sha256(original_transcript).hexdigest()}}})
 assert preview.status_code==200,preview.get_json()
 selected=preview.get_json()['transcript_edit']
 assert len(selected['affected_clip_ids'])==2 and selected['original_media_modified'] is False
 reviewed={'asset_id':assets[0].asset_id,'member':member,'expected_sha256':hashlib.sha256(original_transcript).hexdigest(),
     'edits':[{'segment_id':0,'expected_text':'not a','text':'never a','confirmed':True}]}
 second=export_shared_project(client,{**case['payload'],'previous_artifact_id':first_id,
     'timeline':selected['preview_timeline'],'render_media':True,'delivery_options':{'transcript_reviews':[reviewed]}})
 assert second.status_code==200,second.get_json()
 result=second.get_json()['result'];second_id=result['artifact']['artifact_id']
 reopened=client.get('/api/experience/content-projects/'+second_id,headers=SHARED_HEADERS)
 assert reopened.status_code==200,reopened.get_json()
 package=client.get(reopened.get_json()['package_url'],headers=SHARED_HEADERS)
 assert package.status_code==200 and hashlib.sha256(package.data).hexdigest()==result['artifact']['sha256']
 with zipfile.ZipFile(case['io'].BytesIO(package.data)) as archive:
  assert archive.read(member)==original_transcript
  reviewed_bytes=archive.read('transcription-reviewed-'+assets[0].asset_id+'.json')
  assert json.loads(reviewed_bytes)['text_review']['segments'][0]['text']=='never a'
  mapped=json.loads(archive.read('transcript-timeline.json'))
  media=archive.read('media.wav')
  assert mapped['rendered_sha256']==hashlib.sha256(media).hexdigest()==result['render']['media_sha256']
  assert mapped['timeline_version']==result['project']['timeline']['version']
  assert mapped['sources'][0]['source_artifact_ref'] in case['source_ids']
  assert 'never a' in archive.read('transcript-timeline.vtt').decode()
  assert all(word['source_word_id']!='1:0' for word in mapped['words'] if word['source_asset_id']==assets[0].asset_id)
 with wave.open(case['io'].BytesIO(media)) as audio:
  assert audio.getframerate()==48000 and audio.getnframes()==79200
 assert result['project']['parent_artifact_id']==first_id and result['project']['project_revision']==2
 assert client.get(detail.get_json()['package_url'],headers=SHARED_HEADERS).data==first_package.data
 assert all(path.read_bytes()==raw for path,raw in case['originals'].items())
 code='''import json,shared_artifacts as o
from flask import Flask
from lumenis.system.security.permission import resolve_local_workspace_principal
a=Flask(__name__);a.config['LUMENIS_OPEN_WORKSPACE']=True
with a.test_request_context('/',environ_base={'REMOTE_ADDR':'127.0.0.1'},headers={'Host':'localhost'}):
 p=resolve_local_workspace_principal(module='content',action='read')
 print(json.dumps([o.read_content_project(i,actor=p,shared_workspace_scope='''+repr(SHARED_SCOPE)+''')['render']['state'] for i in '''+repr([first_id,second_id])+''']))
'''
 cold=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).resolve().parents[1],env=os.environ.copy(),
     capture_output=True,text=True,timeout=30)
 assert cold.returncode==0,cold.stderr
 assert json.loads(cold.stdout)==['not_rendered','rendered_verified']


def test_explicit_word_selection_cannot_ignore_stale_transcript_hash(sample,monkeypatch,tmp_path):
 import hashlib,json,zipfile
 import shared_artifacts as owner
 from lumenis.shared.content_creation.transcript_editing import project_word_deletion_candidate
 timeline,transcript=sample;transcript.update(owner='SYSTEM AI Gateway',source_annotation='model_estimated_unreviewed_derivative')
 raw=json.dumps(transcript).encode();path=tmp_path/'project.zip'
 with zipfile.ZipFile(path,'w') as archive:archive.writestr('transcription.json',raw)
 project={'timeline':timeline.to_dict(),'source_artifact_refs':['source'],
     'delivery_manifest':{'transcription.json':{'sha256':hashlib.sha256(raw).hexdigest()}}}
 monkeypatch.setattr(owner,'_verified_content_project',lambda *a,**kw:(project,{}, {'sha256':'b'*64},path))
 with pytest.raises(VideoEditingError,match='TRANSCRIPT_STALE'):
  project_word_deletion_candidate('project',actor={},scope={},source_artifact_refs=['source'],
      word_ids=['0:1'],expected_transcript_sha256='0'*64)


def test_manual_draft_revoke_restore_and_rehashed_wrong_revision_rejected(manual_project):
 import hashlib,json,zipfile
 from tests.test_local_content_source_routes import SHARED_HEADERS
 from lumenis.shared.content_creation.speech_transcription import project_transcription_summary
 case=manual_project;client=case['client'];project_id=case['first']['artifact']['artifact_id']
 url='/api/experience/content-projects/'+project_id
 case['app'].config['LUMENIS_OPEN_WORKSPACE']=False
 assert client.get(url,headers=SHARED_HEADERS).status_code==401
 case['app'].config['LUMENIS_OPEN_WORKSPACE']=True
 assert client.get(url,headers=SHARED_HEADERS).status_code==200
 package=case['store']['root']/(project_id+'.zip');original=package.read_bytes()
 with zipfile.ZipFile(package) as archive:files={name:archive.read(name) for name in archive.namelist()}
 derived=json.loads(files['transcript-timeline.json']);derived['timeline_version']+=1
 files['transcript-timeline.json']=json.dumps(derived,ensure_ascii=False).encode()
 project=json.loads(files['project.json']);render=json.loads(files['render.json'])
 project['delivery_manifest']['transcript-timeline.json']={
     'sha256':hashlib.sha256(files['transcript-timeline.json']).hexdigest(),'size_bytes':len(files['transcript-timeline.json'])}
 render['delivery_reports']['timeline_transcription']=project_transcription_summary(derived,files['transcript-timeline.json'])
 files['project.json']=json.dumps(project).encode();files['render.json']=json.dumps(render).encode()
 with zipfile.ZipFile(package,'w',compression=zipfile.ZIP_STORED) as archive:
  for name,raw in files.items():archive.writestr(name,raw)
 with case['store']['repository'].connect() as connection:
  connection.execute('UPDATE lumenis_shared_artifacts SET sha256=?,size_bytes=? WHERE artifact_id=?',
      (hashlib.sha256(package.read_bytes()).hexdigest(),package.stat().st_size,project_id))
 rejected=client.get(url,headers=SHARED_HEADERS)
 assert rejected.status_code!=200 and rejected.get_json()['code']=='CONTENT_TRANSCRIPT_PROJECT_BINDING_CHANGED'
 package.write_bytes(original)
 with case['store']['repository'].connect() as connection:
  connection.execute('UPDATE lumenis_shared_artifacts SET sha256=?,size_bytes=? WHERE artifact_id=?',
      (hashlib.sha256(original).hexdigest(),len(original),project_id))
 assert client.get(url,headers=SHARED_HEADERS).status_code==200


def test_transcript_projection_cancellation_keeps_saved_parent(manual_project,monkeypatch):
 import shared_artifacts as owner
 from lumenis.shared.content_creation import speech_transcription
 from tests.test_local_content_source_routes import SHARED_HEADERS,export_shared_project
 case=manual_project;client=case['client'];project_id=case['first']['artifact']['artifact_id']
 package=case['store']['root']/(project_id+'.zip');before=package.read_bytes()
 def cancel(*args,**kwargs):raise PermissionError('TRANSCRIPT_PROJECTION_CANCELED')
 monkeypatch.setattr(speech_transcription,'build_project_transcription_files',cancel)
 result=export_shared_project(client,{**case['payload'],'title':'Canceled revision',
     'previous_artifact_id':project_id,'delivery_options':{}})
 assert result.status_code!=200
 assert package.read_bytes()==before
 assert client.get('/api/experience/content-projects/'+project_id,headers=SHARED_HEADERS).status_code==200
 with case['store']['repository'].connect() as connection:
  assert connection.execute("SELECT COUNT(*) FROM lumenis_shared_artifacts WHERE kind='content_project'").fetchone()[0]==1
 assert not list(case['store']['root'].glob('content-project-*'))
 assert owner._content_delivery_filename('transcript-timeline.json')


def test_transcript_route_selects_exact_clip_word_instances_and_reopens_real_audio(manual_project_with_repeated_clip):
 import hashlib,json,wave,zipfile
 from tests.test_local_content_source_routes import SHARED_HEADERS,export_shared_project
 case=manual_project_with_repeated_clip;client=case['client'];first_id=case['first']['artifact']['artifact_id']
 package_path=case['store']['root']/(first_id+'.zip')
 first_package=package_path.read_bytes()
 read_route=client.post('/api/experience/shared-skills/shared.content_project/inspect',headers=SHARED_HEADERS,
     json={'action_type':'READ','input':{'asset_refs':case['source_ids'],
       'transcripts':{'project_id':first_id,'limit':100}}})
 assert read_route.status_code==200,read_route.get_json()
 reading=read_route.get_json()['transcripts']
 assert reading['project_sha256']==case['first']['artifact']['sha256']
 assert reading['timeline_version']==case['timeline'].version and reading['word_count']>=2
 asset_a,asset_b=[asset.asset_id for asset in case['assets']]
 repeated_word=[word for word in reading['words'] if word['source_asset_id']==asset_a and word['word_id']=='0:0']
 assert len(repeated_word)==2 and len({word['clip_id'] for word in repeated_word})==2
 assert {word['qualified_id'] for word in repeated_word}=={
     asset_a+':0:0:'+word['clip_id'] for word in repeated_word}
 assert len({word['qualified_id'] for word in reading['words']})==len(reading['words'])
 repeated_word.sort(key=lambda word:word['start'])
 clip_a,clip_b=[word['clip_id'] for word in repeated_word]
 source_clip=[word['clip_id'] for word in reading['words']
     if word['source_asset_id']==asset_b and word['word_id']=='1:0']
 assert len(source_clip)==1
 source_bindings={source['transcript_asset_id']:source for source in reading['sources']
     if source['state']=='AVAILABLE'}
 assert set(source_bindings)=={asset_a,asset_b}
 def selection(asset_id,word_id,clips):
  source=source_bindings[asset_id]
  return {'transcript_asset_id':asset_id,'expected_transcript_sha256':source['expected_transcript_sha256'],
      'word_ids':[word_id],'clip_ids':clips}
 # source word 0:0 occurs in both clips but only its clip_a instance is selected.
 # words 1:1 and 2:0 overlap in clip_b, so their actual cut is emitted once.
 transcript_bindings=[selection(asset_a,'0:0',[clip_a]),
     selection(asset_a,'1:1',[clip_b]),selection(asset_a,'2:0',[clip_b]),
     selection(asset_b,'1:0',source_clip)]
 def edit_route(selections):
  return client.post('/api/experience/shared-skills/shared.content_project/inspect',headers=SHARED_HEADERS,
      json={'action_type':'READ','input':{'asset_refs':case['source_ids'],
        'transcript_edit':{'project_id':first_id,'source_selections':selections}}})
 duplicate=edit_route([transcript_bindings[0],transcript_bindings[0]])
 assert duplicate.status_code!=200 and duplicate.get_json()['code']=='WORD_EDIT_SOURCE_SELECTION_DUPLICATE'
 repeated_occurrence=edit_route([transcript_bindings[0],selection(asset_a,'0:0',[clip_a,clip_b])])
 assert repeated_occurrence.status_code!=200 and repeated_occurrence.get_json()['code']=='WORD_EDIT_SOURCE_SELECTION_DUPLICATE'
 route=edit_route(transcript_bindings)
 assert route.status_code==200,route.get_json()
 out=route.get_json()['transcript_edit']
 assert out['state']=='candidate' and out['automatic_application'] is False
 assert out['parent_sha256']==case['first']['artifact']['sha256']
 assert out['preview_timeline']['version']==case['timeline'].version+1
 expected={
     (asset_a,'0:0',clip_a),(asset_a,'1:1',clip_b),
     (asset_a,'2:0',clip_b),(asset_b,'1:0',source_clip[0])}
 selected=out['selected_words']
 selected_instances={(word['source_asset_id'],word['id'],word['clip_id']) for word in selected}
 assert selected_instances==expected
 assert len({word['qualified_id'] for word in selected})==len(expected)
 assert all(word['qualified_id']==word['source_asset_id']+':'+word['id']+':'+word['clip_id'] for word in selected)
 mapping_instances={(item['source_asset_id'],item['word_id'],item['clip_id']) for item in out['word_mappings']}
 assert mapping_instances==expected
 cuts=out['edl']['decisions'][0]['metadata']['cuts']
 cut_keys={(item['clip_id'],round(item['source_in'],6),round(item['source_out'],6)) for item in cuts}
 assert len(cuts)==len(cut_keys)==3
 assert sum(item['clip_id']==clip_b and round(item['source_in'],6)==.3
     and round(item['source_out'],6)==.4 for item in cuts)==1
 assert {item['clip_id'] for item in cuts}=={clip_a,clip_b,source_clip[0]}
 assert len(out['removed_source_intervals'])==3
 assert all(interval['transcript_sha256'] for interval in out['removed_source_intervals'])
 assert package_path.read_bytes()==first_package
 revision=export_shared_project(client,{**case['payload'],'title':'Exact clip word transcript edit',
     'previous_artifact_id':first_id,'timeline':out['preview_timeline'],'render_media':True,
     'delivery_options':{}})
 assert revision.status_code==200,revision.get_json()
 result=revision.get_json()['result'];second_id=result['artifact']['artifact_id']
 reopened=client.get('/api/experience/content-projects/'+second_id,headers=SHARED_HEADERS)
 assert reopened.status_code==200,reopened.get_json()
 saved=client.get(reopened.get_json()['package_url'],headers=SHARED_HEADERS)
 assert saved.status_code==200 and hashlib.sha256(saved.data).hexdigest()==result['artifact']['sha256']
 with zipfile.ZipFile(case['io'].BytesIO(saved.data)) as archive:
  sidecar=json.loads(archive.read('transcript-timeline.json'))
  media=archive.read('media.wav')
  assert len(sidecar['sources'])==2
  assert {source['source_asset_id'] for source in sidecar['sources']}=={asset_a,asset_b}
  assert sidecar['timeline_version']==result['project']['timeline']['version']
  assert sidecar['rendered_sha256']==hashlib.sha256(media).hexdigest()==result['render']['media_sha256']
  assert all(archive.read('transcription-'+asset.asset_id+'.json') for asset in case['assets'])
  remaining=[(word['source_asset_id'],word['source_word_id']) for word in sidecar['words']]
  assert remaining.count((asset_a,'0:0'))==1
  assert remaining.count((asset_a,'1:1'))==1 and remaining.count((asset_a,'2:0'))==1
  assert (asset_b,'1:0') not in remaining
 with wave.open(case['io'].BytesIO(media)) as audio:
  assert audio.getframerate()==48000 and audio.getnframes()>0
 assert result['project']['parent_artifact_id']==first_id and result['project']['project_revision']==2
 assert package_path.read_bytes()==first_package
 reopen_route=client.post('/api/experience/shared-skills/shared.content_project/inspect',headers=SHARED_HEADERS,
     json={'action_type':'READ','input':{'asset_refs':case['source_ids'],
       'transcripts':{'project_id':second_id,'limit':100}}})
 assert reopen_route.status_code==200,reopen_route.get_json()
 assert reopen_route.get_json()['transcripts']['timeline_version']==result['project']['timeline']['version']
 reopened_words=reopen_route.get_json()['transcripts']['words']
 assert len([word for word in reopened_words if word['source_asset_id']==asset_a and word['word_id']=='0:0'])==1
 assert not any(word['source_asset_id']==asset_b and word['word_id']=='1:0' for word in reopened_words)
