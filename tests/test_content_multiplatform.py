"""Generated engineering fixtures, not customer copy or language-quality proof."""
import copy
import pytest
from lumenis.shared.content_creation import multiplatform as mp


def spec(locale="en"):
    return {"title": "Demonstration launch", "brief": {"objective": "Explain the launch", "audience": "Local readers", "tone": "neutral"},
        "facts": [{"id": "launch", "role": "lead", "texts": {locale: "A demonstration exhibition opens on 20 October."}, "citation": None},
                  {"id": "context", "role": "context", "texts": {locale: "The exhibition covers local design."}, "citation": None},
                  {"id": "condition", "role": "condition", "texts": {locale: "Opening hours remain unconfirmed."}, "citation": None}],
        "variants": [{"id": genre, "genre": genre, "platform": "website" if genre != "social_post" else "linkedin",
                      "locale": locale, "title": "Demonstration exhibition"} for genre in mp.GENRES]}


def test_all_genres_real_text_no_invented_claims_different_structure():
    value = spec()
    result, citations = mp.compose(value, {})
    variants = result["package"]["variants"]
    assert len({v["body"] for v in variants}) >= 3
    for v in variants:
        assert all(f["texts"]["en"] in v["body"] for f in value["facts"])
        assert all(c["source_status"] == "USER_PROVIDED_UNVERIFIED" for c in v["claims"])
    assert citations == [] and result["package"]["generation"]["model_used"] is False
    for c in result["claims"]:
        assert result["markdown"][c["start"]:c["end"]] == c["text"]
    assert value == spec()


def test_missing_translation_never_relabels_english_as_korean():
    value = spec(); value["variants"][1]["locale"] = "ko"
    result, _ = mp.compose(value, {})
    v = result["package"]["variants"][1]
    assert v["body"] == "" and v["rendered_locale"] is None
    assert v["state"] == "TRANSLATION_UNAVAILABLE"
    for v in value["variants"]: v["locale"] = "ko"
    with pytest.raises(ValueError, match="TRANSLATION_UNAVAILABLE"): mp.compose(value, {})


@pytest.mark.parametrize("locale", mp.TARGET_LANGUAGES)
def test_target_language_selection_is_not_quality_verification(locale):
    # Supplied strings deliberately do not establish linguistic correctness.
    result, _ = mp.compose(spec(locale), {})
    assert all(v["language_quality"] == "NOT_VERIFIED" for v in result["package"]["variants"])
    assert len(mp.capabilities()["target_languages"]) >= 10


def test_no_truncation_or_fabrication_to_meet_platform_limit():
    value = spec(); value["variants"] = [dict(value["variants"][3], platform="x")]
    value["facts"][0]["texts"]["en"] = "Unconfirmed conditions. " * 20
    result, _ = mp.compose(value, {})
    v = result["package"]["variants"][0]
    assert v["state"] == "NEEDS_EDIT" and not v["format_checks"]["platform_limit_verified"]
    assert value["facts"][2]["texts"]["en"] in v["body"]


def test_sources_exact_locators_not_semantic_proof():
    value = spec(); source = {"evidence_id": 1, "text": "Original announcement", "rights": "unknown", "content_hash": "a"}
    c = {"evidence_id": 1, "start": 0, "end": len(source["text"]), "quote": source["text"]}
    value["facts"][0]["citation"] = c
    result, _ = mp.compose(value, {1: source})
    assert result["package"]["source_bindings"][0]["rights"] == "unknown"
    assert result["package"]["variants"][0]["claims"][1]["source_status"] == "SOURCE_LINKED_UNVERIFIED"
    value["facts"][0]["citation"]["quote"] = "Invented"
    with pytest.raises(ValueError, match="LOCATOR"): mp.compose(value, {1: source})


def test_edit_keeps_other_variants_resets_claims_and_conflict():
    result, _ = mp.compose(spec(), {}); package = result["package"]; v = package["variants"][0]
    edit = {"variant_id": v["id"], "expected_body_sha256": v["body_sha256"], "body": "User changed the date; review pending."}
    changed = mp.revise(package, [edit])
    assert changed["package"]["variants"][1:] == package["variants"][1:]
    assert changed["package"]["variants"][0]["claims"][0]["source_status"] == "USER_EDITED_UNVERIFIED"
    assert len(mp.differences(package, changed["package"])) == 1
    with pytest.raises(ValueError, match="CONFLICT"): mp.revise(changed["package"], [edit])


@pytest.mark.parametrize("field,value", [("facts", []), ("variants", []), ("brief", {}), ("title", "")])
def test_empty_input_cannot_generate_facts(field, value):
    data = spec(); data[field] = value
    with pytest.raises(ValueError): mp.compose(data, {})


def test_routine_template_addition_does_not_replace_existing_creative_types():
    import content_generation as content
    assert set(content.CONTENT_TYPES) == {'ad_copy', 'podcast_topic', 'brand_report', 'creative_idea',
                                         'kos_content', 'video_script', 'social_ops', 'pr_response'}
    assert callable(content.generate_content) and callable(content.regenerate_with_feedback)
    assert content.CONTENT_TYPES['creative_idea']['label'] == '创意方向'
    assert content.CONTENT_TYPES['video_script']['label'] == '视频脚本'
    assert content.CONTENT_TYPES['podcast_topic']['label'] == '播客选题'
    assert mp.capabilities()['capability_scope'] == 'routine_source_linked_templates'
    assert 'does not prove creative acceptance' in mp.capabilities()['creative_workflows']
