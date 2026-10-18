import io,json,wave
from dataclasses import replace
import pytest
from PIL import Image
from lumenis.shared.content_creation.podcast_cover import build_podcast_cover_files
from lumenis.shared.content_creation.video_editing import fingerprint_local_media,VideoEditingError

@pytest.fixture
def asset(tmp_path,monkeypatch):
    monkeypatch.setenv('LUMENIS_LOCAL_ASSET_DIR',str(tmp_path))
    p=tmp_path/'own.wav'
    with wave.open(str(p),'wb') as w:
        w.setparams((1,2,16000,0,'NONE','not compressed'));w.writeframes(b'\x01\x00'*16000)
    return fingerprint_local_media(str(p))

def test_actual_chinese_cover(asset):
    result=build_podcast_cover_files(asset,title='序境声音',subtitle='把复杂的问题讲清楚。')
    im=Image.open(io.BytesIO(result['files']['podcast-cover.png']));im.load()
    assert im.size==(3000,3000) and im.mode=='RGB'
    assert result['report']==json.loads(result['files']['podcast-cover.json'])
    assert result['report']['source_sha256']==asset.sha256
    assert result['report']['published'] is False

@pytest.mark.parametrize('title',['',None,'x'*81,'bad\x00text'])
def test_invalid_copy(asset,title):
    with pytest.raises(VideoEditingError):build_podcast_cover_files(asset,title=title,subtitle='正文')

def test_cancel_and_source_change(asset):
    def cancel():raise RuntimeError('cancelled')
    with pytest.raises(RuntimeError,match='cancelled'):build_podcast_cover_files(asset,title='标题',subtitle='正文',check_cancel=cancel)
    with pytest.raises(VideoEditingError):build_podcast_cover_files(replace(asset,sha256='0'*64),title='标题',subtitle='正文')

def test_missing_glyph_fails(asset,monkeypatch):
    from lumenis.shared.content_creation import rendering
    def missing(text):raise VideoEditingError('CAPTION_FONT_MISSING_GLYPHS')
    monkeypatch.setattr(rendering,'_verify_caption_glyphs',missing)
    with pytest.raises(VideoEditingError,match='MISSING_GLYPHS'):build_podcast_cover_files(asset,title='标题',subtitle='正文')
