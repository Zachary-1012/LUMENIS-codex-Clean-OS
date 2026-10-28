"""Declared acquisition fixtures; real permission/DB/Artifact/FFprobe recovery."""
import hashlib
import json
import sqlite3
import math
import struct
import subprocess
import wave
from contextlib import nullcontext

import pytest

from tests.test_collector_comment_pages import comments_case as comments_case
from tests.test_collector_transaction_truth import collector_case as collector_case
from tests.test_content_image_source import _png


@pytest.fixture
def media_case(comments_case, monkeypatch):
    from lumenis.shared.reporting import media_brief as owner
    from lumenis.system.collector.adapters import public_source as transport
    case = comments_case
    detail = case['adapter'].detail
    media_url = 'https://public-media.example.test/source-original.png'
    def observed_detail(target, **kwargs):
        result = detail(target, **kwargs)
        result.items[0]['image_list'] = [{'url': media_url, 'type': 'image'}]
        return result
    monkeypatch.setattr(case['adapter'], 'detail', observed_detail)
    monkeypatch.setitem(case['entry']._last_action, 'xiaohongshu', 0.0)
    collected = case['entry'].collect_detail('xhs', case['source_id'], actor=case['actor'], scope=case['scope'])
    assert collected['ok'], collected
    calls, raw = [], _png()
    def transfer(url, *, destination, max_bytes, check_continue, **kwargs):
        check_continue()
        calls.append(url)
        assert url == media_url and len(raw) <= max_bytes
        destination.write_bytes(raw)
        check_continue()
        return transport.PublicMediaResponse(url, hashlib.sha256(raw).hexdigest(), len(raw), 'image/png', 200, url)
    monkeypatch.setattr(transport, 'fetch_public_media', transfer)
    case.update(media_owner=owner, media_calls=calls, media_raw=raw,
        media_arguments=dict(source_id=case['source_id'], actor=case['actor'], scope=case['scope'],
            source_evidence_ref='app_evidence_records:' + str(collected['evidence_ref'])))
    return case


def _confirm(case):
    owner, args = case['media_owner'], case['media_arguments']
    previous_calls = len(case['media_calls'])
    prepared = owner.prepare_collected_media(**args)
    case['gate'].grant_permission(case['permission'].PermissionLevel.HUMAN_APPROVAL)
    confirmed = owner.confirm_collected_media(**args, source_fingerprint=prepared['source_fingerprint'],
        confirmed_resources=[entry['resource'] for entry in prepared['approval_resources']], confirmed=True)
    assert confirmed['approved'] and len(case['media_calls']) == previous_calls
    return {**args, 'source_fingerprint': prepared['source_fingerprint']}


def _media_inventory(case, monkeypatch, count, *, unavailable=()):
    """Produce signed fixture observations, retaining real Owner persistence."""
    from lumenis.system.collector.adapters import public_source as transport
    detail = case['adapter'].detail
    urls = [f'https://public-media.example.test/native-{index}.png' for index in range(count)]
    def observed_detail(target, **kwargs):
        result = detail(target, **kwargs)
        result.items[0]['image_list'] = [{'url':url,'type':'image'} for url in urls]
        return result
    monkeypatch.setattr(case['adapter'],'detail',observed_detail)
    monkeypatch.setitem(case['entry']._last_action,'xiaohongshu',0.0)
    collected = case['entry'].collect_detail('xhs',case['source_id'],actor=case['actor'],scope=case['scope'])
    assert collected['ok'], collected
    case['media_arguments']['source_evidence_ref'] = 'app_evidence_records:' + str(collected['evidence_ref'])
    failed_urls = {urls[index] for index in unavailable}
    def transfer(url, *, destination, max_bytes, check_continue, **kwargs):
        check_continue()
        case['media_calls'].append(url)
        if url in failed_urls:
            raise transport.PublicSourceHTTPError(404)
        raw = case['media_raw']
        assert url in urls and len(raw) <= max_bytes
        destination.write_bytes(raw)
        return transport.PublicMediaResponse(url,hashlib.sha256(raw).hexdigest(),len(raw),'image/png',200,url)
    monkeypatch.setattr(transport,'fetch_public_media',transfer)
    # These state-machine tests use declared inspection output; the separate
    # local-decoder test below continues to exercise actual FFprobe/FFmpeg.
    monkeypatch.setattr(case['media_owner'],'_inspect_collected_media',
        lambda *args, **kwargs: ({'semantic_understanding':'NOT_RUN'},{}))
    return urls, failed_urls


