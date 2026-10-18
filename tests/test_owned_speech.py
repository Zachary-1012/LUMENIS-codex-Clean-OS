"""Hermetic boundary/recovery tests; simulated decoder output is not ASR accuracy."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import time
import wave

import pytest

import importlib.util

# Standalone owner code uses only stdlib before the pinned worker starts.
# This also allows testing a frozen follow-on outside a full product checkout.
_source = Path(__file__).resolve().parents[1] / "lumenis/system/ai_gateway/owned_speech.py"
_spec = importlib.util.spec_from_file_location("owned_speech_under_test", _source)
speech = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = speech
_spec.loader.exec_module(speech)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_transcript():
    return {"text": " uncertain name", "language": "en", "segments": [
        {"id": 0, "start": 0.0, "end": 0.9, "text": " uncertain name",
         "avg_logprob": -0.2, "compression_ratio": 1.0, "no_speech_prob": 0.1,
         "words": [{"word": " uncertain", "start": 0.0, "end": 0.5, "probability": 0.6},
                   {"word": " name", "start": 0.5, "end": 0.9, "probability": 0.99}]}]}


@pytest.fixture
def local_candidate(tmp_path, monkeypatch):
    audio = tmp_path / "audio.wav"
    with wave.open(str(audio), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\x00\x00" * 16000)
    paths = {}
    for name in ("python", "manifest", "weight", "ffmpeg"):
        path = tmp_path / name
        path.write_bytes(("test fixture " + name).encode())
        paths[name] = path
    # This deliberately disposable stand-in verifies process boundaries only.
    monkeypatch.setattr(speech, "WEIGHT_SHA256", digest(paths["weight"]))
    runtime = speech.SpeechRuntime(str(paths["python"]), digest(paths["python"]),
                                   str(paths["manifest"]), digest(paths["manifest"]),
                                   str(paths["weight"]), str(paths["ffmpeg"]), digest(paths["ffmpeg"]))
    return audio, runtime, paths


def test_derivative_retains_uncertainty_and_actual_intervals():
    raw = raw_transcript()
    before = copy.deepcopy(raw)
    result = speech.validate_transcript(raw, duration_seconds=1)
    assert raw == before
    assert result["review_state"] == "UNREVIEWED"
    decoded = speech._strict_json(speech._transcript_wire_bytes(raw, duration_seconds=1))
    assert type(decoded["segments"][0]["start"]) is float
    assert decoded == raw
    assert result["speaker_identity"] == "UNKNOWN"
    assert result["semantic_correctness"] == "REVIEW_REQUIRED"
    assert result["warnings"] == [{"segment_id": 0, "start": 0.0, "end": 0.5,
                                  "word": " uncertain", "reason": "LOW_DECODER_WORD_PROBABILITY"}]
    assert result["decoder_probabilities_are_accuracy"] is False


@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), "0.0", object()])
def test_wire_boundary_does_not_coerce_invalid_native_numbers(value):
    raw = raw_transcript()
    raw["segments"][0]["start"] = value
    with pytest.raises(speech.SpeechBlocked):
        speech._transcript_wire_bytes(raw, duration_seconds=1)


@pytest.mark.parametrize("mutation", [
    lambda raw: raw["segments"][0].update(start=-0.1),
    lambda raw: raw["segments"][0].update(start=False),
    lambda raw: raw["segments"][0].update(end=1.5),
    lambda raw: raw["segments"][0].update(id=False),
    lambda raw: raw["segments"][0].update(avg_logprob=float("nan")),
    lambda raw: raw["segments"][0].update(avg_logprob=True),
    lambda raw: raw["segments"][0].update(no_speech_prob=1.01),
    lambda raw: raw["segments"][0]["words"][1].update(start=0.2),
    lambda raw: raw["segments"][0]["words"][1].update(probability=-0.2),
    lambda raw: raw["segments"][0]["words"][1].update(probability=True),
    lambda raw: raw["segments"][0].pop("words"),
    lambda raw: raw.update(text="silently corrected"),
    lambda raw: raw.update(language="invented-language"),
])
def test_invalid_decoder_result_is_rejected_without_clamping(mutation):
    raw = raw_transcript()
    mutation(raw)
    with pytest.raises(speech.SpeechBlocked):
        speech.validate_transcript(raw, duration_seconds=1)


def test_no_recognized_speech_is_explicit():
    result = speech.validate_transcript({"text": "", "language": "en", "segments": []}, duration_seconds=1)
    assert result["review_state"] == "NO_RECOGNIZED_SPEECH"


def test_native_decoder_floats_retain_values_and_pass_finite_interval_checks():
    class DecoderFloat(float):
        pass

    raw = raw_transcript()
    raw["segments"][0]["start"] = DecoderFloat(0.0)
    raw["segments"][0]["avg_logprob"] = DecoderFloat(-0.2)
    raw["segments"][0]["words"][0]["probability"] = DecoderFloat(0.6)
    before = copy.deepcopy(raw)
    result = speech.validate_transcript(raw, duration_seconds=1)
    assert type(raw["segments"][0]["start"]) is DecoderFloat
    assert raw == before
    assert result["review_state"] == "UNREVIEWED"
    decoded = speech._strict_json(speech._transcript_wire_bytes(raw, duration_seconds=1))
    assert type(decoded["segments"][0]["start"]) is float
    assert decoded == raw


@pytest.mark.parametrize("raw", [b'{"text":"a","text":"b"}', b'{"metric":NaN}', b'not json'])
def test_duplicate_nonfinite_and_malformed_json_are_blocked(raw):
    with pytest.raises(speech.SpeechBlocked):
        speech._strict_json(raw)


def test_missing_or_tampered_assets_never_spawn(local_candidate, monkeypatch):
    audio, runtime, paths = local_candidate
    original_sha = digest(audio)
    monkeypatch.setattr(speech.subprocess, "Popen", lambda *a, **k: pytest.fail("must not spawn"))
    paths["weight"].write_bytes(b"tampered")
    with pytest.raises(speech.SpeechBlocked, match="HASH_MISMATCH"):
        speech.transcribe_audio(str(audio), expected_audio_sha256=original_sha, runtime=runtime)
    with pytest.raises(speech.SpeechBlocked, match="MISSING"):
        speech.transcribe_audio(str(audio.parent / "missing.wav"), expected_audio_sha256=original_sha, runtime=runtime)


def test_changed_or_truncated_audio_is_not_accepted(local_candidate):
    audio, _runtime, _paths = local_candidate
    original_sha = digest(audio)
    audio.write_bytes(audio.read_bytes()[:-2])
    with pytest.raises(speech.SpeechBlocked, match="CHANGED"):
        speech._wav_bytes(audio, original_sha)
    with pytest.raises(speech.SpeechBlocked, match="TRUNCATED"):
        speech._wav_bytes(audio, digest(audio))


@pytest.mark.parametrize("language_hint", [None,*sorted(speech.CONTENT_LANGUAGE_CODES)])
def test_pipeline_has_no_script_prompt_download_or_fallback(local_candidate, monkeypatch, language_hint):
    audio, runtime, _paths = local_candidate
    calls = []

    def run(command, payload, **kwargs):
        calls.append((command, payload))
        if len(calls) == 1:
            assert command[command.index("-protocol_whitelist") + 1] == "pipe"
            assert "pipe:0" in command and audio.read_bytes() == payload
            return b"\x00" * (16000 * 4)
        spec, _samples = payload.split(b"\n", 1)
        assert set(json.loads(spec)) == {"manifest_path", "manifest_sha256", "weight_path", "duration_seconds", "language_hint"}
        assert json.loads(spec)["language_hint"] == language_hint
        assert command[1] == "-I" and command[-1] == "--worker"
        return json.dumps(raw_transcript()).encode()

    monkeypatch.setattr(speech, "_communicate", run)
    result = speech.transcribe_audio(str(audio), expected_audio_sha256=digest(audio), runtime=runtime,
                                     source_ref="source:caller-locator",language_hint=language_hint)
    assert result["source_ref_authenticated_by_adapter"] is False
    assert result["declared_language"] == language_hint
    assert result["language_selection"] == ("user_declared" if language_hint else "automatic")
    assert result["rights_state"] == "UNKNOWN"
    assert result["fallback_allowed"] is False
    assert result["script_or_target_supplied"] is False
    assert result["promotion_status"] == "NOT_PROMOTED"
    assert result["product_acceptance"] is False
    assert result["transcript"] == raw_transcript()


def test_audio_changed_during_recognition_returns_no_result(local_candidate, monkeypatch):
    audio, runtime, _paths = local_candidate
    original_sha = digest(audio)
    calls = 0

    def run(*_args, **_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return b"\x00" * 64000
        audio.write_bytes(b"modified during inference")
        return json.dumps(raw_transcript()).encode()

    monkeypatch.setattr(speech, "_communicate", run)
    with pytest.raises(speech.SpeechBlocked, match="HASH_MISMATCH"):
        speech.transcribe_audio(str(audio), expected_audio_sha256=original_sha, runtime=runtime)


def test_cancelled_invocation_does_not_spawn_or_persist(local_candidate, monkeypatch):
    audio, runtime, paths = local_candidate
    monkeypatch.setattr(speech.subprocess, "Popen", lambda *a, **k: pytest.fail("must not spawn"))
    before = {path.name: path.read_bytes() for path in paths.values()}
    with pytest.raises(speech.SpeechCancelled):
        speech.transcribe_audio(str(audio), expected_audio_sha256=digest(audio), runtime=runtime,
                                is_cancelled=lambda: True)
    assert before == {path.name: path.read_bytes() for path in paths.values()}


def test_real_subprocess_is_cancelled_and_retry_starts_cleanly():
    started = time.monotonic()
    with pytest.raises(speech.SpeechCancelled):
        speech._communicate([sys.executable, "-I", "-c", "import time; time.sleep(10)"], b"",
                            cancelled=lambda: time.monotonic() - started > 0.1, deadline=started + 5)
    assert time.monotonic() - started < 5
    assert speech._communicate([sys.executable, "-I", "-c", "print('recovered')"], b"",
                               cancelled=lambda: False, deadline=time.monotonic() + 5).strip() == b"recovered"


def test_actual_subprocess_timeout_and_failure_are_not_success():
    with pytest.raises(speech.SpeechBlocked, match="TIMEOUT"):
        speech._communicate([sys.executable, "-I", "-c", "import time; time.sleep(10)"], b"",
                            cancelled=lambda: False, deadline=time.monotonic() + 0.1)
    with pytest.raises(speech.SpeechBlocked, match="WORKER_FAILED"):
        speech._communicate([sys.executable, "-I", "-c", "raise SystemExit(7)"], b"",
                            cancelled=lambda: False, deadline=time.monotonic() + 5)


def test_observed_first_word_can_cross_segment_start_without_timestamp_or_text_edit():
    raw = raw_transcript()
    segment = raw["segments"][0]
    segment.update(start=142.24, end=147.56)
    segment["words"] = [{"word": " unreviewed", "start": 141.89999999999998,
                         "end": 142.26, "probability": 0.9177584648132324}]
    before = copy.deepcopy(raw)
    result = speech.validate_transcript(raw, duration_seconds=226.925)
    assert raw == before
    assert result["review_state"] == "UNREVIEWED"
    assert result["warnings"] == [{"segment_id": 0, "start": 141.89999999999998,
                                   "end": 142.26, "reason": "FIRST_WORD_CROSSES_SEGMENT_START_REVIEW_REQUIRED"}]


@pytest.mark.parametrize("start,end,probability,reason", [
    (-1, 0.3, 0.9, "INTERVAL"), (0.4, 0.3, 0.9, "INTERVAL"),
    (0.0, 2.0, 0.9, "INTERVAL"), (0.0, 0.3, -0.1, "PROBABILITY"),
    (0.0, 0.3, 1.1, "PROBABILITY"), (False, 0.3, 0.9, "VALUE"),
    (float("nan"), 0.3, 0.9, "VALUE"), (0.0, float("inf"), 0.9, "VALUE"),
])
def test_first_word_exception_does_not_admit_invalid_audio_intervals_or_probabilities(start, end, probability, reason):
    raw = raw_transcript()
    raw["segments"][0]["words"][0].update(start=start, end=end, probability=probability)
    with pytest.raises(speech.SpeechBlocked, match=reason):
        speech.validate_transcript(raw, duration_seconds=1)


def test_crossing_start_requires_first_word_to_reach_the_segment_start():
    raw = raw_transcript()
    raw["segments"][0]["start"] = 0.4
    raw["segments"][0]["words"][0].update(start=0.1, end=0.3)
    with pytest.raises(speech.SpeechBlocked, match="INTERVAL"):
        speech.validate_transcript(raw, duration_seconds=1)


def test_typed_failure_reason_is_allowlisted_and_raw_stderr_is_never_an_error():
    stderr = b"private material\n__main__.SpeechBlocked: SPEECH_WORD_INTERVAL_INVALID\n"
    error = speech._failed_process(["python", "-I", "owner.py", "--worker"], 1, stderr)
    assert str(error) == "SPEECH_WORD_INTERVAL_INVALID"
    assert error.diagnostic["exit_code"] == 1
    assert error.diagnostic["stderr_sha256"] == hashlib.sha256(stderr).hexdigest()
    assert "private" not in str(error) and "stderr" not in error.diagnostic
    assert str(speech._failed_process(["worker", "--worker"], 1,
               b"SpeechBlocked: NOT_APPROVED_REASON\n")) == "SPEECH_OFFLINE_WORKER_FAILED"
    assert str(speech._failed_process(["ffmpeg"], 1, stderr)) == "SPEECH_OFFLINE_WORKER_FAILED"


def test_slow_worker_reads_full_large_input_across_poll_timeouts():
    payload = b'\x01\x02\x03\x04' * 200000
    script = "import time,sys,hashlib; time.sleep(.6); print(hashlib.sha256(sys.stdin.buffer.read()).hexdigest())"
    checks = []
    output = speech._communicate([sys.executable, '-I', '-c', script], payload,
        cancelled=lambda: checks.append(time.monotonic()) or False, deadline=time.monotonic()+5)
    assert output.strip().decode() == hashlib.sha256(payload).hexdigest()
    assert len(checks) >= 3


def test_slow_large_input_worker_remains_cancellable():
    start=time.monotonic()
    with pytest.raises(speech.SpeechCancelled):
        speech._communicate([sys.executable,'-I','-c','import time,sys;time.sleep(10);sys.stdin.buffer.read()'],b'x'*800000,
            cancelled=lambda: time.monotonic()-start>.4,deadline=start+5)
    assert time.monotonic()-start<3


@pytest.mark.parametrize('hint',[True,[],{},'auto','zh-CN','../../ko'])
def test_invalid_declared_language_rejected_before_runtime(local_candidate,hint):
    audio,runtime,_=local_candidate
    with pytest.raises(speech.SpeechBlocked,match='DECLARED_LANGUAGE'):
        speech.transcribe_audio(str(audio),expected_audio_sha256=digest(audio),runtime=runtime,language_hint=hint)


@pytest.mark.parametrize('model_id',['openai/whisper-medium','small','',None,[],True])
def test_unadmitted_model_fails_before_assets(local_candidate,monkeypatch,model_id):
    from dataclasses import replace
    audio,runtime,_=local_candidate
    runtime=replace(runtime,model_id=model_id)
    monkeypatch.setattr(speech,'_local_file',lambda *a:pytest.fail('must reject before file access'))
    with pytest.raises(speech.SpeechBlocked,match='MODEL_NOT_ADMITTED'):
        speech.transcribe_audio(str(audio),expected_audio_sha256=digest(audio),runtime=runtime)


def test_explicit_small_binds_worker_and_report_without_changing_base(local_candidate,monkeypatch):
    from dataclasses import replace
    audio,runtime,paths=local_candidate
    original_default=speech.MODEL_ID
    monkeypatch.setitem(speech.EVALUATION_MODEL_HASHES,'openai/whisper-small',digest(paths['weight']))
    calls=[]
    def run(command,payload,**kwargs):
        calls.append(payload)
        if len(calls)==1:return b'\0'*(16000*4)
        spec=json.loads(payload.split(b'\n',1)[0]);assert spec['model_id']=='openai/whisper-small'
        return json.dumps(raw_transcript()).encode()
    monkeypatch.setattr(speech,'_communicate',run)
    result=speech.transcribe_audio(str(audio),expected_audio_sha256=digest(audio),runtime=replace(runtime,model_id='openai/whisper-small'))
    assert result['model_id']=='openai/whisper-small' and result['weight_sha256']==digest(paths['weight'])
    assert result['evaluation_candidate'] and result['promotion_status']=='NOT_PROMOTED'
    assert result['model_revision']==digest(paths['weight'])
    assert speech.MODEL_ID==original_default=='openai/whisper-base'


@pytest.mark.parametrize('hint',sorted(speech.CONTENT_LANGUAGE_CODES))
def test_worker_accepts_declared_languages_before_manifest_check(monkeypatch,hint):
    import io
    spec={'manifest_path':'/missing','manifest_sha256':'a'*64,'weight_path':'/missing','duration_seconds':1,'language_hint':hint}
    monkeypatch.setattr(sys,'stdin',type('Input',(),{'buffer':io.BytesIO(json.dumps(spec).encode()+b'\n')})())
    with pytest.raises(speech.SpeechBlocked,match='LOCAL_SPEECH_ASSET_MISSING'):speech._worker()


@pytest.mark.parametrize('hint',['EN','es-419','auto',' en',[],True])
def test_worker_rejects_invalid_languages_before_manifest(monkeypatch,hint):
    import io
    spec={'manifest_path':'/missing','manifest_sha256':'a'*64,'weight_path':'/missing','duration_seconds':1,'language_hint':hint}
    monkeypatch.setattr(sys,'stdin',type('Input',(),{'buffer':io.BytesIO(json.dumps(spec).encode()+b'\n')})())
    with pytest.raises(speech.SpeechBlocked,match='WORKER_CONTRACT_INVALID'):speech._worker()


def hpr_terminal_envelope_case():
    raw=raw_transcript();s=raw['segments'][0]
    s.update(start=0.0,end=6.72,text=' there.',words=[{'word':' there.','start':6.52,'end':6.82,'probability':.9849562048912048}])
    raw['text']=' there.'
    return raw


def test_hpr_terminal_word_outside_segment_is_preserved_with_pinned_warning():
    raw=hpr_terminal_envelope_case();before=copy.deepcopy(raw)
    result=speech.validate_transcript(raw,duration_seconds=60)
    assert raw==before and result['transcript']==before
    warning=next(w for w in result['warnings'] if w['reason']=='LAST_WORD_CROSSES_SEGMENT_END_REVIEW_REQUIRED')
    assert warning['segment_end']==6.72 and warning['end']==6.82 and warning['word_index']==0
    assert warning['word_values_modified'] is False and warning['applicability']=='openai-whisper==20250625'
    assert result['review_state']=='UNREVIEWED'


@pytest.mark.parametrize('mutation',[
    lambda r:r['segments'][0]['words'][0].update(start=6.0), # terminal duration>.7
    lambda r:r['segments'][0]['words'][0].update(start=6.73), # wholly after segment
    lambda r:r['segments'][0]['words'][0].update(end=60.01), # actual audio bound
    lambda r:r['segments'][0]['words'][0].update(start=float('nan')),
    lambda r:r['segments'][0]['words'][0].update(end=float('inf')),
    lambda r:r['segments'][0]['words'][0].update(start=6.9), # reversed
    lambda r:r['segments'][0]['words'].append({'word':' next','start':6.83,'end':6.9,'probability':.9}), # nonterminal overflow
])
def test_terminal_envelope_does_not_admit_invalid_geometry(mutation):
    raw=hpr_terminal_envelope_case();mutation(raw)
    with pytest.raises(speech.SpeechBlocked):speech.validate_transcript(raw,duration_seconds=60)


def test_terminal_envelope_rejects_crossing_next_segment():
    raw=hpr_terminal_envelope_case();s=copy.deepcopy(raw['segments'][0]);s.update(id=1,start=6.75,end=7.2,text=' next',words=[{'word':' next','start':6.9,'end':7.2,'probability':.9}]);raw['segments'].append(s);raw['text']+=' next'
    with pytest.raises(speech.SpeechBlocked,match='INTERVAL'):speech.validate_transcript(raw,duration_seconds=60)


def test_first_word_crossing_rejects_previous_segment_overlap():
    raw=raw_transcript();raw['segments'][0]['words'][-1]['end']=.9
    s=copy.deepcopy(raw['segments'][0]);s.update(id=1,start=1.0,end=1.4,text=' next',words=[{'word':' next','start':.8,'end':1.2,'probability':.9}]);raw['segments'].append(s);raw['text']+=' next'
    with pytest.raises(speech.SpeechBlocked,match='INTERVAL'):speech.validate_transcript(raw,duration_seconds=2)


def test_word_exceeding_audio_by_point_zero_one_is_rejected():
    raw=raw_transcript();raw['segments'][0]['end']=1.01;raw['segments'][0]['words'][-1]['end']=1.01
    with pytest.raises(speech.SpeechBlocked,match='INTERVAL'):speech.validate_transcript(raw,duration_seconds=1)
