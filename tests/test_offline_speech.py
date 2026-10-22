"""Unit and real installed-FFmpeg integration; not a naturalness/user E2E claim."""
from __future__ import annotations

import hashlib
import io
import json
import os
import struct
import subprocess
import sys
import wave
from array import array
from pathlib import Path

import pytest

from lumenis.shared.content_creation import offline_speech as speech
from lumenis.shared.content_creation import rendering
from lumenis.shared.content_creation.video_editing import VideoEditingError


@pytest.fixture
def ffmpeg():
    from shared_artifacts import _ffmpeg_path
    binary = _ffmpeg_path()
    if not binary:
        pytest.skip("requires the existing FFmpeg executable")
    help_text = subprocess.run([binary, "-hide_banner", "-h", "filter=flite"],
                               capture_output=True, text=True, timeout=10, check=True)
    if "Synthesize voice from text using libflite" not in help_text.stdout:
        pytest.skip("this installed FFmpeg build does not include libflite")
    return binary


def _pcm_wav(samples=(0, 1000, -2000, 3000), *, rate=speech.SAMPLE_RATE, channels=1):
    pcm = struct.pack("<" + "h" * len(samples), *samples)
    output = io.BytesIO()
    with wave.open(output, "wb") as stream:
        stream.setparams((channels, 2, rate, 0, "NONE", "not compressed"))
        stream.writeframes(pcm)
    return output.getvalue(), pcm


def _fake_runner(monkeypatch, *, mutate=None):
    """A deterministic failure-injection runner, never evidence of real TTS."""
    import shared_artifacts
    monkeypatch.setattr(shared_artifacts, "_ffmpeg_path", lambda: "/installed/ffmpeg")
    commands, directories = [], []
    wav, pcm = _pcm_wav()

    def run(command, *, cwd, timeout, check_continue):
        commands.append(command)
        directories.append(cwd)
        check_continue()
        if command[-1] == "speech.wav":
            (cwd / "speech.wav").write_bytes(wav)
        else:
            (cwd / "decoded.pcm").write_bytes(pcm)
        if mutate:
            mutate(command, cwd, check_continue)
        check_continue()
        return "ffmpeg version test-only\n"

    monkeypatch.setattr(rendering, "_run", run)
    return commands, directories


@pytest.mark.parametrize("voice", speech.SUPPORTED_VOICES)
def test_all_builtin_voices_produce_real_complete_pcm(ffmpeg, tmp_path, voice):
    text = "This is an optional local voiceover. The full sentence is synthesized."
    result = speech.synthesize_offline_speech(text, voice=voice)
    assert set(result) == {"files", "report"}
    assert set(result["files"]) == {"speech.wav", "speech.json"}
    report = result["report"]
    assert report == json.loads(result["files"]["speech.json"])
    assert report["voice"] == voice
    assert report["engine"] == "ffmpeg_libflite"
    assert report["engine_ownership"] == "third_party"
    assert report["source"]["text"] == text
    assert report["source"]["sha256"] == hashlib.sha256(text.encode()).hexdigest()
    assert report["source"]["canonical_fact"] is False
    assert report["synthetic"] is True
    assert report["voice_cloned"] is report["external_network_used"] is False
    assert report["automatic_model_download"] is report["published"] is False
    assert report["text_truncated"] is report["audio_trimmed"] is False
    assert report["word_boundaries"] == "unavailable"
    assert report["naturalness"] == report["pronunciation_accuracy"] == "NOT_EVALUATED"
    assert report["label"]["zh"] == "AI 配音"
    assert report["runtime"]["ffmpeg_version_line"].startswith("ffmpeg version ")
    assert str(tmp_path) not in json.dumps(report)
    audio = result["files"]["speech.wav"]
    with wave.open(io.BytesIO(audio), "rb") as stream:
        assert (stream.getframerate(), stream.getnchannels(), stream.getsampwidth()) == (16000, 1, 2)
        assert stream.getcomptype() == "NONE"
        count = stream.getnframes()
        raw = stream.readframes(count + 1)
    assert len(raw) == count * 2
    assert report["audio"]["decoded_samples_per_channel"] == count
    assert report["audio"]["duration_sec"] == count / 16000
    assert 1 < report["audio"]["duration_sec"] < 30
    assert report["audio"]["pcm_sha256"] == hashlib.sha256(raw).hexdigest()
    samples = array("h")
    samples.frombytes(raw)
    if sys.byteorder != "little":
        samples.byteswap()
    assert report["audio"]["sample_peak"] == max(abs(value) for value in samples) / 32768
    assert report["audio"]["sample_peak"] > 0
    assert report["audio"]["clipped_samples"] == sum(value in (-32768, 32767) for value in samples)
    assert report["audio"]["full_decode"] == report["audio"]["full_pcm_comparison"] == "passed"
    metadata = report["outputs"]["speech.wav"]
    assert metadata["size_bytes"] == len(audio)
    assert metadata["sha256"] == hashlib.sha256(audio).hexdigest()
    path = tmp_path / "speech.wav"
    path.write_bytes(audio)
    independent = subprocess.run([
        ffmpeg, "-v", "error", "-xerror", "-nostdin", "-i", str(path),
        "-map", "0:a:0", "-c:a", "pcm_s16le", "-f", "s16le", "pipe:1",
    ], capture_output=True, check=True, timeout=20, shell=False).stdout
    assert independent == raw