def test_manual_signed_media_to_real_original_dimensions_reopen_and_no_replay(media_case):
    case, owner = media_case, media_case['media_owner']
    args = _confirm(case)
    first = owner.process_collected_media(**args, job_id='media-user-task-001')
    assert first['ok'], first
    item = first['media'][0]
    assert item['inspection']['asset']['width'] == 8 and item['inspection']['asset']['height'] == 4
    assert item['original']['sha256'] == hashlib.sha256(case['media_raw']).hexdigest()
    assert first['semantic_understanding'] == 'NOT_RUN' and first['full_post_media_coverage'] == 'UNKNOWN'
    reopened = owner.read_collected_media(item['evidence_ref'], **args)
    assert reopened['manifest_sha256'] == item['manifest_sha256'] and reopened['immutable']
    assert b''.join(owner.iter_collected_media_original(item['evidence_ref'], **args)) == case['media_raw']
    assert b''.join(owner.iter_collected_media_original(item['evidence_ref'], **args, start=5, stop=15)) == case['media_raw'][5:15]
    with pytest.raises(ValueError, match='RANGE_INVALID'):
        b''.join(owner.iter_collected_media_original(item['evidence_ref'], **args, start=True))
    replay = owner.process_collected_media(**args, job_id='media-user-task-001')
    assert replay['ok'] and replay['media'][0]['cached'] and len(case['media_calls']) == 1
    with sqlite3.connect(case['db_path']) as con:
        assert con.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='COLLECTED_MEDIA_INSPECTION'").fetchone()[0] == 2
        # Acquisition bytes/rights were not silently promoted or replaced.
        observation = con.execute('SELECT inputs_json FROM app_evidence_records WHERE id=?',
                                  (int(args['source_evidence_ref'].split(':')[1]),)).fetchone()[0]
        assert 'source-original.png' in observation


def test_missing_media_use_approval_never_fetches_and_changed_confirmation_fails(media_case):
    case, owner = media_case, media_case['media_owner']
    prepared = owner.prepare_collected_media(**case['media_arguments'])
    with pytest.raises(PermissionError, match='APPROVAL_REQUIRED'):
        owner.process_collected_media(**case['media_arguments'], source_fingerprint=prepared['source_fingerprint'], job_id='media-denied-001')
    with pytest.raises(PermissionError, match='CONFIRMATION_CHANGED'):
        owner.confirm_collected_media(**case['media_arguments'], source_fingerprint=prepared['source_fingerprint'],
                                     confirmed_resources=['a-different-source'], confirmed=True)
    assert case['media_calls'] == []


def test_cancel_after_original_commit_recovers_without_refetch(media_case, monkeypatch):
    case, owner = media_case, media_case['media_owner']
    args = _confirm(case)
    inspect = owner._inspect_collected_media
    def cancelled(*_args, **_kwargs):
        raise PermissionError('COLLECTION_ATTEMPT_CANCELLED')
    monkeypatch.setattr(owner, '_inspect_collected_media', cancelled)
    with pytest.raises(PermissionError, match='CANCELLED'):
        owner.process_collected_media(**args, job_id='media-cancel-001')
    assert len(case['media_calls']) == 1
    with sqlite3.connect(case['db_path']) as con:
        assert con.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='COLLECTED_MEDIA_INSPECTION'").fetchone()[0] == 1
    monkeypatch.setattr(owner, '_inspect_collected_media', inspect)
    recovered = owner.process_collected_media(**args, job_id='media-cancel-001')
    assert recovered['ok'] and len(case['media_calls']) == 1
    assert recovered['media'][0]['parent_result_ref']


