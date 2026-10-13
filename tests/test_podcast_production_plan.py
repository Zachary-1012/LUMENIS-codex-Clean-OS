"""Podcast editing intent; these contract cases are not audible acceptance."""
import json
from dataclasses import replace

import pytest

from podcast.intelligence.episode_runtime import PodcastPlan, PodcastSegment


def segment(identifier="s1", **changes):
    fields = dict(segment_id=identifier, media_asset_id="MEDIA-test", source_in=4.0,
                  source_out=7.0, original_text="raw transcription",
                  corrected_text="Reviewed transcription", speaker="Guest",
                  chapter_title="Source discussion", evidence_refs=("opaque-reference",))
    fields.update(changes)
    return PodcastSegment(**fields)


def plan(*segments):
    return PodcastPlan("Source review episode", "An attributed discussion", "en", tuple(segments or (segment(),)))


@pytest.mark.parametrize("text", ["完整中文条件。", "Keep the complete condition.", "조건을 온전히 보존합니다.", "中文 English 한국어 condition"])
def test_editorial_revision_exports_all_members_without_claiming_new_audio(text):
    original = plan()
    corrected = original.with_transcript_corrections(
        {"s1": text}, expected_revision=original.revision,
        expected_digest=original.content_digest(),
    )
    documents = corrected.editable_documents()
    assert set(documents) == {
        "podcast-plan.json", "script.txt", "transcript-original.vtt",
        "transcript-corrected.vtt", "chapters.json", "corrections.json", "metadata.json",
    }
    assert PodcastPlan.from_json(documents["podcast-plan.json"]) == corrected
    assert text in documents["transcript-corrected.vtt"]
    assert "raw transcription" in documents["transcript-original.vtt"]
    assert original.segments[0].original_text == corrected.segments[0].original_text
    assert original.segments[0].media_asset_id == corrected.segments[0].media_asset_id
    assert original.segments[0].source_in == corrected.segments[0].source_in
    assert original.segments[0].source_out == corrected.segments[0].source_out
    assert corrected.revision == original.revision + 1
    metadata = json.loads(documents["metadata.json"])
    assert metadata["transcript_edits_change_audio"] is False
    assert metadata["human_listening_acceptance"] == "not_asserted_by_plan"
    assert original.segments[0].corrected_text == "Reviewed transcription"


def test_editorial_revision_rejects_stale_or_foreign_base_and_unknown_segment():
    original = plan()
    for revision, digest in [(original.revision + 1, original.content_digest()),
                             (original.revision, "0" * 64)]:
        with pytest.raises(ValueError, match="stale"):
            original.with_transcript_corrections({"s1": "new wording"},
                expected_revision=revision, expected_digest=digest)
    with pytest.raises(ValueError, match="unknown"):
        original.with_transcript_corrections({"missing": "new wording"},
            expected_revision=original.revision, expected_digest=original.content_digest())
    assert original.revision == 1
    assert original.with_transcript_corrections({}, expected_revision=1,
        expected_digest=original.content_digest()) is original


def test_editorial_reorder_rebuilds_chapters_without_rewriting_source_or_losing_segments():
    original = plan(segment("first", source_in=1, source_out=3, chapter_title="First"),
                    segment("second", source_in=10, source_out=14, chapter_title="Second"))
    changed = original.reordered_segments(("second", "first"),
        expected_revision=1, expected_digest=original.content_digest())
    assert changed.segments == tuple(reversed(original.segments))
    assert changed.chapter_document()["chapters"][1]["startTime"] == 4
    assert "00:00:04.000 --> 00:00:06.000" in changed.original_transcript_vtt()
    assert PodcastPlan.from_json(changed.to_json()).content_digest() == changed.content_digest()
    with pytest.raises(ValueError, match="duplicates"):
        original.reordered_segments(("first", "first"), expected_revision=1,
            expected_digest=original.content_digest())
    assert [item.segment_id for item in original.segments] == ["first", "second"]


def test_correction_and_reviewed_revision_reopen_without_rewriting_source():
    first = plan()
    revised_segment = replace(first.segments[0], corrected_text="Reviewed source correction")
    second = replace(first, segments=(revised_segment,), revision=2)
    reopened = PodcastPlan.from_json(second.to_json())
    assert reopened == second
    assert reopened.segments[0].original_text == "raw transcription"
    assert reopened.segments[0].corrected_text == "Reviewed source correction"
    assert first.revision == 1 and first.segments[0].corrected_text == "Reviewed transcription"
    assert reopened.segments[0].evidence_refs == ("opaque-reference",)


def test_edit_order_controls_chapters_and_transcript_times():
    first = segment(chapter_title="Opening")
    second = segment("s2", source_in=20, source_out=24, chapter_title="Research")
    p = plan(second, first)
    assert p.chapter_document() == {"version": "1.2.0", "chapters": [
        {"startTime": 0.0, "endTime": 4.0, "title": "Research"},
        {"startTime": 4.0, "endTime": 7.0, "title": "Opening"},
    ]}
    assert "00:00:04.000 --> 00:00:07.000" in p.transcript_vtt()
    assert p.chapter_document()["chapters"][0]["title"] == "Research"