def test_real_input_tail_changes_output_and_is_not_truncated(ffmpeg):
    first = speech.synthesize_offline_speech("One short sentence.")
    text = "One short sentence.\nThe second sentence must also be spoken, completely."
    second = speech.synthesize_offline_speech(text)
    assert second["report"]["source"]["text"] == text
    assert second["report"]["audio"]["duration_sec"] > first["report"]["audio"]["duration_sec"] + 1
    assert second["files"]["speech.wav"] != first["files"]["speech.wav"]


def test_real_filter_metacharacters_remain_literal_text(ffmpeg):
    text = "Let's say [a], colon: one percent %, backslash \\, and semicolon; literally."
    result = speech.synthesize_offline_speech(text)
    assert result["report"]["source"]["text"] == text
    assert result["report"]["audio"]["full_decode"] == "passed"


def test_literal_textfile_never_interpolates_filter_or_shell_and_is_cleaned(monkeypatch):
    text = "  Literal ' : ; [0:a] amovie=https://example.invalid/x | $(touch bad) \\ %\nLast line.\r\n"
    contents = []

    def inspect(command, cwd, callback):
        contents.append((cwd / "speech.txt").read_bytes())
        if os.name == "nt":
            acl_command = r"""
$ErrorActionPreference = 'Stop'
$identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$items = @($env:OEVIRA_SPEECH_TEMP, (Join-Path $env:OEVIRA_SPEECH_TEMP 'speech.txt'))
@($items | ForEach-Object {
  $acl = if ([System.IO.Directory]::Exists($_)) {
    [System.IO.Directory]::GetAccessControl($_)
  } else { [System.IO.File]::GetAccessControl($_) }
  @{owner=$acl.GetOwner([System.Security.Principal.SecurityIdentifier]).Value;
    user=$identity;
    entries=@($acl.GetAccessRules($true,$true,[System.Security.Principal.SecurityIdentifier]) | ForEach-Object {
      @{sid=$_.IdentityReference.Value; type=$_.AccessControlType.ToString(); rights=[int]$_.FileSystemRights}
    })}
}) | ConvertTo-Json -Depth 4 -Compress
"""
            inspected = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", acl_command],
                env={**os.environ, "OEVIRA_SPEECH_TEMP": str(cwd)},
                capture_output=True, text=True, check=True, timeout=15, shell=False,
            )
            for acl in json.loads(inspected.stdout):
                allowed = {acl["user"], "S-1-5-18", "S-1-5-32-544"}
                grants = [entry for entry in acl["entries"] if entry["type"] == "Allow"]
                for entry in grants:
                    if entry["sid"] == "S-1-3-4":
                        entry["sid"] = acl["owner"]
                assert acl["owner"] in allowed
                assert grants and all(entry["sid"] in allowed for entry in grants)
                assert any(entry["sid"] == acl["owner"] and entry["rights"] & 1 for entry in grants)
        else:
            assert (cwd / "speech.txt").stat().st_mode & 0o077 == 0
            assert cwd.stat().st_mode & 0o077 == 0
        assert text not in " ".join(command)
        assert "https://" not in " ".join(command)
        assert all(flag not in command for flag in ("-t", "-fs", "-frames:a", "-af"))
        assert "-protocol_whitelist" in command

    commands, directories = _fake_runner(monkeypatch, mutate=inspect)
    result = speech.synthesize_offline_speech(text)
    assert contents == [text.encode(), text.encode()]
    assert commands[0][commands[0].index("-i") + 1] == "flite=textfile=speech.txt:voice=slt"
    assert result["report"]["source"]["text"] == text
    assert all(not directory.exists() for directory in directories)


