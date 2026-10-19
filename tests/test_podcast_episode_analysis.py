import json,wave,math
import pytest
from podcast.intelligence.episode_analysis import build_episode_analysis_files
from lumenis.shared.content_creation.video_editing import fingerprint_local_media,VideoEditingError
@pytest.fixture
def asset(tmp_path,monkeypatch):
 monkeypatch.setenv('LUMENIS_LOCAL_ASSET_DIR',str(tmp_path));p=tmp_path/'owned.wav'
 with wave.open(str(p),'wb') as w:w.setparams((1,2,16000,0,'NONE','not compressed'));w.writeframes(b'\x01\x00'*32000)
 return fingerprint_local_media(str(p))
def build(asset,**kw):return build_episode_analysis_files(asset,timeline_version=1,expected_timeline_version=1,**kw)
def test_real_decode_and_run_metadata(asset):
 r=build(asset,nodes=[{'node_id':'one','node_type':'insight_peak','start_sec':0,'end_sec':1}]);v=r['report']
 assert v['decoded_duration_seconds']==2 and v['metrics']['story_node_density']['value']==30
 assert v['metrics']['emotion_peak_density']['value']==0 and v['metrics']['insight_density']['value']==30
 assert v['metrics']['runtime_retention_curve']['value'] is None
 assert v['run']['status']=='completed' and v['run']['model_name'] is None and v['run']['inference_performed'] is False
 assert json.loads(r['files']['podcast-analysis.json'])==v
 assert v['annotation_origin']=='USER_ANNOTATION' and v['learning_promoted'] is False
 assert build(asset,nodes=[])['report']['run']['run_id']!=v['run']['run_id']
def test_missing_is_not_zero(asset):
 assert build(asset)['report']['metrics']['story_node_density']['value'] is None
 assert build(asset,nodes=[])['report']['metrics']['story_node_density']['value']==0
@pytest.mark.parametrize('edit',[{'end_sec':3},{'start_sec':math.nan},{'node_type':'auto_fact'},{'node_id':''},{'end_sec':True}])
def test_invalid_node(asset,edit):
 n={'node_id':'one','node_type':'story','start_sec':0,'end_sec':1};n.update(edit)
 with pytest.raises(VideoEditingError):build(asset,nodes=[n])
def test_revision_cancel(asset):
 with pytest.raises(VideoEditingError,match='VERSION_MISMATCH'):build_episode_analysis_files(asset,timeline_version=2,expected_timeline_version=1)
 def cancel():raise RuntimeError('cancel')
 with pytest.raises(RuntimeError,match='cancel'):build(asset,check_cancel=cancel)
