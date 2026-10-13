"""Podcast editing intent; these contract cases are not audible acceptance."""
import hashlib
import json
from dataclasses import replace

import pytest

from lumenis.shared.content_creation.video_editing import Timeline
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


def test_episode_snapshot_rejects_new_order_paired_with_prior_audio_timeline(audio_asset):
    original = plan(segment("first", media_asset_id=audio_asset.asset_id,
                            source_in=1, source_out=3, audio_stream_index=0),
                    segment("second", media_asset_id=audio_asset.asset_id,
                            source_in=10, source_out=14, audio_stream_index=0))
    prior_timeline = original.build_timeline((audio_asset,))
    reordered = original.reordered_segments(("second", "first"),
        expected_revision=original.revision, expected_digest=original.content_digest())
    with pytest.raises(ValueError, match="plan and Timeline"):
        reordered.editorial_snapshot(prior_timeline)
    rebuilt = reordered.build_timeline((audio_asset,), separate_speakers=True)
    snapshot = reordered.editorial_snapshot(rebuilt)
    assert [item["segment_id"] for item in snapshot["segments"]] == ["second", "first"]
    assert [item["timeline_start"] for item in snapshot["segments"]] == [0, 4]
    assert snapshot["plan"]["revision"] == reordered.revision
    assert snapshot["timeline"]["version"] == rebuilt.version
    assert snapshot["documents"] == reordered.editable_documents()


@pytest.mark.parametrize("changes", [{"source_in": 3}, {"audio_stream_index": 1}])
def test_episode_snapshot_rejects_source_or_stream_change_without_rebuild(audio_asset, changes):
    original = plan(segment(media_asset_id=audio_asset.asset_id, audio_stream_index=0))
    timeline = original.build_timeline((audio_asset,))
    revised = replace(original, revision=2, segments=(replace(original.segments[0], **changes),))
    with pytest.raises(ValueError, match="plan and Timeline"):
        revised.editorial_snapshot(timeline)
    assert revised.editorial_snapshot(revised.build_timeline((audio_asset,)))["plan"]["revision"] == 2


def test_episode_snapshot_keeps_text_revision_separate_from_unchanged_audio(audio_asset):
    original = plan(segment(media_asset_id=audio_asset.asset_id, audio_stream_index=0))
    timeline = original.build_timeline((audio_asset,))
    before = original.editorial_snapshot(timeline)
    corrected = original.with_transcript_corrections({"s1": "A corrected condition, not new speech."},
        expected_revision=original.revision, expected_digest=original.content_digest())
    after = corrected.editorial_snapshot(timeline)
    assert before["timeline"] == after["timeline"]
    assert before["plan"] != after["plan"]
    assert before["segments"] == after["segments"]
    assert after["documents"]["transcript-original.vtt"] == before["documents"]["transcript-original.vtt"]
    assert "A corrected condition, not new speech." in after["documents"]["transcript-corrected.vtt"]
    assert after["reviews"] == {
        "transcript_audio_alignment": "NEEDS_REVIEW", "audio_review": "NEEDS_REVIEW",
        "caption_review": "NEEDS_REVIEW", "factual_semantics": "NEEDS_REVIEW",
    }
    assert after["rendition_binding"] is None
    assert json.loads(after["documents"]["metadata.json"])["transcript_edits_change_audio"] is False


def test_episode_snapshot_binds_actual_mix_without_overwriting_editorial_documents(audio_asset):
    from lumenis.shared.content_creation.video_editing import AudioMix

    p = plan(segment(media_asset_id=audio_asset.asset_id, audio_stream_index=0))
    original = p.build_timeline((audio_asset,))
    voice = original.tracks[1].clips[0]
    mixed = original.set_audio_mix(voice.clip_id, AudioMix(volume=0.5, fade_in_sec=0.1))
    mixed = mixed.add_audio_track("environment", audio_role="sfx").add_clip(
        audio_asset.asset_id, source_in=20, source_out=22, timeline_start=0,
        track_id="environment", audio_role="sfx", audio_stream_index=1,
        purpose="permitted environment, not claimed speech",
    )
    before, after = p.editorial_snapshot(original), p.editorial_snapshot(mixed)
    assert before["plan"] == after["plan"]
    assert before["documents"] == after["documents"]
    assert before["timeline"] != after["timeline"]
    assert after["additional_clip_ids"] == [mixed.tracks[2].clips[0].clip_id]
    assert after["rendition_binding"] is None


