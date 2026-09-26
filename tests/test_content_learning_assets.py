from __future__ import annotations

from dataclasses import replace

import pytest

from lumenis.shared.learning.content_assets import (
    CONTENT_PATTERN_RECORD_KIND,
    ContentPatternRegistry,
    LearningAssetError,
    create_pattern_candidate,
    promote_pattern,
    retrieve_pattern_candidates,
)
from lumenis.shared.learning.persistence import LearningPersistence


def _candidate(**overrides):
    values = {
        "asset_type": "narrative",
        "title": "Action before explanation",
        "source_kind": "research",
        "source_refs": ("source-17",),
        "evaluation_refs": ("evaluation-4",),
        "extracted_principle": "Use observable action to carry meaning.",
        "reusable_pattern": {"sequence": ["object", "action", "meaning"]},
        "evidence_requirements": ("source evidence",),
        "originality_boundary": "No copied wording, shots, or creator identity.",
        "legal_or_compliance_boundary": "Use cleared source material.",
        "counterexamples": ("Do not omit accessibility narration.",),
        "platform_scope": ("short_video",),
        "format_scope": ("vertical",),
        "audience_scope": ("new_owners",),
        "objective_scope": ("awareness",),
    }
    values.update(overrides)
    return create_pattern_candidate(**values)


def _persistence(data_dir, *, enabled=True):
    persistence = LearningPersistence()
    persistence.init(data_dir=data_dir, enabled=enabled)
    return persistence


def _spoofed_adopt_record(candidate, *, legacy=False):
    record = candidate.to_dict()
    record.update(
        {
            "decision": "ADOPT",
            "evaluation_refs": ["self-reported-evaluation"],
            "evaluation_status": "pass",
            "reviewer": "self-asserted-reviewer",
        }
    )
    if legacy:
        record.pop("record_kind")
    else:
        assert record["record_kind"] == CONTENT_PATTERN_RECORD_KIND
    return record


def test_candidate_defaults_to_experiment_and_cannot_self_promote():
    candidate = _candidate()

    assert candidate.decision == "EXPERIMENT"
    assert candidate.evaluation_status == "unknown"
    with pytest.raises(LearningAssetError, match="CANONICAL_PROMOTION_GATE_NOT_CONNECTED"):
        promote_pattern(
            candidate,
            decision="ADOPT",
            reviewer="self-asserted-reviewer",
            evaluation_status="pass",
            evaluation_refs=("self-reported-evaluation",),
        )
    with pytest.raises(LearningAssetError, match="CANONICAL_PROMOTION_GATE_NOT_CONNECTED"):
        promote_pattern()
    assert candidate.decision == "EXPERIMENT"


def test_registry_persists_restarts_and_filters_by_scope(tmp_path):
    data_dir = tmp_path / "shared-learning"
    persistence = _persistence(data_dir)
    assert persistence.get_status()["data_dir"] == str(data_dir)
    assert persistence.save_collection("patterns", {"legacy-1": {"name": "preserve me"}})["ok"] is True

    candidate = _candidate()
    registry = ContentPatternRegistry(persistence)
    assert registry.save_candidate(candidate) == candidate

    stored = persistence.load_collection("patterns")
    assert stored["legacy-1"] == {"name": "preserve me"}
    record = stored[candidate.asset_id]
    assert record["record_kind"] == CONTENT_PATTERN_RECORD_KIND
    assert record["decision"] == "EXPERIMENT"
    assert record["source_refs"] == ["source-17"]
    assert record["evaluation_refs"] == ["evaluation-4"]
    assert record["evaluation_status"] == "unknown"
    assert record["platform_scope"] == ["short_video"]
    assert record["format_scope"] == ["vertical"]
    assert (data_dir / "patterns.json").is_file()

    restarted = ContentPatternRegistry(_persistence(data_dir))
    matches = restarted.retrieve_candidates(
        platform="short_video",
        format_name="vertical",
        audience="new_owners",
        objective="awareness",
    )
    assert matches == (candidate,)
    assert restarted.retrieve_candidates(platform="long_video") == ()
    assert restarted.retrieve_candidates(format_name="horizontal") == ()


@pytest.mark.parametrize("decision", ("ADOPT", "REVISE"))
def test_registry_rejects_caller_constructed_non_experiment_assets(tmp_path, decision):
    persistence = _persistence(tmp_path / decision.lower())
    registry = ContentPatternRegistry(persistence)
    forged = replace(
        _candidate(),
        decision=decision,
        reviewer="self-asserted-reviewer",
        evaluation_refs=("self-reported-evaluation",),
        evaluation_status="pass",
    )

    with pytest.raises(LearningAssetError, match="PATTERN_CANDIDATE_MUST_REMAIN_EXPERIMENT"):
        registry.save_candidate(forged)
    assert persistence.load_collection("patterns") is None

    with pytest.raises(LearningAssetError, match="PATTERN_CANDIDATE_MUST_REMAIN_EXPERIMENT"):
        retrieve_pattern_candidates((forged,), platform="short_video")


@pytest.mark.parametrize("legacy", (False, True), ids=("tagged", "legacy-untagged"))
def test_registry_fails_closed_on_persisted_self_reported_adopt(tmp_path, legacy):
    data_dir = tmp_path / ("legacy" if legacy else "tagged")
    persistence = _persistence(data_dir)
    candidate = _candidate()
    record = _spoofed_adopt_record(candidate, legacy=legacy)
    assert persistence.save_collection("patterns", {candidate.asset_id: record})["ok"] is True

    registry = ContentPatternRegistry(_persistence(data_dir))
    with pytest.raises(LearningAssetError, match="PATTERN_CANDIDATE_MUST_REMAIN_EXPERIMENT"):
        registry.retrieve_candidates(platform="short_video")


def test_registry_fails_closed_when_persistence_is_disabled(tmp_path):
    data_dir = tmp_path / "disabled-learning"
    registry = ContentPatternRegistry(_persistence(data_dir, enabled=False))

    with pytest.raises(LearningAssetError, match="PATTERN_PERSISTENCE_UNAVAILABLE"):
        registry.save_candidate(_candidate())
    assert not (data_dir / "patterns.json").exists()