@pytest.mark.parametrize("changes,code", [
    ({"text": ""}, "TTS_TEXT_INVALID"), ({"text": " \n\t"}, "TTS_TEXT_INVALID"),
    ({"text": None}, "TTS_TEXT_INVALID"), ({"text": []}, "TTS_TEXT_INVALID"),
    ({"text": True}, "TTS_TEXT_INVALID"), ({"text": "... ;!?"}, "TTS_TEXT_INVALID"),
    ({"text": "a" * (speech.MAX_TEXT_CHARACTERS + 1)}, "TTS_TEXT_INVALID"),
    ({"text": "hello\x00hidden"}, "TTS_TEXT_INVALID"),
    ({"text": "hello\x1bhidden"}, "TTS_TEXT_INVALID"),
    ({"text": "hello\x7fhidden"}, "TTS_TEXT_INVALID"),
    ({"text": "hello\u202ehidden"}, "TTS_TEXT_INVALID"),
    ({"text": "hello\ud800"}, "TTS_TEXT_INVALID"),
    ({"text": "中文配音"}, "TTS_LANGUAGE_UNAVAILABLE"),
    ({"text": "Hello, 中文"}, "TTS_LANGUAGE_UNAVAILABLE"),
    ({"text": "caf\u00e9"}, "TTS_LANGUAGE_UNAVAILABLE"),
    ({"language": "zh"}, "TTS_LANGUAGE_UNAVAILABLE"),
    ({"language": "en-GB"}, "TTS_LANGUAGE_UNAVAILABLE"),
    ({"language": []}, "TTS_LANGUAGE_UNAVAILABLE"),
    ({"voice": "slt:amovie=x"}, "TTS_VOICE_UNAVAILABLE"),
    ({"voice": "../../slt"}, "TTS_VOICE_UNAVAILABLE"),
    ({"voice": "https://example.invalid/model"}, "TTS_VOICE_UNAVAILABLE"),
    ({"voice": "clone"}, "TTS_VOICE_UNAVAILABLE"),
    ({"voice": []}, "TTS_VOICE_UNAVAILABLE"),
])
def test_bad_inputs_fail_before_runtime(monkeypatch, changes, code):
    import shared_artifacts
    monkeypatch.setattr(shared_artifacts, "_ffmpeg_path", lambda: pytest.fail("invalid input reached runtime"))
    args = {"text": "Safe English text."}
    args.update(changes)
    with pytest.raises(VideoEditingError, match="^" + code + "$"):
        speech.synthesize_offline_speech(**args)


def test_exact_text_boundary_is_preserved(monkeypatch):
    _fake_runner(monkeypatch)
    text = "A" * speech.MAX_TEXT_CHARACTERS
    result = speech.synthesize_offline_speech(text, language="en-US")
    assert result["report"]["source"]["text"] == text
    assert result["report"]["source"]["characters"] == speech.MAX_TEXT_CHARACTERS


def test_missing_runtime_is_explicit(monkeypatch):
    import shared_artifacts
    monkeypatch.setattr(shared_artifacts, "_ffmpeg_path", lambda: None)
    with pytest.raises(VideoEditingError, match="^TTS_RUNTIME_UNAVAILABLE$"):
        speech.synthesize_offline_speech("Safe English text.")


@pytest.mark.parametrize("stage", ["speech.wav", "decoded.pcm"])
def test_failed_synthesis_or_decode_cleans_private_files(monkeypatch, stage):
    directories = []

    def fail(command, cwd, callback):
        directories.append(cwd)
        if command[-1] == stage:
            raise VideoEditingError("MEDIA_RENDER_FAILED")

    _fake_runner(monkeypatch, mutate=fail)
    expected = "TTS_SYNTHESIS_FAILED" if stage == "speech.wav" else "TTS_DECODE_FAILED"
    with pytest.raises(VideoEditingError, match=expected):
        speech.synthesize_offline_speech("Safe English text.")
    assert directories and all(not directory.exists() for directory in directories)


def test_decoded_mismatch_is_not_success(monkeypatch):
    def corrupt(command, cwd, callback):
        if command[-1] == "decoded.pcm":
            (cwd / "decoded.pcm").write_bytes(b"corrupt")
    _, directories = _fake_runner(monkeypatch, mutate=corrupt)
    with pytest.raises(VideoEditingError, match="TTS_DECODE_MISMATCH"):
        speech.synthesize_offline_speech("Safe English text.")
    assert all(not directory.exists() for directory in directories)


