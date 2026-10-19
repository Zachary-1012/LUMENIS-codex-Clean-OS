"""Validate persisted text before delivery; no user audio or external services."""
import json
import xml.etree.ElementTree as ET
from dataclasses import replace
from tests.test_saved_document_workflow import workspace
import pytest
from podcast.intelligence.episode_runtime import PodcastPlan, PodcastSegment, build_offline_publication_documents


def segment():
    return PodcastSegment("s1", "MEDIA-test", 0, 1, "Original", "Corrected", "Speaker", "Chapter")


@pytest.mark.parametrize("bad", ["\x00", "\x01", "\x0b", "\x0c", "\x1f", "\ufffe", "\uffff"])
@pytest.mark.parametrize("field", ["title", "description", "language"])
def test_plan_rejects_text_that_cannot_be_delivered(bad, field):
    plan = PodcastPlan("Title", "Description", "en", (segment(),))
    data = plan.to_dict()
    data[field] = "before" + bad + "after"
    with pytest.raises(ValueError, match="unsupported control|null character"):
        PodcastPlan.from_dict(data)


@pytest.mark.parametrize("field", ["original_text", "corrected_text", "speaker", "chapter_title", "segment_id", "media_asset_id"])
def test_segment_rejects_undeliverable_control_characters(field):
    data = segment().to_dict()
    data[field] = "before\x01after"
    with pytest.raises(ValueError, match="unsupported control|null character"):
        PodcastSegment.from_dict(data)


def test_valid_multilingual_whitespace_and_non_bmp_text_survive_delivery():
    text = "中文 English 한국어 😀\tline\nnext\rline & <literal>"
    source = replace(segment(), original_text=text, corrected_text=text, chapter_title=text)
    plan = PodcastPlan(text, text, "en", (source,))
    assert PodcastPlan.from_json(plan.to_json()) == plan
    delivery = build_offline_publication_documents(plan, audio_filename="episode.mp3", audio_size=10)
    assert ET.fromstring(delivery["files"]["feed.xml"]).find("channel/title").text == text.replace("\r", "\n")
    assert json.loads(delivery["files"]["podcast-plan.json"])["segments"][0]["original_text"] == text
    assert delivery["report"]["publishable"] is False


def test_correction_rejects_control_before_producing_new_revision():
    plan = PodcastPlan("Title", "Description", "en", (segment(),))
    with pytest.raises(ValueError, match="unsupported control|null character"):
        plan.with_transcript_corrections({"s1": "bad\x00text"}, expected_revision=1, expected_digest=plan.content_digest())
    assert plan.revision == 1 and plan.segments[0].corrected_text == "Corrected"


def test_saved_work_rejects_undeliverable_plan_without_artifact(workspace):
    from tests.test_saved_document_workflow import _source, _save
    _, _, source = _source(workspace, filename="control-character-source.txt")
    citation = workspace["documents"].locate_quote(source["evidence_id"], actor=workspace["actor"], scope=workspace["scope"], start=0, end=20)["citation"]
    plan = PodcastPlan("Title", "Description", "en", (segment(),))
    contract = {"id": "lumenis.podcast-plan", "version": "1", "required_payload_paths": ["podcast_plan"]}
    first = _save(workspace, kind="podcast_episode", markdown=plan.script_text(), payload={"podcast_plan":plan.to_dict()}, citations=[citation], contract=contract, request_id="valid-control-baseline")
    invalid = plan.to_dict()
    invalid["title"] = "bad\x01title"
    before = workspace["repo"].query_one("SELECT COUNT(*) FROM lumenis_shared_artifacts")[0]
    with pytest.raises(ValueError, match="WORK_PODCAST_PLAN_INVALID"):
        _save(workspace, kind="podcast_episode", markdown="bad input", payload={"podcast_plan":invalid}, citations=[citation], contract=contract, request_id="invalid-control-plan")
    assert workspace["repo"].query_one("SELECT COUNT(*) FROM lumenis_shared_artifacts")[0] == before
    assert workspace["work"].reopen_work(first["artifact"]["artifact_id"], actor=workspace["actor"], scope=workspace["scope"])["document"]["payload"]["podcast_plan"] == plan.to_dict()
