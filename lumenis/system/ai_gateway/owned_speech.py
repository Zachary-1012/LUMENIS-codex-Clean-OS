"""Explicit offline Whisper evaluation through the existing SYSTEM AI Gateway.

The caller owns Source/Artifact authorization and persistence. This adapter
returns an unreviewed derivative; it creates no job, Evidence, permission or
database. Cancellation discards the computation; recovery starts from the same
verified audio. It never downloads a runtime/model or selects another provider.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import wave

MODEL_ID = "openai/whisper-base"
MODEL_REVISION = "31243bad24cc746f07d4c8bfdd2d974872cb1803"
WEIGHT_SHA256 = "ed3a0b6b1c0edf879ad9b11b1af5a0e6ab5db9205f891f668f8b0e6c6326e34e"
_SHA = re.compile(r"^[0-9a-f]{64}$")
_MAX_AUDIO_BYTES = 256 * 1024 * 1024
_MAX_DURATION_SECONDS = 600
_SAMPLE_RATE = 16000
_WHISPER_FILES = {
    "__init__.py": "79ecbed714783b6230931a3dba6d5da6d386e2d44f9fc27256e4fc72751e1f62",
    "__main__.py": "c519d586c3a6b639f64e59d2d6fd6b591a67ecd739f9727492911fc4ce4d545a",
    "assets/gpt2.tiktoken": "306cd27f03c1a714eca7108e03d66b7dc042abe8c258b44c199a7ed9838dd930",
    "assets/mel_filters.npz": "7450ae70723a5ef9d341e3cee628c7cb0177f36ce42c44b7ed2bf3325f0f6d4c",
    "assets/multilingual.tiktoken": "b34b360dbb493e781e479794586d661700670d65564001f23024971d1f2fa126",
    "audio.py": "36ed287b2de3eaf40207cd2a44a8d45d57ea5c212a39df07401d4fcb4d5a5a1a",
    "decoding.py": "94084fedc5af74cabf8e1883a85552700057081f00ea669ad49435ecb29039db",
    "model.py": "473491a97554ad1d0beaaef6fe91d965f12785b466b93ebb61024307b50ad683",
    "normalizers/__init__.py": "f18fcdce4caee7f2e80e4c01ab0457d3a080a872a29489542c6d23c4b0bba572",
    "normalizers/basic.py": "4742eaa040e0657fa1247a1361e0d856c62317a43326ea59a40c2e9edd8d2c38",
    "normalizers/english.py": "2898e4672aeefc9f44cb4de38c115cdf286f5b35ae321433467a7674ce8841d0",
    "timing.py": "bb091c973c428697012f0f8d1b4f5f3a605cd93c5d1c129957f712a6a878a59c",
    "tokenizer.py": "3b48e361a7e95b4ec0356ca6d72bba635778aa10269153136ee7bc34cae30b85",
    "transcribe.py": "848b82877500d6fb8f0b91bee7a08ac67ef670a113591d11b494848d263ad0f6",
    "triton_ops.py": "26c5082f029bbd2b7ae77ecf5a3f7f196f220e5850e2c9d0ec42961caf0dde4c",
    "utils.py": "c25990446ab7dd5ba30bd52bd4f0e6537f11b5e361a015f02c21355d41027b05",
    "version.py": "c4d27ecccdd52a9cded762f1a82da3152db12cbc0aa6ea781f945446a143cfaf",
}


class SpeechBlocked(RuntimeError):
    """A named input, asset, runtime or decoder contract is unavailable/invalid."""


class SpeechCancelled(SpeechBlocked):
    """No transcript was committed; retry requires a fresh authorized invocation."""


@dataclass(frozen=True)
class SpeechRuntime:
    python_path: str
    python_sha256: str
    manifest_path: str
    manifest_sha256: str
    weight_path: str
    ffmpeg_path: str
    ffmpeg_sha256: str


def _digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _local_file(value: str, expected: str) -> Path:
    if not isinstance(value, str) or not value or not isinstance(expected, str) or not _SHA.fullmatch(expected):
        raise SpeechBlocked("EXACT_LOCAL_PATH_AND_SHA256_REQUIRED")
    path = Path(value)
    if not path.is_absolute() or path.is_symlink() or not path.is_file():
        raise SpeechBlocked("LOCAL_SPEECH_ASSET_MISSING")
    if _digest(path) != expected:
        raise SpeechBlocked("LOCAL_SPEECH_ASSET_HASH_MISMATCH")
    return path.resolve()


def _strict_json(raw: bytes):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise SpeechBlocked("SPEECH_JSON_DUPLICATE_KEY")
            result[key] = value
        return result

    def nonfinite(_value):
        raise SpeechBlocked("SPEECH_JSON_NONFINITE")

    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
    except (ValueError, UnicodeDecodeError) as exc:
        raise SpeechBlocked("SPEECH_JSON_INVALID") from exc


def _finite_number(value) -> bool:
    # Whisper alignment returns numpy.float64 as well as ordinary Python floats.
    # Preserve those values; bool must not masquerade as a numeric timestamp.
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _wav_bytes(path: Path, expected_sha256: str) -> tuple[bytes, float]:
    if not 0 < path.stat().st_size <= _MAX_AUDIO_BYTES:
        raise SpeechBlocked("SPEECH_AUDIO_SIZE_UNSUPPORTED")
    with path.open("rb") as handle:
        data = handle.read(_MAX_AUDIO_BYTES + 1)
    if len(data) > _MAX_AUDIO_BYTES or hashlib.sha256(data).hexdigest() != expected_sha256:
        raise SpeechBlocked("SPEECH_AUDIO_CHANGED")
    try:
        with wave.open(io.BytesIO(data), "rb") as audio:
            frames, rate = audio.getnframes(), audio.getframerate()
            duration = frames / rate if rate else 0
            if (audio.getcomptype() != "NONE" or audio.getnchannels() not in {1, 2}
                    or audio.getsampwidth() not in {2, 3, 4} or not 8000 <= rate <= 192000
                    or not 0 < duration <= _MAX_DURATION_SECONDS):
                raise SpeechBlocked("SPEECH_PCM_WAV_UNSUPPORTED")
            if len(audio.readframes(frames)) != frames * audio.getnchannels() * audio.getsampwidth():
                raise SpeechBlocked("SPEECH_WAV_TRUNCATED")
    except (wave.Error, EOFError) as exc:
        raise SpeechBlocked("SPEECH_PCM_WAV_INVALID") from exc
    return data, duration


def _communicate(command, payload: bytes, *, cancelled, deadline: float) -> bytes:
    if cancelled():
        raise SpeechCancelled("SPEECH_CANCELLED_NO_RESULT")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, creationflags=flags)
    try:
        pending = payload
        while True:
            if cancelled():
                raise SpeechCancelled("SPEECH_CANCELLED_NO_RESULT")
            if time.monotonic() >= deadline:
                raise SpeechBlocked("SPEECH_COMPUTATION_TIMEOUT")
            try:
                stdout, _stderr = process.communicate(input=pending, timeout=0.2)
                if process.returncode != 0:
                    raise SpeechBlocked("SPEECH_OFFLINE_WORKER_FAILED")
                return stdout
            except subprocess.TimeoutExpired:
                pending = None
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate()


def validate_transcript(raw: dict, *, duration_seconds: float) -> dict:
    """Validate intervals and retain decoder uncertainty without correcting text."""
    if not isinstance(raw, dict) or set(raw) != {"text", "language", "segments"}:
        raise SpeechBlocked("SPEECH_TRANSCRIPT_SHAPE_INVALID")
    if (not isinstance(raw["text"], str) or not isinstance(raw["language"], str)
            or not re.fullmatch(r"[a-z]{2,3}", raw["language"])
            or not isinstance(raw["segments"], list)
            or len(raw["segments"]) > 4096 or not _finite_number(duration_seconds) or duration_seconds <= 0):
        raise SpeechBlocked("SPEECH_TRANSCRIPT_INVALID")
    previous, warnings = 0.0, []
    for index, segment in enumerate(raw["segments"]):
        if not isinstance(segment, dict) or type(segment.get("id")) is not int or segment["id"] != index or not isinstance(segment.get("text"), str):
            raise SpeechBlocked("SPEECH_SEGMENT_INVALID")
        start, end = segment.get("start"), segment.get("end")
        if not all(_finite_number(value) for value in (start, end)) or not previous <= start <= end <= duration_seconds + 0.05:
            raise SpeechBlocked("SPEECH_SEGMENT_INTERVAL_INVALID")
        previous = end
        for key in ("avg_logprob", "compression_ratio", "no_speech_prob"):
            value = segment.get(key)
            if not _finite_number(value):
                raise SpeechBlocked("SPEECH_DECODER_METRIC_INVALID")
        if not 0 <= segment["no_speech_prob"] <= 1 or segment["compression_ratio"] < 0:
            raise SpeechBlocked("SPEECH_DECODER_METRIC_INVALID")
        words = segment.get("words")
        if not isinstance(words, list):
            raise SpeechBlocked("SPEECH_WORD_TIMESTAMPS_REQUIRED")
        word_end = start
        for word in words:
            if not isinstance(word, dict) or not isinstance(word.get("word"), str):
                raise SpeechBlocked("SPEECH_WORD_INVALID")
            begin, finish, probability = (word.get(key) for key in ("start", "end", "probability"))
            if not all(_finite_number(value) for value in (begin, finish, probability)) or not word_end <= begin <= finish <= end + 0.05 or not 0 <= probability <= 1:
                raise SpeechBlocked("SPEECH_WORD_INTERVAL_OR_PROBABILITY_INVALID")
            word_end = finish
            if probability < 0.8:
                warnings.append({"segment_id": index, "start": begin, "end": finish,
                                 "word": word["word"], "reason": "LOW_DECODER_WORD_PROBABILITY"})
        if segment["avg_logprob"] < -1 or segment["no_speech_prob"] >= 0.6 or segment["compression_ratio"] > 2.4:
            warnings.append({"segment_id": index, "reason": "DECODER_SEGMENT_REVIEW_REQUIRED"})
    if "".join(segment["text"] for segment in raw["segments"]) != raw["text"]:
        raise SpeechBlocked("SPEECH_TEXT_SEGMENT_MISMATCH")
    return {"transcript": raw, "warnings": warnings,
            "review_state": "UNREVIEWED" if raw["text"].strip() else "NO_RECOGNIZED_SPEECH",
            "speaker_identity": "UNKNOWN", "timestamp_method": "MODEL_ESTIMATED_FROM_AUDIO",
            "decoder_probabilities_are_accuracy": False, "semantic_correctness": "REVIEW_REQUIRED"}


def _transcript_wire_bytes(raw: dict, *, duration_seconds: float) -> bytes:
    # Check exactly the JSON-native values the parent receives. No default=str,
    # arbitrary numeric coercion, transcript correction or timestamp adjustment.
    try:
        wire = json.dumps(raw, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, TypeError) as exc:
        raise SpeechBlocked("SPEECH_DECODER_OUTPUT_NOT_SERIALIZABLE") from exc
    validate_transcript(_strict_json(wire), duration_seconds=duration_seconds)
    return wire


def transcribe_audio(audio_path: str, *, expected_audio_sha256: str, runtime: SpeechRuntime,
                     source_ref: str | None = None, is_cancelled=None, timeout_seconds: float = 600) -> dict:
    """Transcribe one authorized local PCM WAV; return a derivative for its owner.

    ``source_ref`` is an opaque caller locator, never proof of authorization.
    A TaskEngine cancellation predicate can abort either owned subprocess.
    No partial transcript is persisted or reused on a subsequent invocation.
    """
    if not isinstance(runtime, SpeechRuntime) or (source_ref is not None and (not isinstance(source_ref, str) or not source_ref.strip() or len(source_ref) > 512)):
        raise SpeechBlocked("SPEECH_CALLER_CONTRACT_INVALID")
    if type(timeout_seconds) not in {int, float} or not math.isfinite(timeout_seconds) or not 1 <= timeout_seconds <= 1800:
        raise SpeechBlocked("SPEECH_TIMEOUT_INVALID")
    cancelled = is_cancelled if is_cancelled is not None else lambda: False
    if not callable(cancelled):
        raise SpeechBlocked("SPEECH_CANCELLATION_PREDICATE_REQUIRED")
    if cancelled():
        raise SpeechCancelled("SPEECH_CANCELLED_NO_RESULT")
    started = time.monotonic()
    paths = {
        "audio": _local_file(audio_path, expected_audio_sha256),
        "python": _local_file(runtime.python_path, runtime.python_sha256),
        "manifest": _local_file(runtime.manifest_path, runtime.manifest_sha256),
        "weight": _local_file(runtime.weight_path, WEIGHT_SHA256),
        "ffmpeg": _local_file(runtime.ffmpeg_path, runtime.ffmpeg_sha256),
    }
    audio, duration = _wav_bytes(paths["audio"], expected_audio_sha256)
    deadline = started + timeout_seconds
    normalized = _communicate([
        str(paths["ffmpeg"]), "-nostdin", "-hide_banner", "-loglevel", "error",
        "-protocol_whitelist", "pipe", "-f", "wav", "-i", "pipe:0", "-map", "0:a:0",
        "-vn", "-ac", "1", "-ar", str(_SAMPLE_RATE), "-f", "f32le", "pipe:1",
    ], audio, cancelled=cancelled, deadline=deadline)
    if not normalized or len(normalized) % 4 or abs(len(normalized) / 4 / _SAMPLE_RATE - duration) > 1 / _SAMPLE_RATE:
        raise SpeechBlocked("SPEECH_NORMALIZED_DURATION_MISMATCH")
    spec = {"manifest_path": str(paths["manifest"]), "manifest_sha256": runtime.manifest_sha256,
            "weight_path": str(paths["weight"]), "duration_seconds": duration}
    module_path = Path(__file__).resolve()
    module_sha = _digest(module_path)
    response = _communicate([str(paths["python"]), "-I", str(module_path), "--worker"],
                            json.dumps(spec, allow_nan=False).encode() + b"\n" + normalized,
                            cancelled=cancelled, deadline=deadline)
    if cancelled():
        raise SpeechCancelled("SPEECH_CANCELLED_NO_RESULT")
    # Revalidate named assets and source before handing bytes back to their owner.
    for path, expected in ((paths["audio"], expected_audio_sha256), (paths["python"], runtime.python_sha256),
                           (paths["manifest"], runtime.manifest_sha256), (paths["weight"], WEIGHT_SHA256),
                           (paths["ffmpeg"], runtime.ffmpeg_sha256), (module_path, module_sha)):
        _local_file(str(path), expected)
    raw = _strict_json(response)
    result = validate_transcript(raw, duration_seconds=duration)
    return {"schema": "owned-speech-derivative:v1", "owner": "SYSTEM AI Gateway", **result,
            "source_ref": source_ref, "source_ref_authenticated_by_adapter": False,
            "source_sha256": expected_audio_sha256, "duration_seconds": duration,
            "model_id": MODEL_ID, "model_revision": MODEL_REVISION, "weight_sha256": WEIGHT_SHA256,
            "runtime_manifest_sha256": runtime.manifest_sha256, "adapter_sha256": module_sha,
            "ffmpeg_sha256": runtime.ffmpeg_sha256, "elapsed_seconds": time.monotonic() - started,
            "offline": True, "fallback_allowed": False, "script_or_target_supplied": False,
            "rights_state": "UNKNOWN", "human_listening_acceptance": False,
            "promotion_status": "NOT_PROMOTED", "product_acceptance": False}


def _worker() -> None:
    """Private isolated subprocess; no database, network or child process access."""
    from importlib import metadata, util

    spec = _strict_json(sys.stdin.buffer.readline(16384))
    if not isinstance(spec, dict) or set(spec) != {"manifest_path", "manifest_sha256", "weight_path", "duration_seconds"}:
        raise SpeechBlocked("SPEECH_WORKER_CONTRACT_INVALID")
    manifest_path = _local_file(spec["manifest_path"], spec["manifest_sha256"])
    manifest = _strict_json(manifest_path.read_bytes())
    if manifest.get("schema") != "owned-speech-runtime:v1" or manifest.get("owner") != "SYSTEM AI Gateway":
        raise SpeechBlocked("SPEECH_RUNTIME_MANIFEST_INVALID")
    prefix = Path(sys.prefix).resolve()
    for relative, digest in manifest["files"].items():
        path = prefix / relative
        if not path.resolve().is_relative_to(prefix):
            raise SpeechBlocked("SPEECH_RUNTIME_PATH_INVALID")
        _local_file(str(path), digest)
    for name, pin in manifest["packages"].items():
        if metadata.version(name) != pin["version"]:
            raise SpeechBlocked("SPEECH_RUNTIME_VERSION_MISMATCH")
    if metadata.version("openai-whisper") != "20250625" or metadata.version("torch") != "2.14.1+cpu":
        raise SpeechBlocked("SPEECH_PINNED_CPU_RUNTIME_REQUIRED")
    module_dir = Path(util.find_spec("whisper").origin).parent
    for relative, digest in _WHISPER_FILES.items():
        _local_file(str(module_dir / relative), digest)
    weight = _local_file(spec["weight_path"], WEIGHT_SHA256)

    def offline(event, _args):
        if event in {"socket.connect", "socket.bind", "socket.getaddrinfo", "socket.sendto", "sqlite3.connect", "subprocess.Popen"}:
            raise SpeechBlocked("SPEECH_WORKER_EXTERNAL_ACCESS_FORBIDDEN")

    sys.addaudithook(offline)
    import numpy as np
    import torch
    import whisper

    if torch.version.cuda is not None:
        raise SpeechBlocked("SPEECH_CPU_ONLY_REQUIRED")
    torch.set_num_threads(4)
    raw = sys.stdin.buffer.read(_MAX_DURATION_SECONDS * _SAMPLE_RATE * 4 + 1)
    if not raw or len(raw) % 4 or abs(len(raw) / 4 / _SAMPLE_RATE - spec["duration_seconds"]) > 1 / _SAMPLE_RATE:
        raise SpeechBlocked("SPEECH_WORKER_AUDIO_INVALID")
    audio = np.frombuffer(raw, dtype="<f4").copy()
    if not np.isfinite(audio).all():
        raise SpeechBlocked("SPEECH_WORKER_AUDIO_NONFINITE")
    model = whisper.load_model(str(weight), device="cpu")
    result = model.transcribe(audio, fp16=False, verbose=None, language=None, task="transcribe",
                              condition_on_previous_text=False, temperature=0.0, beam_size=1,
                              initial_prompt=None, word_timestamps=True)
    _local_file(str(weight), WEIGHT_SHA256)
    sys.stdout.buffer.write(_transcript_wire_bytes(result, duration_seconds=spec["duration_seconds"]))


if __name__ == "__main__":
    if sys.argv[1:] != ["--worker"]:
        raise SystemExit("EXPLICIT_SPEECH_WORKER_ONLY")
    _worker()