@pytest.mark.parametrize("stage,limit", [("speech.wav", "MAX_WAV_BYTES"), ("decoded.pcm", "MAX_PCM_BYTES")])
def test_byte_limits_reject_whole_result_instead_of_truncating(monkeypatch, stage, limit):
    monkeypatch.setattr(speech, limit, 100)

    def oversize(command, cwd, callback):
        if command[-1] == stage:
            (cwd / stage).write_bytes(b"x" * 101)

    _, directories = _fake_runner(monkeypatch, mutate=oversize)
    with pytest.raises(VideoEditingError, match="TTS_AUDIO_LIMIT_EXCEEDED"):
        speech.synthesize_offline_speech("Safe English text.")
    assert all(not directory.exists() for directory in directories)


@pytest.mark.parametrize("error_class", [RuntimeError, OSError, VideoEditingError])
def test_callback_error_preserved_and_files_cleaned(monkeypatch, error_class):
    expected = error_class("user cancelled or permission revoked")
    paths = []

    def mark_started(command, cwd, callback):
        paths.append(cwd)

    _fake_runner(monkeypatch, mutate=mark_started)

    def cancel():
        if paths:
            raise expected

    with pytest.raises(error_class) as caught:
        speech.synthesize_offline_speech("Safe English text.", check_cancel=cancel)
    assert caught.value is expected
    assert paths and all(not path.exists() for path in paths)


def test_cancellation_before_start_invokes_no_runtime(monkeypatch):
    import shared_artifacts
    monkeypatch.setattr(shared_artifacts, "_ffmpeg_path", lambda: pytest.fail("started despite cancellation"))
    def cancel():
        raise RuntimeError("cancelled")
    with pytest.raises(RuntimeError, match="cancelled"):
        speech.synthesize_offline_speech("Safe English text.", check_cancel=cancel)


def test_real_running_encoder_is_reaped_on_cancel(ffmpeg, monkeypatch):
    real_popen = rendering.subprocess.Popen
    processes, directories = [], []

    def record(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        processes.append(process)
        directories.append(Path(kwargs["cwd"]))
        return process

    monkeypatch.setattr(rendering.subprocess, "Popen", record)
    expected = RuntimeError("cancel running speech")
    def cancel():
        if processes:
            raise expected

    with pytest.raises(RuntimeError) as caught:
        speech.synthesize_offline_speech("This is a longer local speech. " * 50, check_cancel=cancel)
    assert caught.value is expected
    assert len(processes) == 1 and processes[0].poll() is not None
    assert all(not directory.exists() for directory in directories)


def test_real_synthesis_timeout_fails_and_reaps_process(ffmpeg, monkeypatch):
    real_popen = rendering.subprocess.Popen
    processes, directories = [], []

    def record(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        processes.append(process)
        directories.append(Path(kwargs["cwd"]))
        return process

    monkeypatch.setattr(rendering.subprocess, "Popen", record)
    monkeypatch.setattr(speech, "SYNTHESIS_TIMEOUT_SECONDS", 0)
    with pytest.raises(VideoEditingError, match="TTS_SYNTHESIS_FAILED"):
        speech.synthesize_offline_speech("This complete sentence must never be returned partially.")
    assert len(processes) == 1 and processes[0].poll() is not None
    assert all(not directory.exists() for directory in directories)


@pytest.mark.parametrize("mutation", ["truncated", "wrong_rate", "stereo", "empty", "bad_riff", "duration"])
def test_invalid_pcm_rejected(monkeypatch, mutation):
    wav, _ = _pcm_wav()
    if mutation == "truncated":
        wav = wav[:-1]
    elif mutation == "wrong_rate":
        wav, _ = _pcm_wav(rate=8000)
    elif mutation == "stereo":
        wav, _ = _pcm_wav(channels=2)
    elif mutation == "empty":
        wav, _ = _pcm_wav(samples=())
    elif mutation == "bad_riff":
        wav = b"RF64" + wav[4:]
    elif mutation == "duration":
        monkeypatch.setattr(speech, "MAX_AUDIO_SECONDS", 0)
    with pytest.raises(VideoEditingError, match="TTS_AUDIO_INVALID"):
        speech._read_pcm(wav)


def test_silent_audio_rejected(monkeypatch):
    wav, pcm = _pcm_wav(samples=(0, 0, 0, 0))
    def silence(command, cwd, callback):
        (cwd / command[-1]).write_bytes(wav if command[-1] == "speech.wav" else pcm)
    _, directories = _fake_runner(monkeypatch, mutate=silence)
    with pytest.raises(VideoEditingError, match="TTS_AUDIO_SILENT"):
        speech.synthesize_offline_speech("Safe English text.")
    assert all(not directory.exists() for directory in directories)
