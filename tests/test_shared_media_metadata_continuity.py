"""Compatibility checks for source-media stream metadata across Artifact versions."""
import copy

import pytest

from shared_artifacts import (
    _source_asset_metadata_is_valid,
    _source_asset_metadata_matches_probe,
)

_MEDIA_SHA256 = "a" * 64
_VIDEO_AUDIO_STREAMS = [
    {
        "kind": "video",
        "type_relative_ordinal": 0,
        "global_index": 0,
        "time_base": "1/1000",
        "start_pts": 0,
        "duration_ts": 2000,
    },
    {
        "kind": "audio",
        "type_relative_ordinal": 0,
        "global_index": 1,
        "time_base": "1/48000",
        "start_pts": 0,
        "duration_ts": 96000,
        "sample_rate": 48000,
        "channels": 2,
    },
]


def _legacy_video_asset(**changes):
    asset = {
        "asset_id": f"MEDIA-{_MEDIA_SHA256[:16]}",
        "filename": "clip.mp4",
        "sha256": _MEDIA_SHA256,
        "duration_sec": 2.0,
        "media_kind": "video_audio",
        "has_video": True,
        "audio_stream_count": 1,
        "evidence_refs": [],
        "rights_status": "unknown",
    }
    asset.update(changes)
    return asset


def _current_video_asset(*, streams=None, **changes):
    asset = _legacy_video_asset(
        stream_metadata=copy.deepcopy(
            _VIDEO_AUDIO_STREAMS if streams is None else streams
        ),
        **changes,
    )
    return asset


def test_exact_legacy_and_valid_current_video_descriptors_are_accepted():
    legacy = _legacy_video_asset()
    current = _current_video_asset()

    assert _source_asset_metadata_is_valid(legacy, "clip.mp4")
    assert _source_asset_metadata_is_valid(current, "clip.mp4")
    assert current["stream_metadata"] == _VIDEO_AUDIO_STREAMS


def test_legacy_descriptor_matches_current_probe_without_dropping_probe_streams():
    stored = _legacy_video_asset()
    probed = _current_video_asset()
    probed_streams = copy.deepcopy(probed["stream_metadata"])

    assert _source_asset_metadata_matches_probe(stored, probed)
    assert probed["stream_metadata"] == probed_streams

    changed_legacy_field = _current_video_asset(duration_sec=2.25)
    assert not _source_asset_metadata_matches_probe(stored, changed_legacy_field)


@pytest.mark.parametrize(
    "corruption",
    [
        "stream_kind", "field_type", "stream_count", "ordinal", "hash",
        "extra_field", "stream_container",
    ],
)
def test_current_stream_descriptor_rejects_malformed_or_inconsistent_metadata(corruption):
    asset = _current_video_asset()
    if corruption == "stream_kind":
        asset["stream_metadata"][0]["kind"] = "subtitle"
    elif corruption == "field_type":
        asset["stream_metadata"][0]["type_relative_ordinal"] = True
    elif corruption == "stream_count":
        asset["audio_stream_count"] = 2
    elif corruption == "ordinal":
        asset["stream_metadata"][1]["type_relative_ordinal"] = 1
    elif corruption == "hash":
        asset["sha256"] = "A" * 64
    elif corruption == "extra_field":
        asset["unreviewed"] = "not allowed"
    else:
        asset["stream_metadata"] = tuple(asset["stream_metadata"])

    assert not _source_asset_metadata_is_valid(asset, "clip.mp4")


def test_current_descriptor_requires_exact_probed_streams():
    stored = _current_video_asset()
    probed = _current_video_asset()
    assert _source_asset_metadata_matches_probe(stored, probed)

    changed_stream = copy.deepcopy(probed)
    changed_stream["stream_metadata"][1]["time_base"] = "1/44100"
    assert _source_asset_metadata_is_valid(changed_stream, "clip.mp4")
    assert not _source_asset_metadata_matches_probe(stored, changed_stream)


def test_image_source_descriptors_keep_the_existing_exact_shape():
    image_sha256 = "c" * 64
    image = {
        "asset_id": f"MEDIA-{image_sha256[:16]}",
        "filename": "cover.png",
        "sha256": image_sha256,
        "duration_sec": None,
        "media_kind": "image",
        "has_video": False,
        "audio_stream_count": 0,
        "width": 640,
        "height": 480,
        "evidence_refs": [],
        "rights_status": "unknown",
    }

    assert _source_asset_metadata_is_valid(image, "cover.png")
    assert _source_asset_metadata_matches_probe(image, dict(image))
    assert not _source_asset_metadata_is_valid(
        {**image, "stream_metadata": []}, "cover.png",
    )
