import subprocess
from lumenis.shared.content_creation.toolchain_capabilities import inspect_media_toolchain


def test_real_media_toolchain_reports_actual_filters_and_font():
    result=inspect_media_toolchain()
    assert result['platform'] and not result['cross_platform_verified'] and not result['automatic_install']
    assert set(result['ffmpeg']['filters'])=={'flite','afftdn','ass','drawtext','loudnorm','sidechaincompress'}
    if result['caption_font']['glyphs_available']:
        assert len(result['caption_font']['sha256'])==64
    for key,value in result['ffmpeg']['filters'].items():
        assert (value['capability'] in result['missing_capabilities']) is not value['available']


def test_missing_runtime_is_explicit_no_silent_fallback(monkeypatch):
    import shared_artifacts
    from lumenis.shared.content_creation import video_editing
    monkeypatch.setattr(shared_artifacts,'_ffmpeg_path',lambda:None)
    monkeypatch.setattr(video_editing,'_ffprobe_path',lambda:None)
    result=inspect_media_toolchain()
    assert not result['ffmpeg']['available'] and not result['ffprobe']['available']
    assert len(result['missing_capabilities'])==6 and not result['automatic_install']
