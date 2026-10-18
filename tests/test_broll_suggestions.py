import subprocess
import pytest
from lumenis.shared.content_creation.video_editing import Timeline,VideoEditingError,fingerprint_local_media,TimedOverlay
from lumenis.shared.content_creation.broll_suggestions import suggest_broll,prepare_broll_insertion
from tests.test_content_project_storage import media_store

@pytest.fixture
def video(media_store):
    path=media_store['source'].with_suffix('.mp4')
    subprocess.run(['ffmpeg','-v','error','-n','-f','lavfi','-i','color=c=red:s=96x64:r=30:d=2','-c:v','libx264','-threads:v','1',str(path)],check=True,capture_output=True)
    return fingerprint_local_media(str(path))

def test_explainable_local_keywords_and_explicit_insertion(video):
    ranking=suggest_broll([video],transcript='展示城市街景与建筑',descriptions={video.asset_id:'城市建筑街景自有素材'})
    assert ranking['candidates'][0]['matching_terms'] and ranking['semantic_understanding'] is False
    assert ranking['candidates'][0]['rights_state']=='unknown_not_a_license'
    original=Timeline.from_assets([video]).add_clip(video.asset_id,source_out=1,audio_role='muted')
    before=original.to_dict()
    preview=prepare_broll_insertion(original,selected_asset_id=video.asset_id,at_sec=.5,source_in=1,source_out=1.5)
    result=Timeline.from_dict(preview['timeline'],assets=[video])
    clips=result.tracks[0].clips
    assert [(c.source_in,c.source_out) for c in clips]==[(0,.5),(1,1.5),(.5,1)]
    assert original.to_dict()==before and preview['requires_explicit_export_confirmation']
    assert result.version>original.version

def test_no_match_does_not_fabricate_candidate(video):
    assert suggest_broll([video],transcript='医学研究',descriptions={video.asset_id:'城市街景'})['candidates']==[]

@pytest.mark.parametrize('value',[float('nan'),True,-1,9])
def test_invalid_insertion_position_denied(video,value):
    timeline=Timeline.from_assets([video]).add_clip(video.asset_id,source_out=1,audio_role='muted')
    with pytest.raises(VideoEditingError):prepare_broll_insertion(timeline,selected_asset_id=video.asset_id,at_sec=value,source_in=1,source_out=1.5)

def test_out_of_scope_metadata_and_changed_source_denied(video):
    with pytest.raises(VideoEditingError,match='SCOPE'):suggest_broll([video],transcript='city',descriptions={'not-authorized':'city'})
    from pathlib import Path
    Path(video.path).write_bytes(b'changed')
    with pytest.raises(ValueError):suggest_broll([video],transcript='city',descriptions={video.asset_id:'city'})