def test_processing_approval_expiry_preserves_reads_but_permission_and_bytes_revocation_blocks(media_case):
    case, owner = media_case, media_case['media_owner']
    args = _confirm(case)
    result = owner.process_collected_media(**args, job_id='media-integrity-001')
    assert result['ok'], result
    item = result['media'][0]
    prepared = owner.prepare_collected_media(**args)
    media_resources = {entry['resource'] for entry in prepared['approval_resources']}
    for token, approval in list(case['gate']._approvals.items()):
        if approval.resource in media_resources:
            case['gate'].revoke_approval(token)
    assert owner.read_collected_media(item['evidence_ref'], **args)['immutable']
    case['gate'].revoke_permission(case['permission'].PermissionLevel.READ)
    with pytest.raises((PermissionError, ValueError)):
        owner.read_collected_media(item['evidence_ref'], **args)
    case['gate'].grant_permission(case['permission'].PermissionLevel.READ)
    args = _confirm(case)
    import shared_artifacts
    original = shared_artifacts._content_original_path(item['original']['sha256'])
    original.write_bytes(b'changed original')
    with pytest.raises(ValueError, match='INTEGRITY_FAILED'):
        owner.read_collected_media(item['evidence_ref'], **args)


def test_native_positions_keep_distinct_original_locators_without_guessing_avatar():
    from lumenis.shared.reporting.media_brief import _observed_media
    record = {'image_list': [{'url': 'https://media.example.test/a.png'},
                             {'url': 'https://media.example.test/a.png'}, {'id': 'missing-url'}],
              'avatar_url': 'https://media.example.test/private-avatar.png'}
    media = _observed_media(record, 'xiaohongshu')
    assert len(media) == 3 and media[0]['native_locator'] != media[1]['native_locator']
    assert media[2]['url'] is None and 'avatar' not in json.dumps(media)


def test_superseded_attempt_cannot_commit_original_association(media_case):
    case, owner = media_case, media_case['media_owner']
    args = _confirm(case)
    with pytest.raises(PermissionError, match='ATTEMPT_SUPERSEDED'):
        owner.process_collected_media(**args, job_id='media-stale-001', attempt_guard=lambda: nullcontext(False))
    with sqlite3.connect(case['db_path']) as con:
        assert con.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='COLLECTED_MEDIA_INSPECTION'").fetchone()[0] == 0


def test_multiple_budget_groups_advance_all_pending_positions_without_replay(media_case, monkeypatch):
    case, owner = media_case, media_case['media_owner']
    urls, _ = _media_inventory(case,monkeypatch,18)
    args = _confirm(case)
    first = owner.process_collected_media(**args,job_id='media-groups-001')
    assert first['saved_media_count'] == 8 and first['pending_positions'] == list(range(8,18))
    assert first['auto_continue'] and first['continuation_reason'] == 'MEDIA_STEP_BUDGET'
    assert first['step_processed_count'] == 8 and not first['intervention_required']
    second = owner.process_collected_media(**args,job_id='media-groups-001')
    assert second['saved_media_count'] == 16 and second['pending_positions'] == [16,17]
    assert second['auto_continue'] and second['step_processed_count'] == 8
    complete = owner.process_collected_media(**args,job_id='media-groups-001')
    assert complete['ok'] and complete['saved_media_count'] == 18
    assert complete['step_processed_count'] == 2 and not complete['auto_continue']
    assert not complete['continuation_required'] and not complete['failed_positions']
    assert case['media_calls'] == urls
    assert [item['position'] for item in complete['media']] == list(range(18))


def test_failed_front_group_is_durable_skipped_and_explicit_new_job_retries(media_case, monkeypatch):
    case, owner = media_case, media_case['media_owner']
    urls, failures = _media_inventory(case,monkeypatch,18,unavailable=range(8))
    args = _confirm(case)
    first = owner.process_collected_media(**args,job_id='media-failed-front-001')
    assert first['failed_positions'] == list(range(8)) and first['pending_positions'] == list(range(8,18))
    assert first['intervention_required'] and not first['auto_continue']
    assert first['continuation_required'] and first['continuation_reason'] == 'MEDIA_INTERVENTION_REQUIRED'
    failure_refs = [item['failure_evidence_ref'] for item in first['media'][:8]]
    second = owner.process_collected_media(**args,job_id='media-failed-front-001')
    assert second['step_processed_count'] == 8 and second['saved_media_count'] == 8
    assert second['pending_positions'] == [16,17] and second['failed_positions'] == list(range(8))
    assert [item['failure_evidence_ref'] for item in second['media'][:8]] == failure_refs
    finished = owner.process_collected_media(**args,job_id='media-failed-front-001')
    assert finished['saved_media_count'] == 10 and not finished['continuation_required']
    assert finished['intervention_required'] and finished['failed_positions'] == list(range(8))
    assert case['media_calls'] == urls
    replay = owner.process_collected_media(**args,job_id='media-failed-front-001')
    assert replay['step_processed_count'] == 0 and case['media_calls'] == urls
    with sqlite3.connect(case['db_path']) as con:
        assert con.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='COLLECTED_MEDIA_INSPECTION' AND result='FAIL'").fetchone()[0] == 8
    # Only a new explicitly confirmed request revisits failed locations.
    failures.clear()
    retried = owner.process_collected_media(**_confirm(case),job_id='media-failed-front-002')
    assert retried['ok'] and retried['step_processed_count'] == 8
    assert case['media_calls'] == urls + urls[:8]