@pytest.mark.parametrize("damage", ["missing", "extra", "changed"])
def test_episode_snapshot_reopen_rejects_incomplete_or_tampered_editorial_members(audio_asset, damage):
    p = plan(segment(media_asset_id=audio_asset.asset_id, audio_stream_index=0))
    timeline = p.build_timeline((audio_asset,))
    documents = p.editable_documents()
    assert p.editorial_snapshot(timeline, documents=documents)["documents"] == documents
    if damage == "missing":
        documents.pop("chapters.json")
    elif damage == "extra":
        documents["alternate-script.txt"] = "unbound draft"
    else:
        documents["script.txt"] += "\nUnbound words"
    with pytest.raises(ValueError, match="editorial documents"):
        p.editorial_snapshot(timeline, documents=documents)


def test_episode_snapshot_rejects_duplicate_planned_segment_and_shifted_timing(audio_asset):
    p = plan(segment(media_asset_id=audio_asset.asset_id, audio_stream_index=0))
    timeline = p.build_timeline((audio_asset,))
    duplicate = timeline.add_audio_track("duplicate", audio_role="voiceover").add_clip(
        audio_asset.asset_id, source_in=4, source_out=7, timeline_start=0,
        track_id="duplicate", audio_role="voiceover", audio_stream_index=0,
        purpose="podcast-segment:s1",
    )
    with pytest.raises(ValueError, match="plan and Timeline"):
        p.editorial_snapshot(duplicate)
    voice_track = timeline.tracks[1]
    shifted = replace(timeline, tracks=(timeline.tracks[0], replace(voice_track,
        clips=(replace(voice_track.clips[0], timeline_start=0.25),))))
    with pytest.raises(ValueError, match="plan and Timeline"):
        p.editorial_snapshot(shifted)


def test_reopened_snapshot_round_trip_preserves_exact_editorial_members_and_rejects_tampering(audio_asset):
    p = plan(segment(media_asset_id=audio_asset.asset_id, audio_stream_index=0))
    timeline = p.build_timeline((audio_asset,), separate_speakers=True)
    reopened_plan = PodcastPlan.from_json(p.to_json())
    reopened_timeline = Timeline.from_dict(
        json.loads(json.dumps(timeline.to_dict())), assets=(audio_asset,),
    )

    original_snapshot = p.editorial_snapshot(timeline)
    reopened_snapshot = reopened_plan.editorial_snapshot(reopened_timeline)
    expected_members = {
        "podcast-plan.json", "script.txt", "transcript-original.vtt",
        "transcript-corrected.vtt", "chapters.json", "corrections.json", "metadata.json",
    }
    assert reopened_snapshot == original_snapshot
    assert set(reopened_snapshot["documents"]) == expected_members
    assert set(reopened_snapshot["members"]) == expected_members
    assert reopened_snapshot["members"] == {
        name: {
            "size_bytes": len(text.encode("utf-8")),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }
        for name, text in reopened_snapshot["documents"].items()
    }

    tampered_documents = dict(reopened_snapshot["documents"])
    tampered_documents["script.txt"] += "\nUnbound reopened text"
    with pytest.raises(ValueError, match="editorial documents"):
        reopened_plan.editorial_snapshot(reopened_timeline, documents=tampered_documents)


