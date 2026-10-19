"""PR83: deleted sources are not export dependencies; referenced bytes stay checked."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from lumenis.shared.content_creation import timeline_interchange as exchange
from lumenis.shared.content_creation.video_editing import (
    Timeline, TimelineClip, TimelineTrack, VideoEditingError, fingerprint_local_media,
)


@pytest.fixture
def sources(tmp_path, monkeypatch):
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):
        pytest.skip('real FFmpeg/FFprobe required')
    monkeypatch.setenv('LUMENIS_LOCAL_ASSET_DIR', str(tmp_path))
    assets = []
    for name, color in (('used', 'red'), ('deleted', 'blue')):
        path = tmp_path / (name + '.mp4')
        subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-n', '-f', 'lavfi', '-i',
                        f'color=c={color}:s=160x90:r=30:d=2', '-c:v', 'libx264',
                        '-threads', '1', str(path)], check=True, timeout=30)
        assets.append(fingerprint_local_media(str(path)))
    used, deleted = assets
    original = Timeline(assets=tuple(assets), tracks=(TimelineTrack('video', 'video', (
        TimelineClip('keep', used.asset_id, 0, 1, 0),
        TimelineClip('remove', deleted.asset_id, 0, 1, 1),
    )),), format_ratio='16:9')
    return original, original.delete('remove'), used, deleted


def export(timeline, used, fmt, **kwargs):
    return exchange.build_interchange_files(
        timeline, formats=[fmt], frame_rate='30',
        media_refs={used.asset_id: 'used.mp4'}, allow_loss=(fmt == 'cmx3600'), **kwargs)


@pytest.mark.parametrize('fmt', ['otio', 'fcpxml', 'cmx3600'])
@pytest.mark.parametrize('state', ['unchanged', 'missing', 'changed'])
def test_deleted_source_not_export_dependency(sources, monkeypatch, fmt, state):
    original, edited, used, deleted = sources
    snapshot = edited.to_dict()
    if state == 'missing':
        Path(deleted.path).unlink()
    elif state == 'changed':
        with Path(deleted.path).open('ab') as handle:
            handle.write(b'changed unused source')
    verified = []
    real_fingerprint = exchange.fingerprint_local_media
    def record(path):
        verified.append(path)
        return real_fingerprint(path)
    monkeypatch.setattr(exchange, 'fingerprint_local_media', record)
    result = export(edited, used, fmt)
    assert verified == [used.path]
    assert result['report']['source_sha256'] == {used.asset_id: used.sha256}
    assert json.loads(result['files']['interchange.json'])['source_sha256'] == {used.asset_id: used.sha256}
    assert edited.to_dict() == snapshot
    assert edited.assets == original.assets
    assert edited.undo().tracks == original.tracks
    assert edited.undo().assets == original.assets
    if fmt in ('otio', 'fcpxml'):
        restored = exchange.import_interchange(result['files']['timeline.' + fmt], format=fmt,
            assets=(used,), media_refs={used.asset_id: 'used.mp4'})
        assert restored.tracks == edited.tracks


@pytest.mark.parametrize('state', ['missing', 'changed'])
def test_referenced_source_integrity_still_blocks(sources, monkeypatch, state):
    original, edited, used, deleted = sources
    if state == 'missing':
        Path(used.path).unlink()
        # A declared clock permits preflight but cannot bypass byte verification.
        monkeypatch.setattr(exchange, '_ffprobe_path', lambda: None)
        with pytest.raises(VideoEditingError, match='LOCAL_MEDIA_NOT_FOUND'):
            export(edited, used, 'otio', source_frame_rates={used.asset_id: '30'})
    else:
        with Path(used.path).open('ab') as handle:
            handle.write(b'changed referenced source')
        with pytest.raises(VideoEditingError, match='INTERCHANGE_MEDIA_CHANGED'):
            export(edited, used, 'otio')


@pytest.mark.parametrize('cancel_at', [1, 2, 3])
def test_cancellation_remains_fatal(sources, cancel_at):
    _, edited, used, _ = sources
    calls = 0
    def cancel():
        nonlocal calls
        calls += 1
        if calls == cancel_at:
            raise RuntimeError('cancel requested')
    with pytest.raises(RuntimeError, match='cancel requested'):
        export(edited, used, 'otio', check_cancel=cancel)
    assert calls == cancel_at


def test_undo_restores_source_verification(sources):
    original, edited, used, deleted = sources
    with Path(deleted.path).open('ab') as handle:
        handle.write(b'changed source restored by undo')
    recovered = edited.undo()
    assert recovered.tracks == original.tracks
    with pytest.raises(VideoEditingError, match='INTERCHANGE_MEDIA_CHANGED'):
        exchange.build_interchange_files(recovered, formats=['otio'], frame_rate='30',
            media_refs={used.asset_id: 'used.mp4', deleted.asset_id: 'deleted.mp4'})