def test_processing_failure_keeps_original_and_does_not_retry_same_job(media_case, monkeypatch):
    case, owner = media_case, media_case['media_owner']
    args = _confirm(case)
    def unavailable(*args, **kwargs):
        raise ValueError('LOCAL_DECODER_UNAVAILABLE')
    monkeypatch.setattr(owner,'_inspect_collected_media',unavailable)
    first = owner.process_collected_media(**args,job_id='media-inspect-fail-001')
    failed = first['media'][0]
    assert failed['original_bytes_saved'] and failed['evidence_ref'] and failed['failure_evidence_ref']
    assert failed['failure_stage'] == 'INSPECT' and failed['failure_class'] == 'PROCESSING'
    assert first['intervention_required'] and not first['auto_continue'] and not first['continuation_required']
    resumed = owner.process_collected_media(**args,job_id='media-inspect-fail-001')
    assert resumed['step_processed_count'] == 0 and len(case['media_calls']) == 1
    assert owner.read_collected_media(failed['evidence_ref'],**args)['original']['sha256']
    monkeypatch.setattr(owner,'_inspect_collected_media',lambda *args, **kwargs: ({'semantic_understanding':'NOT_RUN'},{}))
    recovered = owner.process_collected_media(**_confirm(case),job_id='media-inspect-fail-002')
    assert recovered['ok'] and len(case['media_calls']) == 1
    assert recovered['media'][0]['parent_result_ref'] == failed['evidence_ref']


@pytest.mark.parametrize('blocker',['access','resource'])
def test_global_blocker_stops_group_and_never_auto_continues(media_case, monkeypatch, blocker):
    import shared_artifacts
    from lumenis.system.collector.adapters import public_source as transport
    case, owner = media_case, media_case['media_owner']
    _media_inventory(case,monkeypatch,3)
    args = _confirm(case)
    if blocker == 'access':
        def denied(url, **kwargs):
            case['media_calls'].append(url)
            raise transport.PublicSourceHTTPError(403)
        monkeypatch.setattr(transport,'fetch_public_media',denied)
    else:
        monkeypatch.setattr(shared_artifacts,'content_media_resource_budget',lambda: {'available_bytes':0})
    result = owner.process_collected_media(**args,job_id='media-blocked-'+blocker)
    assert result['failed_positions'] == [0] and result['pending_positions'] == [1,2]
    assert result['intervention_required'] and not result['auto_continue']
    assert result['media'][0]['failure_class'] == ('ACCESS' if blocker == 'access' else 'RESOURCE')
    assert result['network_attempted'] is (blocker == 'access')
    assert len(case['media_calls']) == (1 if blocker == 'access' else 0)


def test_byte_step_budget_is_continuation_without_failed_receipt(media_case, monkeypatch):
    case, owner = media_case, media_case['media_owner']
    urls, _ = _media_inventory(case,monkeypatch,3)
    monkeypatch.setattr(owner,'_COLLECTED_MEDIA_BYTES',2*len(case['media_raw']))
    args = _confirm(case)
    first = owner.process_collected_media(**args,job_id='media-byte-budget-001')
    assert first['auto_continue'] and first['pending_positions'] == [2] and not first['failed_positions']
    assert first['step_processed_count'] == 2 and first['media'][2]['budget_dimension'] == 'bytes'
    final = owner.process_collected_media(**args,job_id='media-byte-budget-001')
    assert final['ok'] and case['media_calls'] == urls