def test_legacy_v1_stream_defaults_and_null_timeline_clip_boundary(audio_asset, monkeypatch):
    from lumenis.shared.content_creation import video_editing

    multi_stream_probe = video_editing._probe_media_info
    monkeypatch.setattr(
        video_editing, "_probe_media_info",
        lambda _: video_editing._MediaProbe(60, False, 1),
    )
    single_stream_asset = video_editing.fingerprint_local_media(audio_asset.path)
    legacy_payload = plan(segment(media_asset_id=single_stream_asset.asset_id)).to_dict()
    assert legacy_payload["version"] == 1
    assert "audio_stream_index" not in legacy_payload["segments"][0]
    legacy_plan = PodcastPlan.from_json(json.dumps(legacy_payload))
    assert legacy_plan.segments[0].audio_stream_index is None
    single_stream_timeline = legacy_plan.build_timeline((single_stream_asset,))
    assert single_stream_timeline.tracks[1].clips[0].audio_stream_index == 0
    snapshot = legacy_plan.editorial_snapshot(single_stream_timeline)
    assert snapshot["segments"][0]["audio_stream_index"] == 0

    monkeypatch.setattr(video_editing, "_probe_media_info", multi_stream_probe)
    multi_stream_legacy_plan = PodcastPlan.from_json(
        plan(segment(media_asset_id=audio_asset.asset_id)).to_json(),
    )
    assert multi_stream_legacy_plan.segments[0].audio_stream_index is None
    selected_multi_stream_timeline = plan(segment(
        media_asset_id=audio_asset.asset_id, audio_stream_index=0,
    )).build_timeline((audio_asset,))
    multi_stream_document = selected_multi_stream_timeline.to_dict()
    multi_stream_document["tracks"][1]["clips"][0]["audio_stream_index"] = None
    with pytest.raises(ValueError, match="AUDIO_STREAM_SELECTION_REQUIRED"):
        Timeline.from_dict(multi_stream_document, assets=(audio_asset,))
    with pytest.raises(ValueError, match="explicit selection is required"):
        multi_stream_legacy_plan.build_timeline((audio_asset,))
    with pytest.raises(ValueError, match="explicit audio stream selection"):
        multi_stream_legacy_plan.editorial_snapshot(selected_multi_stream_timeline)


def test_separate_speaker_lanes_reject_reassigned_planned_clips(audio_asset):
    p = plan(
        segment("guest", media_asset_id=audio_asset.asset_id, speaker="Guest", audio_stream_index=0),
        segment("host", media_asset_id=audio_asset.asset_id, speaker="Host", audio_stream_index=0),
    )
    labels = p.voice_track_labels()
    guest_track_id = next(track_id for track_id, speaker in labels.items() if speaker == "Guest")
    host_track_id = next(track_id for track_id, speaker in labels.items() if speaker == "Host")
    separate = p.build_timeline((audio_asset,), separate_speakers=True)
    separate_snapshot = p.editorial_snapshot(separate)
    assert {item["segment_id"]: item["track_id"] for item in separate_snapshot["segments"]} == {
        "guest": guest_track_id, "host": host_track_id,
    }

    tracks = {track.track_id: track for track in separate.tracks}
    guest_clip = tracks[guest_track_id].clips[0]
    host_clip = tracks[host_track_id].clips[0]
    swapped_tracks = []
    for track in separate.tracks:
        if track.track_id == guest_track_id:
            swapped_tracks.append(replace(track, clips=(replace(host_clip, track_id=track.track_id),)))
        elif track.track_id == host_track_id:
            swapped_tracks.append(replace(track, clips=(replace(guest_clip, track_id=track.track_id),)))
        else:
            swapped_tracks.append(track)
    swapped = replace(separate, tracks=tuple(swapped_tracks))
    with pytest.raises(ValueError, match="podcast plan and Timeline"):
        p.editorial_snapshot(swapped)

    combined = p.build_timeline((audio_asset,))
    assert combined.tracks[1].track_id == "podcast_voice"
    assert len(p.editorial_snapshot(combined)["segments"]) == 2
