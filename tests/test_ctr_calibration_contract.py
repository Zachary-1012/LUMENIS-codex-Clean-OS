"""Original-owner engineering regression; generated rows are not market evidence."""
import copy
import json

import pytest

from ad_intelligence.models.ctr_predictor import CTRPredictor
from lumenis.shared.reporting import business_brief as brief
from tests.test_saved_document_workflow import workspace
from tests.test_applied_business_statistics import _source, _save_engineering_receipt


def _data():
    return {
        "rows": [{"id": f"row-{i}", "partition": "calibration" if i < 40 else "test",
                  "score": (i % 10) / 10, "label": int(i % 10 >= 5)} for i in range(80)],
        "model_provenance": {"model_id": "engineering-only", "model_version": "fixture-v1",
                             "calibration_model_version": "fixture-v1", "test_model_version": "fixture-v1",
                             "population": "generated contract test, not ads", "training_ids": ["train-1"]},
    }


def test_ctr_no_data_never_invents_probability():
    result = CTRPredictor().predict().to_dict()
    assert result["state"] == "NO_DATA"
    for key in ("predicted_ctr", "confidence", "prediction_interval", "heuristic_signal"):
        assert result[key] is None
    assert result["trained_model"] is False
    json.dumps(result, allow_nan=False)


def test_heuristic_is_separate_and_registered():
    predictor = CTRPredictor()
    result = predictor.predict({"platform": "xhs", "hour": 20, "bid_amount": 2})
    assert result.heuristic_signal == pytest.approx(0.02 * 1.15 * 1.35 * 1.004)
    assert result.predicted_ctr is None and result.confidence is None
    assert result.prediction_interval is None and result.probability_state == "UNCALIBRATED"
    assert predictor.get_model_info()["parameters"]["bid_coefficient"] == .002


@pytest.mark.parametrize("features", [[], False, {"hour": True}, {"hour": -1}, {"hour": 24},
                                       {"hour": 2.5}, {"hour": "20"}, {"hour": float("nan")},
                                       {"bid_amount": float("inf")}, {"bid_amount": -1},
                                       {"bid_amount": "2"}, {"bid_amount": True},
                                       {"platform": 2}, {"platform": " "}])
def test_ctr_invalid_values_are_not_silently_clamped(features):
    with pytest.raises(ValueError, match="CTR_"):
        CTRPredictor().predict(features)


def test_calibration_ready_does_not_promote_unverified_model():
    data = _data()
    report = brief._statistics_calibration(data)
    assert report["state"] == "READY"
    assert report["ece"] == 0 and report["brier"] == 0
    assert report["lineage_state"] == "DECLARED_DISJOINT_NOT_INDEPENDENTLY_VERIFIED"
    assert report["ctr_deployment_eligible"] is False
    assert report["prediction_interval"] is None
    # Even a perfect engineering calibration cannot activate the heuristic.
    assert CTRPredictor().predict({"platform": "xhs"}).predicted_ctr is None
    del data["model_provenance"]
    assert brief._statistics_calibration(data)["lineage_state"] == "NOT_PROVIDED"


@pytest.mark.parametrize("mutation,code", [
    (lambda d: d["model_provenance"].update(training_ids=["row-0"]), "TRAINING_LEAKAGE"),
    (lambda d: d["model_provenance"].update(training_ids=["train-1", "train-1"]), "TRAINING_LEAKAGE"),
    (lambda d: d["model_provenance"].update(test_model_version="fixture-v2"), "MODEL_VERSION_MISMATCH"),
    (lambda d: d["model_provenance"].update(model_id=""), "PROVENANCE_INVALID"),
    (lambda d: d["rows"][40].update(id="row-0"), "PARTITION_INVALID"),
    (lambda d: d["rows"][40].update(score=float("nan")), "NONFINITE|INVALID"),
])
def test_calibration_rejects_known_leakage_invalid_and_version_mismatch(mutation, code):
    data = _data()
    mutation(data)
    with pytest.raises(ValueError, match=code):
        brief._statistics_calibration(data)


def test_calibration_missing_rows_is_insufficient():
    data = _data()
    data["rows"] = data["rows"][:10]
    report = brief._statistics_calibration(data)
    assert report["state"] == "INSUFFICIENT" and "mapping" not in report
    assert report["ctr_deployment_eligible"] is False


def test_same_owner_calibration_save_revision_reopen_revoked_tampered_recovery(workspace, monkeypatch):
    monkeypatch.setattr(brief, "get_repository", lambda: workspace["repo"])
    source = _source(workspace, _data(), "calibration")
    args = {"actor": workspace["actor"], "scope": workspace["scope"]}
    result = brief.analyze_statistics_source(source["evidence_id"], **args)
    assert result["result"]["ctr_deployment_eligible"] is False
    saved = workspace["work"].save_work(**result["saved_work_draft"], request_id="ctr-calibration-v1", **args)
    aid = saved["artifact"]["artifact_id"]
    assert workspace["work"].reopen_work(aid, **args)["document"]["payload"] == result["saved_work_draft"]["payload"]
    updated = copy.deepcopy(result["saved_work_draft"])
    updated["markdown"] += "\nThis engineering fixture does not validate real CTR."
    second = workspace["work"].save_work(**updated, request_id="ctr-calibration-v2",
                                        work_id=saved["document"]["work_id"], previous_artifact_id=aid, **args)
    assert second["document"]["version"] == 2
    workspace["app"].config["LUMENIS_OPEN_WORKSPACE"] = False
    with pytest.raises(ValueError, match="PERMISSION"):
        brief.analyze_statistics_source(source["evidence_id"], **args)
    with pytest.raises(ValueError, match="PERMISSION"):
        workspace["work"].reopen_work(aid, **args)
    workspace["app"].config["LUMENIS_OPEN_WORKSPACE"] = True
    original_hash = result["saved_work_draft"]["payload"]["statistics"]["dataset_sha256"]
    workspace["repo"].execute("UPDATE app_evidence_records SET content_hash=? WHERE id=?", ("0" * 64, source["evidence_id"]))
    with pytest.raises(ValueError, match="INTEGRITY|CONTEXT"):
        brief.analyze_statistics_source(source["evidence_id"], **args)
    with pytest.raises(ValueError, match="INTEGRITY|CONTEXT"):
        workspace["work"].reopen_work(aid, **args)
    workspace["repo"].execute("UPDATE app_evidence_records SET content_hash=? WHERE id=?", (original_hash, source["evidence_id"]))
    for item in (saved, second):
        reopened = workspace["work"].reopen_work(item["artifact"]["artifact_id"], **args)
        assert reopened["artifact"]["sha256"] == item["artifact"]["sha256"]
    assert brief.analyze_statistics_source(source["evidence_id"], **args) == result
    with pytest.raises(ValueError, match="MISSING"):
        brief.analyze_statistics_source(source["evidence_id"] + 1000, **args)
    _save_engineering_receipt("ctr_calibration_lifecycle", source, result, second)