def test_multiline_vtt_keeps_one_cue_and_escapes_markup():
    p = plan(segment(speaker="Guest\r\nName", corrected_text="first\r\n\r\n <b>second</b> & x --> y"))
    vtt = p.transcript_vtt()
    assert "<br>" not in vtt
    assert "Guest Name: first\n&nbsp;\n &lt;b&gt;second&lt;/b&gt; &amp; x --&gt; y" in vtt
    assert len(vtt.strip().split("\n\n")) == 2
    assert p.segments[0].speaker == "Guest\r\nName"


def test_submillisecond_cue_fails_without_invalid_equal_timestamps():
    p = plan(segment(source_in=0, source_out=0.0001))
    with pytest.raises(ValueError, match="millisecond precision"):
        p.transcript_vtt()


def test_null_character_is_not_exported_as_valid_vtt():
    with pytest.raises(ValueError, match="null character"):
        plan(segment(corrected_text="invalid\x00text")).transcript_vtt()


@pytest.mark.parametrize("document", [
    '{"version":1,"version":1}',
    '{"x":NaN}',
    '{"x":Infinity}',
    '[' * 1500 + '0' + ']' * 1500,
])
def test_invalid_or_deep_json_fails_with_declared_validation_error(document):
    with pytest.raises(ValueError):
        PodcastPlan.from_json(document)


def test_oversized_input_rejected_before_json_parser(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("oversized input reached JSON parser")
    monkeypatch.setattr("podcast.intelligence.episode_runtime.json.loads", forbidden)
    with pytest.raises(ValueError, match="input limit"):
        PodcastPlan.from_json(" " * 1_600_001)


def test_duplicate_segments_unknown_fields_and_missing_media_are_errors():
    with pytest.raises(ValueError, match="unique"):
        plan(segment(), segment())
    payload = plan().to_dict()
    payload["approved"] = True
    with pytest.raises(ValueError, match="fields"):
        PodcastPlan.from_dict(payload)
    with pytest.raises(ValueError, match="assets"):
        plan().build_timeline(())


def test_shared_timeline_precision_controls_edit_boundaries():
    p = plan(segment(source_in=0, source_out=0.3333334),
             segment("s2", source_in=0, source_out=0.6666666))
    boundaries = p._output_segments()
    assert boundaries[0][2] == 0.333333
    assert boundaries[1][1:] == (0.333333, 1.0)
    assert PodcastPlan.from_json(json.dumps(p.to_dict())) == p


@pytest.fixture
def audio_asset(tmp_path, monkeypatch):
    from lumenis.shared.content_creation import video_editing
    monkeypatch.setenv("LUMENIS_LOCAL_ASSET_DIR", str(tmp_path))
    monkeypatch.setattr(video_editing, "_probe_media_info", lambda _: video_editing._MediaProbe(60, False, 2))
    source = tmp_path / "contract-only.wav"
    source.write_bytes(b"not playable; fingerprint factory contract only")
    return video_editing.fingerprint_local_media(str(source))


def test_explicit_stream_selection_reopens_v2_and_old_v1_stays_readable(audio_asset):
    p = plan(segment(media_asset_id=audio_asset.asset_id, audio_stream_index=1))
    document = p.to_dict()
    assert document["version"] == 2 and document["segments"][0]["audio_stream_index"] == 1
    reopened = PodcastPlan.from_json(p.to_json())
    assert reopened == p
    timeline = reopened.build_timeline((audio_asset,))
    assert timeline.tracks[1].clips[0].audio_stream_index == 1
    legacy = plan(segment()).to_dict()
    assert legacy["version"] == 1 and "audio_stream_index" not in legacy["segments"][0]
    assert PodcastPlan.from_dict(legacy) == plan(segment())
    document["version"] = 1
    with pytest.raises(ValueError, match="requires Podcast plan version 2"):
        PodcastPlan.from_dict(document)


@pytest.mark.parametrize("index", [True, -1, 1.0, "1"])
def test_invalid_stream_selection_is_not_coerced(index):
    with pytest.raises(ValueError, match="non-negative exact integer"):
        segment(audio_stream_index=index)


def test_multistream_missing_or_out_of_range_selection_is_an_error(audio_asset):
    with pytest.raises(ValueError, match="explicit selection is required"):
        plan(segment(media_asset_id=audio_asset.asset_id)).build_timeline((audio_asset,))
    with pytest.raises(ValueError, match="out of range"):
        plan(segment(media_asset_id=audio_asset.asset_id, audio_stream_index=2)).build_timeline((audio_asset,))


def test_speaker_turn_tracks_preserve_original_order_and_absolute_timing(audio_asset):
    p = plan(*(segment(f"s{index}", media_asset_id=audio_asset.asset_id, speaker=speaker,
                       audio_stream_index=0) for index, speaker in enumerate(("Guest", "Host", "Guest"), 1)))
    assert p.voice_track_labels() == {"podcast_voice_1": "Guest", "podcast_voice_2": "Host"}
    timeline = p.build_timeline((audio_asset,), separate_speakers=True)
    assert [(track.track_id, [clip.timeline_start for clip in track.clips]) for track in timeline.tracks[1:]] == [
        ("podcast_voice_1", [0.0, 6.0]), ("podcast_voice_2", [3.0])]
    assert [clip.purpose for clip in timeline.tracks[1].clips] == ["podcast-segment:s1", "podcast-segment:s3"]
    combined = p.build_timeline((audio_asset,))
    assert combined.tracks[1].track_id == "podcast_voice" and len(combined.tracks[1].clips) == 3
    with pytest.raises(ValueError, match="boolean"):
        p.build_timeline((audio_asset,), separate_speakers=1)
