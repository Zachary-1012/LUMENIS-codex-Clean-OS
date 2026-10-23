"""Optional, local English speech for the existing Shared media owner.

This is a bounded adapter to an *already installed* FFmpeg/libflite, not a
LUMENIS-owned model, model downloader, voice-cloning service or Artifact store.
The caller owns explicit user selection, scope, text rights and persistence.
Missing dependencies fail; there is no external service or model fallback.

References reviewed for this adapter:
https://ffmpeg.org/ffmpeg-filters.html#flite
https://github.com/festvox/flite/blob/v2.2/COPYING
https://github.com/festvox/flite/tree/v2.2/lang
Flite code and bundled voice data retain their upstream notices. This adapter
does not redistribute the engine/voice data; redistributing an FFmpeg binary
requires a separate review of that exact build's LGPL/GPL and other notices.
"""
from __future__ import annotations

from array import array
import hashlib
import io
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
from typing import Any, Callable
import unicodedata
import wave

from . import rendering
from .video_editing import VideoEditingError


def speech_capabilities() -> dict:
    from shared_artifacts import _ffmpeg_path
    engines = []
    ffmpeg = _ffmpeg_path()
    voices = []
    if ffmpeg:
        try:
            result = subprocess.run(
                [ffmpeg, "-hide_banner", "-nostdin", "-f", "lavfi", "-i", "flite=list_voices=1"],
                capture_output=True, text=True, timeout=10, check=False,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            voices = sorted(set(re.findall(r"\[Parsed_flite_\d+ @ [^\]]+\] (\w+)\s*$", result.stderr, re.MULTILINE)) & set(SUPPORTED_VOICES))
        except (OSError, subprocess.SubprocessError):
            pass
    engines.append({"id": "flite", "available": bool(voices), "languages": ["en"] if voices else [],
                    "voices": voices, "text_limit": 4000, "ascii_only": True,
                    "synthetic": True, "quality_verified": False})
    from .offline_formant_speech import VOICES, _runtime
    languages = []
    try:
        binary, args, environment = _runtime()
        result = subprocess.run([binary, *args, "--voices"], env=environment, capture_output=True,
                                text=True, timeout=10, check=True,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        observed = {line.split()[1] for line in result.stdout.splitlines()[1:] if len(line.split()) > 2}
        languages = [language for language, voice in VOICES.items() if voice in observed]
    except (ValueError, OSError, subprocess.SubprocessError):
        pass
    engines.append({"id": "espeak_ng", "available": bool(languages), "languages": languages,
                    "voices": [VOICES[language] for language in languages], "text_limit": 4000,
                    "ascii_only": False, "synthetic": True, "quality_verified": False})
    return {"engines": engines, "automatic_install": False, "external_network_used": False}


def speech_source_wav(audio: bytes, report: dict) -> bytes:
    pcm, count = _speech_source_pcm(audio)
    value = {
        "schema": "oevira.speech-source/v1", "synthetic": True,
        "text": report["source"]["text"], "engine": report["engine"],
        "voice": report["voice"], "language": report["language"],
        "text_sha256": report["source"]["sha256"],
        "pcm_sha256": hashlib.sha256(pcm).hexdigest(), "samples": count,
        "identity_state": "file_embedded_declaration", "canonical_fact": False,
    }
    comment = b"OEVIRA-SPEECH-V1\n" + json.dumps(value, ensure_ascii=True, sort_keys=True).encode("ascii")
    if len(comment) > 48 * 1024:
        raise VideoEditingError("TTS_SOURCE_METADATA_INVALID")
    comment += b"\0"
    info = b"INFOICMT" + struct.pack("<I", len(comment)) + comment
    if len(comment) % 2:
        info += b"\0"
    result = audio + b"LIST" + struct.pack("<I", len(info)) + info
    result = result[:4] + struct.pack("<I", len(result) - 8) + result[8:]
    if read_speech_source(result) != value:
        raise VideoEditingError("TTS_SOURCE_METADATA_INVALID")
    return result


def _speech_source_pcm(audio: bytes) -> tuple[bytes, int]:
    try:
        if (len(audio) > 31 * 1024 * 1024 or len(audio) < 44 or audio[:4] != b"RIFF"
                or audio[8:12] != b"WAVE" or struct.unpack_from("<I", audio, 4)[0] + 8 != len(audio)):
            raise ValueError()
        with wave.open(io.BytesIO(audio), "rb") as sound:
            count = sound.getnframes()
            if (sound.getnchannels() != 1 or sound.getsampwidth() != 2
                    or sound.getcomptype() != "NONE" or not 0 < count / sound.getframerate() <= 300):
                raise ValueError()
            pcm = sound.readframes(count + 1)
        if len(pcm) != count * 2:
            raise ValueError()
        return pcm, count
    except (EOFError, OSError, ValueError, ZeroDivisionError, struct.error, wave.Error) as exc:
        raise VideoEditingError("TTS_SOURCE_METADATA_INVALID") from exc


def read_speech_source(audio: bytes) -> dict | None:
    if len(audio) > 31 * 1024 * 1024 or audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
        return None
    position = 12
    found = None
    while position + 8 <= len(audio):
        kind, size = struct.unpack_from("<4sI", audio, position)
        end = position + 8 + size
        if end > len(audio):
            raise VideoEditingError("TTS_SOURCE_METADATA_INVALID")
        if kind == b"LIST" and audio[position + 8:position + 12] == b"INFO":
            item = position + 12
            while item + 8 <= end:
                tag, length = struct.unpack_from("<4sI", audio, item)
                stop = item + 8 + length
                if stop > end:
                    raise VideoEditingError("TTS_SOURCE_METADATA_INVALID")
                prefix = b"OEVIRA-SPEECH-V1\n"
                if tag == b"ICMT" and audio[item + 8:item + 8 + len(prefix)] == prefix:
                    if found is not None or length > 48 * 1024:
                        raise VideoEditingError("TTS_SOURCE_METADATA_INVALID")
                    try:
                        found = json.loads(audio[item + 8 + len(prefix):stop].rstrip(b"\0").decode("ascii"))
                    except (ValueError, UnicodeError) as exc:
                        raise VideoEditingError("TTS_SOURCE_METADATA_INVALID") from exc
                item = stop + length % 2
        position = end + size % 2
    if found is None:
        return None
    pcm, count = _speech_source_pcm(audio)
    try:
        if (not isinstance(found, dict) or set(found) != {
                "schema", "synthetic", "text", "engine", "voice", "language", "text_sha256",
                "pcm_sha256", "samples", "identity_state", "canonical_fact"}
                or found["schema"] != "oevira.speech-source/v1" or found["synthetic"] is not True
                or found["canonical_fact"] is not False
                or found["identity_state"] != "file_embedded_declaration"
                or not isinstance(found["text"], str) or not 1 <= len(found["text"]) <= 4000
                or not found["text"].strip()
                or hashlib.sha256(found["text"].encode("utf-8")).hexdigest() != found["text_sha256"]
                or hashlib.sha256(pcm).hexdigest() != found["pcm_sha256"]
                or type(found["samples"]) is not int or found["samples"] != count):
            raise ValueError()
        if found["engine"] == "ffmpeg_libflite":
            _validate_text(found["text"], found["voice"], found["language"])
        elif found["engine"] == "espeak_ng":
            from .offline_formant_speech import VOICES
            if VOICES.get(found["language"]) != found["voice"]:
                raise ValueError()
        else:
            raise ValueError()
    except (ValueError, TypeError, KeyError) as exc:
        raise VideoEditingError("TTS_SOURCE_METADATA_INVALID") from exc
    return found


# These are FFmpeg's built-in, US-English Flite voices, not user-controlled
# filenames, remote model locations or claims of multilingual availability.
SUPPORTED_VOICES = ("awb", "kal", "kal16", "rms", "slt")
SUPPORTED_LANGUAGES = ("en", "en-US")
MAX_TEXT_CHARACTERS = 4000
MAX_AUDIO_SECONDS = 300
SAMPLE_RATE = 16000
MAX_PCM_BYTES = MAX_AUDIO_SECONDS * SAMPLE_RATE * 2
MAX_WAV_BYTES = MAX_PCM_BYTES + 4096
SYNTHESIS_TIMEOUT_SECONDS = 120
DECODE_TIMEOUT_SECONDS = 30


def _check(callback: Callable[[], None] | None) -> None:
    if callback is not None:
        callback()


def _validate_text(text: Any, voice: Any, language: Any) -> bytes:
    if not isinstance(language, str) or language not in SUPPORTED_LANGUAGES:
        raise VideoEditingError("TTS_LANGUAGE_UNAVAILABLE")
    if not isinstance(voice, str) or voice not in SUPPORTED_VOICES:
        raise VideoEditingError("TTS_VOICE_UNAVAILABLE")
    if (not isinstance(text, str) or not text.strip()
            or len(text) > MAX_TEXT_CHARACTERS
            or any(unicodedata.category(char).startswith("C") and char not in "\t\r\n"
                   for char in text)):
        raise VideoEditingError("TTS_TEXT_INVALID")
    # The built-in English lexicon cannot promise pronunciation of Chinese,
    # other scripts or accented letters. Reject, never drop/transliterate them.
    if not text.isascii():
        raise VideoEditingError("TTS_LANGUAGE_UNAVAILABLE")
    if not any(char.isalnum() for char in text):
        raise VideoEditingError("TTS_TEXT_INVALID")
    return text.encode("utf-8")


def _read_pcm(data: bytes) -> tuple[bytes, int]:
    try:
        if (len(data) > MAX_WAV_BYTES or len(data) < 44 or data[:4] != b"RIFF"
                or struct.unpack_from("<I", data, 4)[0] + 8 != len(data)):
            raise ValueError("incomplete WAV container")
        with wave.open(io.BytesIO(data), "rb") as sound:
            count = sound.getnframes()
            if (sound.getnchannels() != 1 or sound.getsampwidth() != 2
                    or sound.getframerate() != SAMPLE_RATE or sound.getcomptype() != "NONE"
                    or count <= 0 or count > MAX_AUDIO_SECONDS * SAMPLE_RATE):
                raise ValueError("unsupported or empty PCM")
            raw = sound.readframes(count + 1)
        if len(raw) != count * 2:
            raise ValueError("truncated PCM")
    except (EOFError, OSError, ValueError, struct.error, wave.Error) as exc:
        raise VideoEditingError("TTS_AUDIO_INVALID") from exc
    return raw, count


def synthesize_offline_speech(
    text: str, *, voice: str = "slt", language: str = "en",
    check_cancel: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Return a complete PCM WAV plus an honest, source-bound JSON receipt.

    Accepts 1..4000 characters of nonblank ASCII English text. Both the full
    submitted text and its hash are retained in the receipt. No duration/byte
    truncation, phoneme alignment, translation, cloning or automatic publishing
    is performed. A resource limit rejects the *whole* result. ``check_cancel``
    must raise to cancel; its exact exception propagates after process cleanup.
    """
    _check(check_cancel)
    text_bytes = _validate_text(text, voice, language)
    from shared_artifacts import _ffmpeg_path
    ffmpeg = _ffmpeg_path()
    if not ffmpeg:
        raise VideoEditingError("TTS_RUNTIME_UNAVAILABLE")

    with tempfile.TemporaryDirectory(prefix="lumenis-offline-speech-") as directory:
        work = Path(directory)
        textfile = work / "speech.txt"
        wavfile = work / "speech.wav"
        decoded = work / "decoded.pcm"
        # A private directory plus an exclusive file prevents path substitution.
        # The fixed relative filename is the only textfile expression in lavfi.
        with textfile.open("xb") as stream:
            stream.write(text_bytes)
        textfile.chmod(0o600)

        callback_error: BaseException | None = None

        def check_resources() -> None:
            nonlocal callback_error
            try:
                _check(check_cancel)
                for path, limit in ((wavfile, MAX_WAV_BYTES), (decoded, MAX_PCM_BYTES)):
                    if path.exists() and path.stat().st_size > limit:
                        raise VideoEditingError("TTS_AUDIO_LIMIT_EXCEEDED")
            except BaseException as exc:
                callback_error = exc
                raise

        def run(command: list[str], *, timeout: float, error: str) -> str:
            try:
                return rendering._run(command, cwd=work, timeout=timeout,
                                      check_continue=check_resources)
            except VideoEditingError as exc:
                if exc is callback_error:
                    raise
                raise VideoEditingError(error) from exc

        # No -t/-frames/-fs/atrim: FFmpeg must consume the entire utterance.
        # No user text, paths, URLs or unknown voices are interpolated into lavfi.
        # Input/output protocols are file-only; Flite's selected voice is builtin.
        stderr = run([
            ffmpeg, "-v", "info", "-xerror", "-nostdin", "-n", "-threads", "1",
            "-filter_threads", "1", "-protocol_whitelist", "file", "-f", "lavfi",
            "-i", f"flite=textfile=speech.txt:voice={voice}", "-map", "0:a:0",
            "-vn", "-sn", "-dn", "-map_metadata", "-1", "-ac", "1",
            "-ar", str(SAMPLE_RATE), "-c:a", "pcm_s16le", "-threads:a", "1",
            "-fflags", "+bitexact", "-flags:a", "+bitexact",
            "-protocol_whitelist", "file", "-f", "wav", "speech.wav",
        ], timeout=SYNTHESIS_TIMEOUT_SECONDS, error="TTS_SYNTHESIS_FAILED")
        check_resources()
        try:
            audio = wavfile.read_bytes()
        except OSError as exc:
            raise VideoEditingError("TTS_AUDIO_INVALID") from exc
        raw, count = _read_pcm(audio)

        # Independently decode every frame with strict FFmpeg error handling and
        # compare the complete PCM, rather than trusting duration/header alone.
        run([
            ffmpeg, "-v", "error", "-xerror", "-nostdin", "-n", "-threads", "1",
            "-err_detect", "explode", "-protocol_whitelist", "file",
            "-format_whitelist", "wav", "-i", "speech.wav", "-map", "0:a:0",
            "-vn", "-sn", "-dn", "-map_metadata", "-1", "-c:a", "pcm_s16le",
            "-threads:a", "1", "-protocol_whitelist", "file", "-f", "s16le", "decoded.pcm",
        ], timeout=DECODE_TIMEOUT_SECONDS, error="TTS_DECODE_FAILED")
        check_resources()
        try:
            if decoded.read_bytes() != raw:
                raise VideoEditingError("TTS_DECODE_MISMATCH")
        except OSError as exc:
            raise VideoEditingError("TTS_DECODE_FAILED") from exc
        samples = array("h")
        samples.frombytes(raw)
        if sys.byteorder != "little":
            samples.byteswap()
        peak = max(abs(value) for value in samples)
        if peak == 0:
            raise VideoEditingError("TTS_AUDIO_SILENT")
        _check(check_cancel)
        version = next((line for line in stderr.splitlines()
                        if line.startswith("ffmpeg version ")), "NOT_REPORTED")
        report = {
            "schema": "lumenis.offline-speech/v1",
            "engine": "ffmpeg_libflite", "engine_ownership": "third_party",
            "runtime": {"ffmpeg_version_line": version,
                        "voice_model_version": "installed_builtin_not_independently_versioned"},
            "voice": voice, "language": language, "voice_language": "en-US",
            "label": {"en": "AI voiceover", "zh": "AI 配音"},
            "synthetic": True, "voice_cloned": False,
            "external_network_used": False, "automatic_model_download": False,
            "source": {"kind": "caller_supplied_text", "text": text,
                       "sha256": hashlib.sha256(text_bytes).hexdigest(),
                       "encoding": "UTF-8", "size_bytes": len(text_bytes),
                       "characters": len(text), "canonical_fact": False,
                       "rights": "caller_must_verify"},
            "text_submission": "complete_literal_textfile", "text_truncated": False,
            "audio_trimmed": False, "normalization": "none",
            "word_boundaries": "unavailable", "naturalness": "NOT_EVALUATED",
            "pronunciation_accuracy": "NOT_EVALUATED", "published": False,
            "audio": {"codec": "pcm_s16le", "sample_rate": SAMPLE_RATE,
                      "channels": 1, "sample_width_bytes": 2,
                      "decoded_samples_per_channel": count, "duration_sec": count / SAMPLE_RATE,
                      "sample_peak": peak / 32768,
                      "clipped_samples": sum(value in (-32768, 32767) for value in samples),
                      "true_peak": "NOT_MEASURED", "loudness_lufs": "NOT_MEASURED",
                      "pcm_sha256": hashlib.sha256(raw).hexdigest(),
                      "full_decode": "passed", "full_pcm_comparison": "passed"},
            "limits": {"max_text_characters": MAX_TEXT_CHARACTERS,
                       "max_audio_seconds": MAX_AUDIO_SECONDS,
                       "supported_text": "ASCII English only; no language detection",
                       "limit_behavior": "reject_entire_result_without_truncation"},
            "references": {"ffmpeg_filter": "https://ffmpeg.org/ffmpeg-filters.html#flite",
                           "flite_license": "https://github.com/festvox/flite/blob/v2.2/COPYING",
                           "voice_sources": "https://github.com/festvox/flite/tree/v2.2/lang",
                           "redistributed_engine_or_voices": False},
            "outputs": {"speech.wav": {"mime_type": "audio/wav", "size_bytes": len(audio),
                                       "sha256": hashlib.sha256(audio).hexdigest()}},
        }
        receipt = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        _check(check_cancel)
        return {"files": {"speech.wav": audio, "speech.json": receipt}, "report": report}