def test_failure_receipt_cannot_commit_after_attempt_is_superseded(media_case, monkeypatch):
    from lumenis.system.collector.adapters import public_source as transport
    case, owner = media_case, media_case['media_owner']
    args = _confirm(case)
    monkeypatch.setattr(transport,'fetch_public_media',lambda *args, **kwargs: (_ for _ in ()).throw(ValueError('TRANSFER_UNAVAILABLE')))
    with pytest.raises(PermissionError,match='ATTEMPT_SUPERSEDED'):
        owner.process_collected_media(**args,job_id='media-fail-stale-001',attempt_guard=lambda: nullcontext(False))
    with sqlite3.connect(case['db_path']) as con:
        assert con.execute("SELECT COUNT(*) FROM app_evidence_records WHERE feature_id='COLLECTED_MEDIA_INSPECTION'").fetchone()[0] == 0


def test_tampered_failure_receipt_cannot_hide_an_unprocessed_position(media_case, monkeypatch):
    case, owner = media_case, media_case['media_owner']
    _media_inventory(case,monkeypatch,1,unavailable=(0,))
    args = _confirm(case)
    result = owner.process_collected_media(**args,job_id='media-fail-signature-001')
    evidence_id = int(result['media'][0]['failure_evidence_ref'].split(':')[1])
    with sqlite3.connect(case['db_path']) as con:
        con.execute("UPDATE app_evidence_records SET outputs_json='{}' WHERE id=?",(evidence_id,))
    with pytest.raises(PermissionError,match='FAILURE_RECEIPT_UNVERIFIED'):
        owner.process_collected_media(**args,job_id='media-fail-signature-001')
    assert len(case['media_calls']) == 1


def test_actual_local_audio_and_video_decoding_preserves_explicit_coverage(tmp_path, monkeypatch):
    import shared_artifacts
    from lumenis.shared.reporting.media_brief import _inspect_collected_media
    monkeypatch.setenv('LUMENIS_LOCAL_ASSET_DIR', str(tmp_path))
    audio_path = tmp_path / 'declared-engineering-audio.wav'
    samples = b''.join(struct.pack('<h', round(1000 * math.sin(index / 7))) for index in range(8000))
    with wave.open(str(audio_path), 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(samples)
    inspected, _ = _inspect_collected_media(audio_path, check_continue=lambda: None)
    assert inspected['asset']['media_kind'] == 'audio'
    assert inspected['coverage']['audio_decoded_ranges'] == [{'start_sec': 0, 'end_sec': 1.0, 'audio_stream_index': 0}]
    assert inspected['speech_transcription'] == 'NOT_RUN'
    png = tmp_path / 'declared-engineering-frame.png'
    png.write_bytes(_png(32, 32))
    video = tmp_path / 'declared-engineering-video.mp4'
    subprocess.run([shared_artifacts._ffmpeg_path(), '-v', 'error', '-nostdin', '-n', '-loop', '1',
        '-i', str(png), '-t', '1', '-r', '4', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(video)],
        check=True, capture_output=True, timeout=20)
    inspected, files = _inspect_collected_media(video, check_continue=lambda: None)
    assert inspected['video_measurement']['decoded_frames'] == 4
    assert inspected['coverage']['video_frames'] == 'ALL_FRAMES_DECODED_NOT_SEMANTICALLY_REVIEWED'
    assert files and inspected['semantic_understanding'] == 'NOT_RUN'


@pytest.mark.parametrize('raw,content_type,extension', [
    (_png(), 'application/octet-stream', '.png'),
    (b'GIF89a' + b'\0' * 30, 'image/gif', '.gif'),
    (b'\0\0\0\x18ftypisom' + b'\0' * 20, 'application/octet-stream', '.mp4'),
    (b'RIFF\0\0\0\0AVI ' + b'\0' * 30, 'video/x-msvideo', '.avi'),
])
def test_original_format_preservation_and_octet_stream_detection(tmp_path, raw, content_type, extension):
    from lumenis.shared.reporting.media_brief import _collected_media_extension
    path = tmp_path / 'original.partial'
    path.write_bytes(raw)
    assert _collected_media_extension(path, content_type) == extension
    with pytest.raises(ValueError, match='UNSUPPORTED'):
        _collected_media_extension(path, 'text/html')


def _declared_format(selection, *, video=True, audio=True, entry='original-entry', index=0, **metadata):
    return {'selection_id':selection,'entry_id':entry,'native_locator':{'entry_index':index},
        'has_video':video,'has_audio':audio,'has_drm':None,'protocol':'https',**metadata}


def test_full_ten_minute_native_dash_timeline_selects_av_within_approved_budget():
    from lumenis.shared.reporting.media_brief import _select_collected_media_formats
    timeline=[{'path':'init.mp4'}]+[{'path':f'{index}.m4s','duration':2} for index in range(317)]
    formats=[_declared_format('video-'+str(height),audio=False,height=height,width=height*16/9,
        tbr=rate,duration=None,fragments=timeline,protocol='http_dash_segments')
        for height,rate in [(2160,15000),(1080,5000),(720,2500)]]
    formats.append(_declared_format('native-audio',video=False,duration=634,tbr=128,abr=128))
    selected,budget,coverage=_select_collected_media_formats({'formats':formats},'video',300*1024*1024)
    assert [item['selection_id'] for item in selected]==['video-720','native-audio']
    assert budget['selected_required_bytes']<=300*1024*1024 and budget['known_over_budget_count']==2
    estimates={value['selection_id']:value for value in budget['estimates']}
    assert estimates['video-720']['duration_sec']==634
    assert estimates['video-720']['duration_basis']=='NATIVE_FRAGMENT_TIMELINE'
    assert coverage['has_video'] is True and coverage['has_audio'] is True
    assert coverage['temporal_coverage']=='COMPLETE_SELECTED_REPRESENTATION_NO_TRIM'
    assert len(selected[0]['fragments'])==318 and coverage['semantic_understanding']=='NOT_RUN'


def test_known_budget_fit_precedes_unknown_and_prefers_feasible_muxed():
    from lumenis.shared.reporting.media_brief import _select_collected_media_formats
    formats=[_declared_format('unknown-4k',height=2160),
        _declared_format('over-budget-1080',height=1080,filesize=600000),
        _declared_format('muxed-720',height=720,filesize=100000),
        _declared_format('paired-1080',audio=False,height=1080,filesize=10000),
        _declared_format('audio',video=False,filesize=1000)]
    selected,budget,coverage=_select_collected_media_formats({'formats':formats},'video',200000)
    assert [item['selection_id'] for item in selected]==['muxed-720']
    assert budget['unknown_size_count']==1 and coverage['stream_coverage']=='COMPLETE_REQUESTED_STREAMS'
    selected,budget,coverage=_select_collected_media_formats({'formats':[formats[0]]},'video',1000)
    assert selected[0]['selection_id']=='unknown-4k'
    assert budget['selected_required_bytes'] is None and budget['state']=='UNKNOWN_SIZE_BOUNDED_TRANSFER'


def test_complete_pair_cannot_drop_audio_to_fit_and_drm_or_other_entry_never_selected():
    from lumenis.shared.reporting.media_brief import _select_collected_media_formats,_CollectedMediaBudgetRequired
    video=_declared_format('native-video',audio=False,filesize=10000)
    audio=_declared_format('native-audio',video=False,filesize=100000)
    with pytest.raises(_CollectedMediaBudgetRequired) as error:
        _select_collected_media_formats({'formats':[video,audio]},'video',100000)
    assert error.value.required_bytes>100000
    drm=_declared_format('protected',height=2160,filesize=1,has_drm=True)
    selected,_,_=_select_collected_media_formats({'formats':[drm,_declared_format('clear',filesize=100)]},'video',1000)
    assert [item['selection_id'] for item in selected]==['clear']
    with pytest.raises(ValueError,match='MULTIPLE_ENTRIES'):
        _select_collected_media_formats({'formats':[video,{**audio,'native_locator':{'entry_index':1}}]},'video',1000000)
    with pytest.raises(ValueError,match='NO_UNENCRYPTED_FORMAT'):
        _select_collected_media_formats({'formats':[drm]},'video',1000)


def test_standalone_and_unknown_tracks_keep_partial_stream_coverage():
    from lumenis.shared.reporting.media_brief import _select_collected_media_formats
    video=_declared_format('silent-native',audio=False,filesize=1000)
    _,budget,coverage=_select_collected_media_formats({'formats':[video]},'video',2000)
    assert coverage['has_audio'] is False and coverage['has_video'] is True
    assert coverage['stream_coverage']=='OBSERVED_TRACKS_ONLY_STREAM_COVERAGE_UNKNOWN_OR_PARTIAL'
    unknown=_declared_format('unknown-streams',video=None,audio=None,filesize=None,tbr=True,duration=float('nan'))
    _,budget,coverage=_select_collected_media_formats({'formats':[unknown]},'video',2000)
    assert coverage['has_audio'] is None and coverage['has_video'] is None
    assert budget['estimates'][0]['estimated_bytes'] is None
    overflow={**unknown,'tbr':1e308,'duration':1e308}
    _,budget,_=_select_collected_media_formats({'formats':[overflow]},'video',2000)
    assert budget['selected_required_bytes'] is None and budget['state']=='UNKNOWN_SIZE_BOUNDED_TRANSFER'
    audio=_declared_format('audio-only',video=False,tbr=None,abr=64,duration=60)
    _,budget,coverage=_select_collected_media_formats({'formats':[audio]},'audio',1000000)
    assert budget['estimates'][0]['estimated_bytes']==480000 and coverage['stream_coverage']=='COMPLETE_REQUESTED_STREAMS'


def test_fetch_binds_only_budget_selected_pair_and_preserves_native_plan(monkeypatch,tmp_path):
    from lumenis.shared.reporting.media_brief import _fetch_collected_media
    from lumenis.system.collector.adapters import public_source as transport
    plan={'formats':[_declared_format('huge',audio=False,height=2160,filesize=10000000),
        _declared_format('fit',audio=False,height=720,filesize=200000),
        _declared_format('audio',video=False,filesize=10000)],'extractor':{'name':'yt-dlp'},
        'source_document_sha256':'a'*64,'plan_sha256':'b'*64}
    monkeypatch.setattr(transport,'extract_public_media',lambda *args,**kwargs:plan)
    calls=[]
    def fetch(source_plan,**kwargs):
        calls.append(kwargs)
        assert source_plan is plan and kwargs['selection_ids']==['fit','audio']
        assert kwargs['max_bytes']==400000 and kwargs['allow_segment_assembly'] is True
        return transport.PublicMediaResponse('https://example.test/observed.mpd','c'*64,200000,'video/mp4',200,
            'https://example.test/observed.mpd',extraction={'representation':'COPY_MUXED_NATIVE_TRACKS','components':[]})
    monkeypatch.setattr(transport,'fetch_extracted_public_media',fetch)
    _,extraction=_fetch_collected_media({'url':'https://example.test/observed.mpd','kind':'video',
        'acquisition':{'representation':'STREAM_MANIFEST'}},destination=tmp_path/'original.mp4',
        max_bytes=400000,check_continue=lambda:None)
    assert len(calls)==1 and extraction['source_plan'] is plan
    assert extraction['selection_budget']['selected_required_bytes']<=400000
    assert extraction['selection_coverage']['has_audio'] is True


@pytest.mark.parametrize('insufficient_whole_step',[False,True])
def test_format_budget_distinguishes_step_continuation_from_resource_intervention(media_case,monkeypatch,insufficient_whole_step):
    case,owner=media_case,media_case['media_owner']
    urls,_=_media_inventory(case,monkeypatch,3)
    size=len(case['media_raw'])
    monkeypatch.setattr(owner,'_COLLECTED_MEDIA_BYTES',size-1 if insufficient_whole_step else 2*size-1)
    native_fetch=owner._fetch_collected_media
    def fetch(media,**kwargs):
        owner._select_collected_media_formats({'formats':[_declared_format('whole-original',filesize=size)]},
            'video',kwargs['max_bytes'])
        return native_fetch(media,**kwargs)
    monkeypatch.setattr(owner,'_fetch_collected_media',fetch)
    args=_confirm(case)
    job='media-format-resource-001' if insufficient_whole_step else 'media-format-step-001'
    result=owner.process_collected_media(**args,job_id=job)
    if insufficient_whole_step:
        assert result['failed_positions']==[0] and result['pending_positions']==[1,2]
        assert result['intervention_required'] and not result['auto_continue'] and not case['media_calls']
        assert result['media'][0]['failure_class']=='RESOURCE'
        assert result['media'][0]['selection_budget']['minimum_required_bytes']==size
    else:
        assert result['auto_continue'] and not result['failed_positions'] and result['pending_positions']==[1,2]
        assert result['media'][1]['reason']=='MEDIA_STEP_BUDGET'
        second=owner.process_collected_media(**args,job_id=job)
        assert second['auto_continue'] and second['pending_positions']==[2]
        final=owner.process_collected_media(**args,job_id=job)
        assert final['ok'] and case['media_calls']==urls
