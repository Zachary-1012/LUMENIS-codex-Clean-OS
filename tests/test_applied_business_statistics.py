"""Engineering inputs exercise custody/permission/save lifecycle, not market validation."""

import json
import math
import pytest
from tests.test_saved_document_workflow import workspace
from canonical_metrics import binomial_confidence, share_of_voice
from lumenis.shared.reporting import business_brief as brief
from lumenis.system.security import permission


def _source(workspace, data, analysis="binomial"):
    path = workspace["root"] / f"{analysis}.txt"
    path.write_text(
        json.dumps(
            {
                "schema": "lumenis.statistics-input/v1",
                **({"analysis": analysis} if analysis is not None else {}),
                "unit": "trial",
                "data": data,
            }
        ),
        encoding="utf-8",
    )
    args = {
        "actor": workspace["actor"],
        "scope": workspace["scope"],
        "provenance": {
            "source_url": None,
            "source_origin": {"kind": "approved-file", "ref": "engineering-statistics"},
            "published_at": None,
            "captured_at": "2026-10-17T01:00:00Z",
            "rights": "owner-approved",
            "title": "Explicit engineering input, not market observations",
        },
    }
    resource = workspace["documents"].document_import_resource(str(path), **args)
    workspace["gate"].grant_approval(
        permission.OperationType.DATA_IMPORT.value,
        resource=resource,
        granted_by="isolated-test",
    )
    return workspace["documents"].import_document(str(path), **args)


def _save_engineering_receipt(name, source, result, saved):
    """Optional external verification output, never a product storage owner."""
    import os
    from pathlib import Path

    target = os.environ.get("LUMENIS_STATISTICS_EVIDENCE_DIR")
    if target:
        Path(target, name + ".json").write_text(
            json.dumps(
                {
                    "source": source,
                    "analysis": result,
                    "saved": saved,
                    "claim": "Self-owned engineering fixture and source custody; not real-market acceptance",
                },
                indent=2,
            )
        )


def test_wilson_matches_official_library():
    from statsmodels.stats.proportion import proportion_confint

    for k, n in [(0, 1), (1, 1), (3, 10), (37, 100), (999, 1000)]:
        actual = binomial_confidence(k, n)
        assert actual["interval"] == pytest.approx(
            proportion_confint(k, n, method="wilson")
        )
    assert binomial_confidence(0, 0)["value"] is None
    for k, n in [(True, 10), (2, 1), (-1, 5), (1, 2.0)]:
        with pytest.raises(ValueError):
            binomial_confidence(k, n)


def test_real_import_compute_save_revision_reopen_and_source_integrity(
    workspace, monkeypatch
):
    monkeypatch.setattr(brief, "get_repository", lambda: workspace["repo"])
    source = _source(workspace, {"successes": 37, "trials": 100})
    result = brief.analyze_statistics_source(
        source["evidence_id"], actor=workspace["actor"], scope=workspace["scope"]
    )
    assert result["result"]["value"] == 0.37 and result["ai_used"] is False
    draft = result["saved_work_draft"]
    saved = workspace["work"].save_work(
        **draft,
        request_id="statistics-save-01",
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    aid = saved["artifact"]["artifact_id"]
    reopened = workspace["work"].reopen_work(
        aid, actor=workspace["actor"], scope=workspace["scope"]
    )
    assert reopened["document"]["payload"] == draft["payload"]
    second = workspace["work"].save_work(
        **{
            **draft,
            "markdown": draft["markdown"] + "\nReviewer: retain sampling caveat.",
        },
        request_id="statistics-save-02",
        work_id=saved["document"]["work_id"],
        previous_artifact_id=aid,
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    assert second["document"]["version"] == 2
    assert (
        workspace["work"].reopen_work(
            aid, actor=workspace["actor"], scope=workspace["scope"]
        )["document"]["version"]
        == 1
    )
    assert (
        workspace["work"].reopen_work(
            second["artifact"]["artifact_id"],
            actor=workspace["actor"],
            scope=workspace["scope"],
        )["document"]["version"]
        == 2
    )
    with workspace["repo"].transaction() as con:
        con.execute(
            "UPDATE app_evidence_records SET content_hash=? WHERE id=?",
            ("0" * 64, source["evidence_id"]),
        )
    with pytest.raises(ValueError, match="INTEGRITY|CONTEXT"):
        brief.analyze_statistics_source(
            source["evidence_id"], actor=workspace["actor"], scope=workspace["scope"]
        )
    with pytest.raises(ValueError, match="INTEGRITY|CONTEXT"):
        workspace["work"].reopen_work(
            aid, actor=workspace["actor"], scope=workspace["scope"]
        )


def test_missing_inputs_never_zero_success(workspace, monkeypatch):
    monkeypatch.setattr(brief, "get_repository", lambda: workspace["repo"])
    source = _source(workspace, {"successes": 0, "trials": 0})
    result = brief.analyze_statistics_source(
        source["evidence_id"], actor=workspace["actor"], scope=workspace["scope"]
    )
    assert result["state"] == "NO_DATA" and result["result"]["interval"] is None
    with pytest.raises(ValueError):
        brief.analyze_statistics_source(
            source["evidence_id"],
            actor=workspace["actor"],
            scope=workspace["scope"],
            options={"horizon": 1},
        )


def test_network_observed_edges_only():
    data = {
        "nodes": ["a", "b", "c"],
        "edges": [
            {"source": "a", "target": "b", "relation": "mention"},
            {"source": "b", "target": "c", "relation": "repost"},
        ],
    }
    result = brief._statistics_network(data)
    assert sum(row["pagerank"] for row in result["nodes"]) == pytest.approx(1)
    assert result["nodes"][1]["betweenness"] > 0
    assert (
        brief._statistics_network({"nodes": ["a"], "edges": []})["state"] == "NO_DATA"
    )
    with pytest.raises(ValueError):
        brief._statistics_network(
            {
                "nodes": ["a", "b"],
                "edges": [{"source": "a", "target": "b", "relation": "inferred"}],
            }
        )


def test_decision_consistency_and_budget_constraints():
    data = {
        "alternatives": ["a", "b", "c"],
        "matrix": [[8, 6], [4, 3], [7, 8]],
        "pairwise": [[1, 2], [0.5, 1]],
        "benefit": [True, False],
    }
    result = brief._statistics_decision(data)
    assert result["state"] == "READY" and result["consistency_ratio"] == pytest.approx(
        0
    )
    result = brief._statistics_portfolio(
        {
            "items": [
                {"id": "a", "cost": 4, "benefit": 5, "coverage": ["x"]},
                {"id": "b", "cost": 6, "benefit": 8, "coverage": ["y"]},
                {"id": "c", "cost": 10, "benefit": 10, "coverage": ["x", "y"]},
            ],
            "budget": 10,
            "required_coverage": ["x", "y"],
            "unit": "declared utility",
        }
    )
    assert result["selected"] == ["a", "b"] and result["benefit"] == 13
    assert (
        brief._statistics_portfolio(
            {
                "items": [{"id": "a", "cost": 4, "benefit": 5, "coverage": ["x"]}],
                "budget": 3,
                "required_coverage": ["x"],
            }
        )["reason"]
        == "INFEASIBLE"
    )


def test_calibration_disjoint_partitions():
    rows = [
        {
            "id": str(i),
            "partition": "calibration" if i < 40 else "test",
            "score": (i % 10) / 10,
            "label": int(i % 10 >= 5),
        }
        for i in range(80)
    ]
    result = brief._statistics_calibration({"rows": rows})
    assert result["state"] == "READY" and result["test_n"] == 40 and result["ece"] == 0
    rows[-1]["id"] = rows[0]["id"]
    with pytest.raises(ValueError):
        brief._statistics_calibration({"rows": rows})


def test_trend_uses_disjoint_holdout():
    from trend_api import analyze_observed_series

    values = [
        30 + 0.15 * i + 3 * math.sin(2 * math.pi * i / 7) + 0.5 * math.sin(i * 1.37)
        for i in range(70)
    ]
    result = analyze_observed_series(values, unit="daily observed posts")
    assert result["state"] == "READY"
    assert result["holdout"]["train_n"] + result["holdout"]["test_n"] == 70
    assert len(result["forecast"]["intervals"]) == 7
    assert analyze_observed_series(values[:13], unit="posts")["state"] == "INSUFFICIENT"
    with pytest.raises(ValueError):
        analyze_observed_series([None] * 20, unit="posts")


def test_novelty_experiment_conformal_known_values():
    assert (
        brief._statistics_novelty(
            {"current_counts": {"a": 2, "b": 2}, "historical_counts": {"a": 2, "b": 2}}
        )["kl"]
        == 0
    )
    assert (
        brief._statistics_novelty(
            {"current_counts": {"a": 2, "b": 2}, "historical_counts": {"a": 0, "b": 4}}
        )["divergence_state"]
        == "POSITIVE_INFINITY"
    )
    experiment = {
        "arms": [
            {"id": "a", "successes": 10, "trials": 20},
            {"id": "b", "successes": 10, "trials": 20},
        ],
        "stop_probability": 0.95,
        "minimum_trials": 20,
        "enable_thompson": True,
        "seed": 42,
    }
    result = brief._statistics_experiment(experiment)
    assert result["comparison"]["probability_first_better"] == pytest.approx(0.5)
    assert result["comparison"]["stop_recommended"] is False
    assert result == brief._statistics_experiment(experiment)
    rows = [
        {
            "id": str(i),
            "partition": "calibration" if i < 20 else "test",
            "prediction": 100,
            "observed": 100 + (i % 20),
        }
        for i in range(40)
    ]
    conformal = brief._statistics_conformal({"rows": rows, "alpha": 0.1})
    assert (
        conformal["order_statistic_rank"] == 19 and conformal["residual_quantile"] == 18
    )
    assert conformal["test_coverage"] == 0.95


def test_did_parallel_pretrend_rejected_and_known_effect():
    control = [30 + 0.5 * i + math.sin(i) for i in range(24)]
    treated = [
        x + 3 + (2 if i >= 16 else 0) + 0.001 * math.sin(i * 2)
        for i, x in enumerate(control)
    ]
    result = brief._statistics_did(
        {
            "treated": treated,
            "control": control,
            "intervention_index": 16,
            "pretrend_tolerance": 0.05,
            "design_assumptions_confirmed": True,
        }
    )
    assert result["state"] == "READY" and result["effect"] == pytest.approx(
        2, abs=0.001
    )
    rejected = brief._statistics_did(
        {
            "treated": [x + i for i, x in enumerate(control)],
            "control": control,
            "intervention_index": 16,
            "pretrend_tolerance": 0.05,
            "design_assumptions_confirmed": True,
        }
    )
    assert rejected["state"] == "INSUFFICIENT" and rejected["effect"] is None


def test_markov_shapley_exact_known_credit():
    result = brief._statistics_attribution(
        {
            "paths": [
                {"id": "a", "channels": ["a"], "converted": True},
                {"id": "b", "channels": ["b"], "converted": True},
            ]
        }
    )
    assert result["baseline_probability"] == 1
    assert [c["shapley"] for c in result["channels"]] == pytest.approx([0.5, 0.5])
    synergy = brief._statistics_attribution(
        {"paths": [{"id": "x", "channels": ["a", "b"], "converted": True}]}
    )
    assert [c["shapley"] for c in synergy["channels"]] == pytest.approx([0.5, 0.5])


def test_entity_matching_heldout_and_classifier_unknown():
    rows = [
        {
            "id": str(i),
            "partition": "train" if i < 40 else "test",
            "agreements": [bool(i % 2), bool(i % 2)],
            "label": i % 2,
        }
        for i in range(80)
    ]
    result = brief._statistics_entity_matching(
        {
            "rows": rows
            + [
                {
                    "id": "candidate",
                    "partition": "candidate",
                    "agreements": [True, False],
                    "label": None,
                }
            ]
        }
    )
    assert result["precision"] == 1 and result["recall"] == 1
    assert result["candidates"][0]["recommendation"] == "MANUAL_REVIEW"
    classifier = brief._statistics_classifier_evaluation(
        {
            "model_version": "engineering-v1",
            "heldout_declared": True,
            "confidence_threshold": 0.8,
            "rows": [
                {
                    "id": "a",
                    "language": "zh",
                    "label": "positive",
                    "probabilities": {"positive": 0.4, "negative": 0.3, "neutral": 0.3},
                }
            ],
        }
    )
    assert classifier["languages"]["zh"]["unknown_n"] == 1
    assert classifier["languages"]["zh"]["ratio_denominator"] == 0
    assert classifier["languages"]["en"]["state"] == "NO_DATA"


@pytest.mark.parametrize(
    "analysis,data",
    [
        (
            "sov",
            {
                "counts": {"a": 10, "b": 30},
                "platform_coverage": ["owned-engineering"],
                "observation_window": "2026-10-01/2026-10-02",
            },
        ),
        (
            "network",
            {
                "nodes": ["a", "b"],
                "edges": [{"source": "a", "target": "b", "relation": "mention"}],
            },
        ),
        (
            "decision",
            {
                "alternatives": ["a", "b"],
                "matrix": [[8, 4], [6, 3]],
                "pairwise": [[1, 2], [0.5, 1]],
                "benefit": [True, False],
            },
        ),
        (
            "portfolio",
            {
                "items": [{"id": "a", "cost": 4, "benefit": 5, "coverage": ["x"]}],
                "budget": 4,
                "required_coverage": ["x"],
            },
        ),
        (
            "novelty",
            {"current_counts": {"a": 1, "b": 2}, "historical_counts": {"a": 2, "b": 1}},
        ),
        ("attribution", {"paths": [{"id": "a", "channels": ["a"], "converted": True}]}),
        (
            "experiment",
            {
                "arms": [
                    {"id": "a", "successes": 10, "trials": 20},
                    {"id": "b", "successes": 5, "trials": 20},
                ],
                "stop_probability": 0.95,
                "minimum_trials": 20,
                "enable_thompson": False,
                "seed": 42,
            },
        ),
    ],
)
def test_all_method_source_save_roundtrips(workspace, monkeypatch, analysis, data):
    monkeypatch.setattr(brief, "get_repository", lambda: workspace["repo"])
    source = _source(workspace, data, analysis=analysis)
    result = brief.analyze_statistics_source(
        source["evidence_id"], actor=workspace["actor"], scope=workspace["scope"]
    )
    assert result["state"] == "READY"
    saved = workspace["work"].save_work(
        **result["saved_work_draft"],
        request_id="statistics-" + analysis + "-save",
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    reopened = workspace["work"].reopen_work(
        saved["artifact"]["artifact_id"],
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    assert reopened["document"]["payload"]["statistics"]["result"] == result["result"]


def test_mmm_insufficient_real_periods_and_no_variation():
    data = {
        "periods": [],
        "currency": "USD",
        "outcome_unit": "sales USD",
        "filing_entity": "Engineering entity",
        "disclosure_scope": "group",
        "spend_basis": "public_proxy",
    }
    assert brief._statistics_mmm(data)["reason"] == "NEED_AT_LEAST_12_REAL_QUARTERS"
    data["periods"] = [
        {
            "period": f"{2020+i//4}-Q{i%4+1}",
            "outcome": 100 + i,
            "spend": {"channel": 10},
        }
        for i in range(16)
    ]
    assert (
        brief._statistics_mmm(data)["reason"]
        == "NO_TRAINING_CHANNEL_OR_OUTCOME_VARIATION"
    )
    data["budget"] = {"total": 1, "lower": {"channel": 2}, "upper": {"channel": 3}}
    with pytest.raises(ValueError, match="BUDGET_INFEASIBLE"):
        brief._statistics_mmm(data)


def test_hawkes_small_sample_refuses():
    result = brief._statistics_hawkes(
        {"times": [1, 2, 3], "observation_end": 10, "time_unit": "days"}
    )
    assert result["state"] == "INSUFFICIENT"
    with pytest.raises(ValueError):
        brief._statistics_hawkes(
            {"times": [1, 1, 3], "observation_end": 10, "time_unit": "days"}
        )


def test_bass_recovers_known_curve_and_backtest():
    times = [i / 4 for i in range(1, 81)]
    p, q, m = 0.03, 0.38, 1000
    cumulative = [
        m * (1 - math.exp(-(p + q) * t)) / (1 + q / p * math.exp(-(p + q) * t))
        for t in times
    ]
    result = brief._statistics_bass(
        {"times": times, "cumulative": cumulative, "time_unit": "weeks"}
    )
    assert result["state"] == "READY"
    assert result["innovation"] == pytest.approx(p, rel=0.001)
    assert result["imitation"] == pytest.approx(q, rel=0.001)
    assert result["market_potential"] == pytest.approx(m, rel=0.001)
    assert result["holdout"]["final_cumulative_relative_error"] < 0.001


def test_beta_binomial_shrinkage_preserves_missingness():
    groups = [
        {"id": str(i), "successes": k, "trials": n}
        for i, (k, n) in enumerate(
            [(1, 2), (20, 100), (25, 100), (60, 100), (70, 100), (50, 100), (0, 0)]
        )
    ]
    result = brief._statistics_beta_ranking({"groups": groups})
    assert result["state"] == "READY"
    assert result["groups"][-1]["posterior_mean"] is None
    assert abs(
        result["groups"][0]["posterior_mean"]
        - result["alpha"] / (result["alpha"] + result["beta"])
    ) < abs(0.5 - result["alpha"] / (result["alpha"] + result["beta"]))


def test_hawkes_seeded_branching_process_is_nonempty():
    import numpy as np

    rng = np.random.default_rng(314)
    end = 80
    events = list(rng.uniform(0, end, rng.poisson(2 * end)))
    queue = list(events)
    while queue:
        parent = queue.pop()
        for delay in rng.exponential(0.5, rng.poisson(0.6)):
            child = parent + delay
            if child < end:
                events.append(child)
                queue.append(child)
    result = brief._statistics_hawkes(
        {
            "times": [float(t) for t in sorted(events)],
            "observation_end": end,
            "time_unit": "days",
        }
    )
    assert result["state"] == "READY"
    assert 0 < result["branching_ratio"] < 1
    assert result["holdout"]["train_n"] >= 30
    assert result["holdout"]["predicted_count"] > 0
    assert result["finite_peak_time"] is None


def test_bayesian_mmm_source_save_reopen(workspace, monkeypatch):
    """Actual CPU posterior from owned synthetic data, never a market ROI acceptance."""
    import numpy as np
    from pathlib import Path

    monkeypatch.setattr(brief, "get_repository", lambda: workspace["repo"])
    monkeypatch.setenv(
        "PYTENSOR_FLAGS", "base_compiledir=" + str(workspace["root"] / "pytensor")
    )
    monkeypatch.setenv("MPLCONFIGDIR", str(workspace["root"] / "mpl"))
    rng = np.random.default_rng(1701)
    n = 48
    x = rng.uniform(20, 180, n)
    weights = 0.3 ** np.arange(8)
    carry = np.array(
        [
            sum(weights[j] * x[i - j] for j in range(min(i + 1, 8))) / weights.sum()
            for i in range(n)
        ]
    )
    y = (
        100
        + 70 * carry / (80 + carry)
        + 4 * np.sin(2 * np.pi * np.arange(n) / 4)
        + rng.normal(0, 2, n)
    )
    data = {
        "periods": [
            {
                "period": f"{2010+i//4}-Q{i%4+1}",
                "outcome": float(y[i]),
                "spend": {"owned_channel": float(x[i])},
            }
            for i in range(n)
        ],
        "currency": "USD",
        "outcome_unit": "trial",
        "filing_entity": "Owned engineering simulation",
        "disclosure_scope": "group",
        "spend_basis": "user_declared",
        "budget": {
            "total": 100,
            "lower": {"owned_channel": 0},
            "upper": {"owned_channel": 200},
        },
    }
    source = _source(workspace, data, analysis="mmm")
    result = brief.analyze_statistics_source(
        source["evidence_id"], actor=workspace["actor"], scope=workspace["scope"]
    )
    assert result["state"] == "READY", result["result"].get("reason")
    assert result["result"]["sampling"]["divergences"] == 0
    assert result["result"]["sampling"]["max_rhat"] <= 1.05
    assert result["result"]["sampling"]["min_ess_bulk"] >= 200
    saved = workspace["work"].save_work(
        **result["saved_work_draft"],
        request_id="statistics-mmm-save",
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    reopened = workspace["work"].reopen_work(
        saved["artifact"]["artifact_id"],
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    assert reopened["document"]["payload"]["statistics"]["result"] == result["result"]
    receipt = {
        "source": source,
        "saved": saved,
        "reopened_hash": reopened["artifact"]["sha256"],
        "claim": "Owned engineering input and CPU model lifecycle; not observed marketing ROI",
    }
    import os

    target = (
        Path(os.environ.get("LUMENIS_STATISTICS_EVIDENCE_DIR", str(workspace["root"])))
        / "mmm_saved_source_result.json"
    )
    # Evidence is deliberately outside product data/storage and contains only owned engineering input.
    target.write_text(json.dumps(receipt, indent=2))


@pytest.mark.parametrize(
    "analysis",
    [
        "calibration",
        "conformal",
        "did",
        "entity_matching",
        "classifier_evaluation",
        "beta_ranking",
        "bass",
        "net_sentiment",
    ],
)
def test_additional_method_source_custody_and_saved_result(
    workspace, monkeypatch, analysis
):
    monkeypatch.setattr(brief, "get_repository", lambda: workspace["repo"])
    if analysis == "calibration":
        data = {
            "rows": [
                {
                    "id": str(i),
                    "partition": "calibration" if i < 40 else "test",
                    "score": (i % 10) / 10,
                    "label": int(i % 10 >= 5),
                }
                for i in range(80)
            ]
        }
    elif analysis == "conformal":
        data = {
            "rows": [
                {
                    "id": str(i),
                    "partition": "calibration" if i < 20 else "test",
                    "prediction": 100,
                    "observed": 100 + i % 20,
                }
                for i in range(40)
            ],
            "alpha": 0.1,
        }
    elif analysis == "did":
        control = [30 + 0.5 * i + math.sin(i) for i in range(24)]
        data = {
            "treated": [
                x + 3 + (2 if i >= 16 else 0) + 0.001 * math.sin(i * 2)
                for i, x in enumerate(control)
            ],
            "control": control,
            "intervention_index": 16,
            "pretrend_tolerance": 0.05,
            "design_assumptions_confirmed": True,
        }
    elif analysis == "entity_matching":
        data = {
            "rows": [
                {
                    "id": str(i),
                    "partition": "train" if i < 40 else "test",
                    "agreements": [bool(i % 2), bool(i % 2)],
                    "label": i % 2,
                }
                for i in range(80)
            ]
        }
    elif analysis == "classifier_evaluation":
        data = {
            "model_version": "engineering-v1",
            "heldout_declared": True,
            "confidence_threshold": 0.8,
            "rows": [
                {
                    "id": "a",
                    "language": "zh",
                    "label": "positive",
                    "probabilities": {
                        "positive": 0.9,
                        "negative": 0.05,
                        "neutral": 0.05,
                    },
                }
            ],
        }
    elif analysis == "beta_ranking":
        data = {
            "groups": [
                {"id": str(i), "successes": k, "trials": n}
                for i, (k, n) in enumerate(
                    [
                        (1, 2),
                        (20, 100),
                        (25, 100),
                        (60, 100),
                        (70, 100),
                        (50, 100),
                        (0, 0),
                    ]
                )
            ]
        }
    elif analysis == "net_sentiment":
        data = {
            "records": [
                {"sentiment": "positive"},
                {"sentiment": "neutral"},
                {"sentiment": "negative"},
                {"sentiment": "unknown"},
            ]
        }
    else:
        times = [i / 4 for i in range(1, 81)]
        data = {
            "times": times,
            "cumulative": [
                1000
                * (1 - math.exp(-0.41 * t))
                / (1 + 0.38 / 0.03 * math.exp(-0.41 * t))
                for t in times
            ],
            "time_unit": "weeks",
        }
    source = _source(workspace, data, analysis)
    result = brief.analyze_statistics_source(
        source["evidence_id"], actor=workspace["actor"], scope=workspace["scope"]
    )
    assert result["state"] == "READY"
    saved = workspace["work"].save_work(
        **result["saved_work_draft"],
        request_id="statistics-extra-" + analysis,
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    reopened = workspace["work"].reopen_work(
        saved["artifact"]["artifact_id"],
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    assert reopened["document"]["payload"]["statistics"]["result"] == result["result"]


def test_optional_topics_source_save_reopen(workspace, monkeypatch):
    """Optional official lexical BERTopic path; main runtime remains valid without it."""
    monkeypatch.setattr(brief, "get_repository", lambda: workspace["repo"])
    documents = ["apple orchard fruit harvest sweet tree " + str(i) for i in range(15)]
    documents += [
        "rocket galaxy orbit space astronaut telescope " + str(i) for i in range(15)
    ]
    source = _source(workspace, {"documents": documents, "language": "en"}, "topics")
    result = brief.analyze_statistics_source(
        source["evidence_id"], actor=workspace["actor"], scope=workspace["scope"]
    )
    if result["state"] == "UNAVAILABLE":
        assert (
            result["result"]["reason"] in {"OPTIONAL_BERTOPIC_DEPENDENCIES_UNAVAILABLE", "STATISTICS_REQUIRED_DEPENDENCIES_UNAVAILABLE"}
        )
        from importlib.util import find_spec

        assert (
            find_spec("bertopic") is None
        ), "Installed topic capability must execute rather than hide dependency failure"
    else:
        assert result["state"] == "READY"
        labels = result["result"]["assignments"]
        assert (
            len(set(labels[:15])) == 1
            and len(set(labels[15:])) == 1
            and labels[0] != labels[-1]
        )
    saved = workspace["work"].save_work(
        **result["saved_work_draft"],
        request_id="statistics-optional-topics",
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    reopened = workspace["work"].reopen_work(
        saved["artifact"]["artifact_id"],
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    assert reopened["document"]["payload"]["statistics"]["result"] == result["result"]


def test_business_purpose_discovery_and_source_selection(workspace, monkeypatch):
    monkeypatch.setattr(brief, "get_repository", lambda: workspace["repo"])
    capabilities = brief.statistics_capabilities()
    rows = capabilities["capabilities"]
    assert len(rows) == 24
    assert len({row["business_purpose"] for row in rows}) == 24
    assert all(row["ai_required"] is False for row in rows)
    source = _source(workspace, {"successes": 37, "trials": 100}, analysis=None)
    kwargs = {"actor": workspace["actor"], "scope": workspace["scope"]}
    result = brief.analyze_statistics_source(
        source["evidence_id"], business_purpose="assess_rate_reliability", **kwargs
    )
    assert result["result"]["value"] == 0.37
    assert result["business_purpose"] == "assess_rate_reliability"
    with pytest.raises(ValueError, match="PURPOSE_REQUIRED"):
        brief.analyze_statistics_source(source["evidence_id"], **kwargs)
    with pytest.raises(ValueError, match="PURPOSE_INVALID"):
        brief.analyze_statistics_source(
            source["evidence_id"], business_purpose="invented", **kwargs
        )
    expert = _source(workspace, {"successes": 37, "trials": 100})
    with pytest.raises(ValueError, match="PURPOSE_CONFLICT"):
        brief.analyze_statistics_source(
            expert["evidence_id"], business_purpose="understand_change", **kwargs
        )


@pytest.mark.parametrize("analysis", ["nps", "som"])
def test_recommendation_and_sales_source_save_reopen(workspace, monkeypatch, analysis):
    monkeypatch.setattr(brief, "get_repository", lambda: workspace["repo"])
    if analysis == "nps":
        data = {
            "question_type": "likelihood_to_recommend_0_10",
            "responses": [
                {"response_id": str(i), "score": score}
                for i, score in enumerate([10, 9, 8, 7, 6, None])
            ],
            "survey_id": "owned-survey",
            "sampling_frame": "engineering fixture respondents",
            "observation_window": "2026-10",
        }
        purpose, expected = "measure_recommendation", 20
        from canonical_metrics import recommendation_score

        with pytest.raises(ValueError, match="SURVEY_REQUIRED"):
            recommendation_score({**data, "question_type": "sentiment_labels"})
        with pytest.raises(ValueError, match="RESPONSE_INVALID"):
            recommendation_score({**data, "responses": [data["responses"][0]] * 2})
        missing = recommendation_score(
            {**data, "responses": [{"response_id": "x", "score": None}]}
        )
        assert missing["state"] == "NO_DATA" and missing["value"] is None
    else:
        data = {
            "numerator": 20,
            "market_total": 100,
            "sales_basis": "revenue",
            "currency": "USD",
            "period_start": "2026-01-01",
            "period_end": "2026-03-31",
            "entity": "owned brand",
            "geography": "declared region",
            "category": "comparable product",
            "market_definition": "inclusive total of declared market",
            "data_basis": "user_supplied_sales",
        }
        purpose, expected = "compare_sales_share", 0.2
        from canonical_metrics import sales_market_share

        with pytest.raises(ValueError, match="USER_SALES_REQUIRED"):
            sales_market_share({**data, "data_basis": "social_mentions"})
        with pytest.raises(ValueError, match="SALES_INVALID"):
            sales_market_share({**data, "numerator": 101})
        with pytest.raises(ValueError, match="CURRENCY_REQUIRED"):
            sales_market_share({**data, "currency": None})
        assert (
            sales_market_share({**data, "numerator": 0, "market_total": 0})["value"]
            is None
        )
    source = _source(workspace, data, analysis=None)
    result = brief.analyze_statistics_source(
        source["evidence_id"],
        business_purpose=purpose,
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    assert result["result"]["value"] == expected
    if analysis == "nps":
        assert result["result"]["n"] == 5 and result["result"]["missing_n"] == 1
        assert result["result"]["counts"]["passives"] == 2
        assert (
            result["result"]["interval"][0]
            <= expected
            <= result["result"]["interval"][1]
        )
    else:
        assert result["result"]["interval"] is None
    saved = workspace["work"].save_work(
        **result["saved_work_draft"],
        request_id="statistics-" + analysis,
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    reopened = workspace["work"].reopen_work(
        saved["artifact"]["artifact_id"],
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    assert reopened["document"]["payload"]["statistics"]["result"] == result["result"]


def test_same_version_embedding_distance_source_roundtrip(workspace, monkeypatch):
    monkeypatch.setattr(brief, "get_repository", lambda: workspace["repo"])
    model = {
        "model_id": "owned-engineering-vector-fixture",
        "version": "1",
        "preprocessing_id": "identity-2d",
    }
    block = {
        "current_model": model,
        "historical_model": model,
        "current": [
            {"id": "same", "vector": [2, 0]},
            {"id": "orthogonal", "vector": [0, 1]},
            {"id": "opposite", "vector": [-1, 0]},
        ],
        "historical": [{"id": "history", "vector": [1, 0]}],
    }
    source = _source(workspace, {"embeddings": block}, analysis=None)
    result = brief.analyze_statistics_source(
        source["evidence_id"],
        business_purpose="measure_information_change",
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    assert [
        row["distance"] for row in result["result"]["embedding_distance"]["nearest"]
    ] == pytest.approx([0, 1, 2])
    with pytest.raises(ValueError, match="MODEL_MISMATCH"):
        brief._statistics_novelty(
            {"embeddings": {**block, "historical_model": {**model, "version": "2"}}}
        )
    with pytest.raises(ValueError, match="ZERO_NORM"):
        brief._statistics_novelty(
            {"embeddings": {**block, "current": [{"id": "zero", "vector": [0, 0]}]}}
        )
    with pytest.raises(ValueError, match="PARTITION_OVERLAP"):
        brief._statistics_novelty(
            {"embeddings": {**block, "current": block["historical"]}}
        )
    assert (
        brief._statistics_novelty({"embeddings": {**block, "historical": []}})["state"]
        == "NO_DATA"
    )
    saved = workspace["work"].save_work(
        **result["saved_work_draft"],
        request_id="statistics-embeddings",
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    reopened = workspace["work"].reopen_work(
        saved["artifact"]["artifact_id"],
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    assert reopened["document"]["payload"]["statistics"]["result"] == result["result"]


def _synthetic_control_fixture():
    from datetime import date, timedelta

    n, pre = 30, 24
    donors = [
        [100 + 0.2 * t + math.sin(0.3 * t) for t in range(n)],
        [105 - 0.1 * t + math.cos(0.7 * t) for t in range(n)],
        [98 + 0.3 * t + math.sin(0.8 * t) for t in range(n)],
    ]
    return {
        "periods": [
            (date(2026, 1, 1) + timedelta(days=t)).isoformat() for t in range(n)
        ],
        "frequency": "day",
        "treated": {
            "id": "treated",
            "outcomes": [
                sum(w * donors[j][t] for j, w in enumerate([0.2, 0.3, 0.5]))
                + (2 if t >= pre else 0)
                for t in range(n)
            ],
        },
        "donors": [
            {"id": "donor" + str(j), "outcomes": series, "untreated_declared": True}
            for j, series in enumerate(donors)
        ],
        "pre_periods": pre,
        "max_pre_rmse": 0.01,
        "design": {
            "no_anticipation": True,
            "no_spillovers": True,
            "comparable_measurement": True,
            "selection_protocol": "Owned known-mixture engineering fixture fixed before outcome inspection",
        },
    }


def test_synthetic_control_known_weights_holdout_and_source_save(
    workspace, monkeypatch
):
    import copy

    monkeypatch.setattr(brief, "get_repository", lambda: workspace["repo"])
    data = _synthetic_control_fixture()
    source = _source(workspace, data, analysis=None)
    result = brief.analyze_statistics_source(
        source["evidence_id"],
        business_purpose="compare_with_synthetic_baseline",
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    actual = result["result"]
    assert actual["state"] == "READY"
    assert list(actual["donor_weights"].values()) == pytest.approx(
        [0.2, 0.3, 0.5], abs=1e-5
    )
    assert actual["fit"]["mean_post_gap"] == pytest.approx(2, abs=1e-5)
    assert actual["fit"]["validation_n"] == 6
    assert actual["fit"]["validation_rmse"] < 1e-5
    assert actual["placebo_comparison"]["p_value"] is None
    changed = copy.deepcopy(data)
    changed["treated"]["outcomes"][24:] = [
        v + 200 for v in changed["treated"]["outcomes"][24:]
    ]
    assert brief._statistics_synthetic_control(changed)[
        "donor_weights"
    ] == pytest.approx(actual["donor_weights"])
    changed = copy.deepcopy(data)
    changed["treated"]["outcomes"][18:24] = [
        v + 5 for v in changed["treated"]["outcomes"][18:24]
    ]
    assert (
        brief._statistics_synthetic_control(changed)["reason"]
        == "PRE_FIT_OR_HOLDOUT_ERROR_EXCEEDS_DECLARED_TOLERANCE"
    )
    changed = copy.deepcopy(data)
    changed["donors"][1]["outcomes"] = changed["donors"][0]["outcomes"]
    assert (
        brief._statistics_synthetic_control(changed)["reason"]
        == "DONOR_WEIGHTS_NOT_IDENTIFIABLE"
    )
    changed = copy.deepcopy(data)
    changed["design"]["no_spillovers"] = False
    assert (
        brief._statistics_synthetic_control(changed)["reason"]
        == "DECLARED_DESIGN_ASSUMPTIONS_NOT_MET"
    )
    saved = workspace["work"].save_work(
        **result["saved_work_draft"],
        request_id="statistics-synthetic-control",
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    reopened = workspace["work"].reopen_work(
        saved["artifact"]["artifact_id"],
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    assert reopened["document"]["payload"]["statistics"]["result"] == actual
    _save_engineering_receipt("synthetic_control_saved_result", source, result, saved)


def _schedule_fixture():
    return {
        "tasks": [
            {
                "id": "A",
                "cost_minor": 4,
                "benefit": 8,
                "duration": 2,
                "earliest_start": 0,
                "latest_end": 4,
                "resources": ["creator"],
                "coverage": ["x"],
            },
            {
                "id": "B",
                "cost_minor": 4,
                "benefit": 7,
                "duration": 2,
                "earliest_start": 0,
                "latest_end": 4,
                "resources": ["creator"],
                "coverage": ["y"],
            },
            {
                "id": "C",
                "cost_minor": 6,
                "benefit": 12,
                "duration": 3,
                "earliest_start": 0,
                "latest_end": 4,
                "resources": ["creator"],
                "coverage": ["x", "y"],
            },
        ],
        "resource_ids": ["creator"],
        "budget_minor": 8,
        "currency": "USD",
        "benefit_unit": "user judgment points",
        "start_at": "2026-10-17T00:00:00+00:00",
        "slot_minutes": 60,
        "horizon": 4,
        "required_coverage": ["x", "y"],
        "mandatory_tasks": [],
        "prerequisites": [["A", "B"]],
        "exclusions": [],
    }


def test_ortools_schedule_matches_exhaustive_known_optimum_and_saved_source(
    workspace, monkeypatch
):
    import copy
    import itertools

    monkeypatch.setattr(brief, "get_repository", lambda: workspace["repo"])
    data = _schedule_fixture()
    # Independent enumeration of every subset and integer start time in this fixture.
    feasible_values = []
    for selected in itertools.product([False, True], repeat=3):
        rows = [r for r, on in zip(data["tasks"], selected) if on]
        ids = {r["id"] for r in rows}
        if sum(r["cost_minor"] for r in rows) > 8 or not {"x", "y"} <= {
            c for r in rows for c in r["coverage"]
        }:
            continue
        if "B" in ids and "A" not in ids:
            continue
        for starts in itertools.product(*(range(5 - r["duration"]) for r in rows)):
            spans = {r["id"]: (s, s + r["duration"]) for r, s in zip(rows, starts)}
            if any(
                max(a[0], b[0]) < min(a[1], b[1])
                for a, b in itertools.combinations(spans.values(), 2)
            ):
                continue
            if "B" in spans and spans["A"][1] > spans["B"][0]:
                continue
            feasible_values.append(sum(r["benefit"] for r in rows))
    source = _source(workspace, data, analysis=None)
    result = brief.analyze_statistics_source(
        source["evidence_id"],
        business_purpose="plan_budgeted_schedule",
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    actual = result["result"]
    assert actual["state"] == "READY" and actual["solver"]["status"] == "OPTIMAL"
    assert actual["objective"] == max(feasible_values) == 15
    assert [r["id"] for r in actual["schedule"]] == ["A", "B"]
    assert actual["schedule"][0]["end_slot"] <= actual["schedule"][1]["start_slot"]
    changed = copy.deepcopy(data)
    changed.update(budget_minor=10, mandatory_tasks=["A", "C"])
    assert (
        brief._statistics_schedule(changed)["reason"]
        == "DECLARED_SCHEDULE_CONSTRAINTS_INFEASIBLE"
    )
    changed = copy.deepcopy(data)
    changed["exclusions"] = [["A", "B"]]
    assert brief._statistics_schedule(changed)["objective"] == 12
    changed = copy.deepcopy(data)
    changed["tasks"][0]["cost_minor"] = 1.5
    with pytest.raises(ValueError, match="INTEGER_INVALID"):
        brief._statistics_schedule(changed)
    saved = workspace["work"].save_work(
        **result["saved_work_draft"],
        request_id="statistics-schedule",
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    reopened = workspace["work"].reopen_work(
        saved["artifact"]["artifact_id"],
        actor=workspace["actor"],
        scope=workspace["scope"],
    )
    assert reopened["document"]["payload"]["statistics"]["result"] == actual
    _save_engineering_receipt("schedule_saved_result", source, result, saved)


def test_entity_candidate_identity_source_custody_and_saved_review(
    workspace, monkeypatch
):
    import copy

    monkeypatch.setattr(brief, "get_repository", lambda: workspace["repo"])
    reference = _source(
        workspace,
        {"left": "Brand A", "right": "Brand B"},
        analysis="identity-reference",
    )
    raw = (workspace["root"] / "identity-reference.txt").read_text()
    pair = {}
    for side, label in (("left", "Brand A"), ("right", "Brand B")):
        start = raw.index(label)
        pair[side] = {
            "label": label,
            "registry_subject_id": None,
            "source_evidence_id": reference["evidence_id"],
            "start": start,
            "end": start + len(label),
            "quote": label,
        }
    rows = [
        {
            "id": str(i),
            "partition": "train" if i < 40 else "test",
            "agreements": [bool(i % 2), bool(i % 2)],
            "label": i % 2,
        }
        for i in range(80)
    ]
    rows.append(
        {
            "id": "comparison-pair-1",
            "partition": "candidate",
            "agreements": [True, False],
            "label": None,
            "identity_pair": pair,
        }
    )
    source = _source(workspace, {"rows": rows}, analysis="entity_matching")
    kwargs = {"actor": workspace["actor"], "scope": workspace["scope"]}
    result = brief.analyze_statistics_source(source["evidence_id"], **kwargs)
    candidate = result["result"]["candidates"][0]
    assert (
        candidate["source_binding_state"]
        == "SOURCE_QUOTES_VERIFIED_NOT_IDENTITY_CONFIRMED"
    )
    assert candidate["registry_identity_state"] == "REQUIRES_SEPARATE_REGISTRY_REVIEW"
    assert candidate["recommendation"] == "MANUAL_REVIEW"
    assert len(result["saved_work_draft"]["citations"]) == 3
    saved = workspace["work"].save_work(
        **result["saved_work_draft"], request_id="statistics-identity-review", **kwargs
    )
    reopened = workspace["work"].reopen_work(saved["artifact"]["artifact_id"], **kwargs)
    assert (
        reopened["document"]["payload"]["statistics"]["result"]["candidates"][0]
        == candidate
    )
    _save_engineering_receipt("identity_candidate_saved_result", source, result, saved)
    changed = copy.deepcopy(rows)
    changed[-1]["identity_pair"]["left"].update(label="Brand X", quote="Brand X")
    invalid = _source(workspace, {"rows": changed}, analysis="entity_matching")
    with pytest.raises(ValueError, match="QUOTE_MISMATCH"):
        brief.analyze_statistics_source(invalid["evidence_id"], **kwargs)
    with workspace["repo"].transaction() as con:
        con.execute(
            "UPDATE app_evidence_records SET content_hash=? WHERE id=?",
            ("0" * 64, reference["evidence_id"]),
        )
    with pytest.raises(ValueError, match="INTEGRITY|CONTEXT"):
        workspace["work"].reopen_work(saved["artifact"]["artifact_id"], **kwargs)


def test_basic_statistics_without_scientific_dependencies_or_metadata(
    workspace, monkeypatch
):
    import builtins
    import importlib.metadata
    import importlib.util

    monkeypatch.setattr(brief, "get_repository", lambda: workspace["repo"])
    source = _source(workspace, {"successes": 37, "trials": 100})
    network = _source(
        workspace,
        {
            "nodes": ["A", "B"],
            "edges": [{"source": "A", "target": "B", "relation": "mention"}],
        },
        analysis="network",
    )
    original_import, original_spec, original_version = (
        builtins.__import__,
        importlib.util.find_spec,
        importlib.metadata.version,
    )

    def no_scientific_import(name, *args, **kwargs):
        if name.split(".")[0] in {"numpy", "scipy"}:
            raise ModuleNotFoundError(name)
        return original_import(name, *args, **kwargs)

    def no_scientific_spec(name, *args, **kwargs):
        return (
            None if name in {"numpy", "scipy"} else original_spec(name, *args, **kwargs)
        )

    def no_scientific_metadata(name):
        if name in {"numpy", "scipy"}:
            raise importlib.metadata.PackageNotFoundError(name)
        return original_version(name)

    monkeypatch.setattr(builtins, "__import__", no_scientific_import)
    monkeypatch.setattr(importlib.util, "find_spec", no_scientific_spec)
    monkeypatch.setattr(importlib.metadata, "version", no_scientific_metadata)
    kwargs = {"actor": workspace["actor"], "scope": workspace["scope"]}
    result = brief.analyze_statistics_source(source["evidence_id"], **kwargs)
    assert result["state"] == "READY" and result["result"]["value"] == 0.37
    assert result["result"]["implementation_versions"] == {
        "numpy": "UNKNOWN",
        "scipy": "UNKNOWN",
    }
    missing = brief.analyze_statistics_source(network["evidence_id"], **kwargs)
    assert missing["state"] == "UNAVAILABLE"
    assert missing["result"]["missing_dependencies"] == ["numpy", "scipy"]
    assert missing["result"]["n"] is None


def test_macro_controls_original_source_missing_quarter_save(workspace, monkeypatch):
    from lumenis.importer import macro
    from tests.test_public_macro_pipeline import TEXT, URL

    w = workspace
    monkeypatch.setattr(brief, "get_repository", lambda: w["repo"])
    monkeypatch.setattr(macro, "get_repository", lambda: w["repo"])
    path = w["root"] / "owned-macro.txt"
    path.write_text(TEXT)
    args = dict(actor=w["actor"], scope=w["scope"], provenance={
        "source_url": URL, "captured_at": "2025-04-20T00:00:00Z",
        "published_at": None, "rights": "owner-approved",
        "title": "Owned synthetic macro source; not real release acquisition",
        "content_origin": {"kind": "self-authored", "claim_type": "synthetic_sample"},
    })
    resource = w["documents"].document_import_resource(str(path), **args)
    w["gate"].grant_approval(permission.OperationType.DATA_IMPORT.value, resource=resource, granted_by="isolated-test")
    macro_source = w["documents"].import_document(str(path), **args)
    data = {
        "periods": [{"period": p, "outcome": 100, "spend": {"owned": 10}}
                    for p in ("2025-Q1", "2025-Q2")],
        "currency": "CNY", "outcome_unit": "trial", "filing_entity": "Owned national fixture",
        "disclosure_scope": "group", "spend_basis": "user_declared", "region": "CN-national",
        "macro_controls": [{"evidence_ids": [macro_source["evidence_id"]], "selection": {
            "region": "CN-national", "metric": "retail_sales", "periods": ["2025-Q1", "2025-Q2"],
            "as_of": "2025-05-01T00:00:00Z"}}],
    }
    source = _source(w, data, "mmm")
    result = brief.analyze_statistics_source(source["evidence_id"], actor=w["actor"], scope=w["scope"])
    assert result["result"]["reason"] == "MACRO_CONTROL_QUARTERS_UNAVAILABLE"
    assert len(result["saved_work_draft"]["citations"]) == 2
    control = result["result"]["macro_controls"][0]
    assert control["periods"][0]["value"] == "12467100000000.0"
    assert control["periods"][1]["value"] is None
    saved = w["work"].save_work(**result["saved_work_draft"], actor=w["actor"], scope=w["scope"], request_id="macro-mmm-owned-1")
    reopened = w["work"].reopen_work(saved["artifact"]["artifact_id"], actor=w["actor"], scope=w["scope"])
    assert reopened["document"]["payload"]["statistics"]["result"] == result["result"]
    data["macro_controls"][0]["selection"]["region"] = "CN-Shanghai"
    with pytest.raises(ValueError, match="CONTROL_ALIGNMENT"):
        source = _source(w, data, "mmm")
        brief.analyze_statistics_source(source["evidence_id"], actor=w["actor"], scope=w["scope"])


def test_mmm_rejects_unresolved_or_forged_internal_controls(workspace, monkeypatch):
    monkeypatch.setattr(brief, "get_repository", lambda: workspace["repo"])
    data = {"periods": [], "currency": "CNY", "outcome_unit": "trial",
            "filing_entity": "Owned fixture", "disclosure_scope": "group",
            "spend_basis": "user_declared", "macro_controls": []}
    with pytest.raises(ValueError, match="CONTROLS_REQUIRE_SOURCE_OWNER"):
        brief._statistics_mmm(data)
    data.pop("macro_controls")
    data["_resolved_macro_controls"] = []
    source = _source(workspace, data, "mmm")
    with pytest.raises(ValueError, match="INTERNAL_CONTROL_INPUT_FORBIDDEN"):
        brief.analyze_statistics_source(source["evidence_id"], actor=workspace["actor"], scope=workspace["scope"])


def test_mmm_actual_cpu_macro_control_posterior_and_training_scaling(workspace, monkeypatch):
    """Owned numeric experiment; real NBS matching observations remain insufficient."""
    import numpy as np
    from pathlib import Path

    monkeypatch.setenv("PYTENSOR_FLAGS", "base_compiledir=" + str(workspace["root"] / "macro-pytensor"))
    rng = np.random.default_rng(1701)
    n = 48
    x = rng.uniform(20, 180, n)
    z = rng.normal(2, 0.7, n)
    weights = 0.3 ** np.arange(8)
    carry = np.array([sum(weights[j] * x[i-j] for j in range(min(i+1, 8))) / weights.sum() for i in range(n)])
    y = 100 + 70 * carry / (80 + carry) + 6 * z + 4 * np.sin(2 * np.pi * np.arange(n) / 4) + rng.normal(0, 2, n)
    periods = [f"{2010+i//4}-Q{i%4+1}" for i in range(n)]
    control = {"state": "AVAILABLE", "region": "CN-national", "metric": "cpi_yoy_percent",
               "unit": "percent_yoy", "as_of": "2026-10-17T00:00:00Z",
               "vintage_basis": "owned numerical engineering fixture, not official macro observations",
               "periods": [{"period": p, "value": str(z[i]), "state": "AVAILABLE",
                            "aggregation": "arithmetic-mean-monthly-yoy-percent"} for i,p in enumerate(periods)]}
    data = {"periods": [{"period": p, "outcome": float(y[i]), "spend": {"owned": float(x[i])}} for i,p in enumerate(periods)],
            "currency": "CNY", "outcome_unit": "synthetic sales", "filing_entity": "Owned national simulation",
            "disclosure_scope": "group", "spend_basis": "user_declared", "region": "CN-national",
            "_resolved_macro_controls": [control]}
    result = brief._statistics_mmm(data)
    assert result["state"] == "READY", result.get("reason")
    assert result["control_scaling"]["means"] == pytest.approx([z[:39].mean()])
    assert result["control_scaling"]["standard_deviations"] == pytest.approx([z[:39].std()])
    low, median, high = result["macro_control_coefficients"][0]["posterior_interval_95_and_median"]
    assert low < 6 < high
    assert median == pytest.approx(6, abs=2)
    destination = workspace["root"] / "mmm_macro_cpu_result.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2))


@pytest.mark.parametrize('metric,unit', [('domestic_tourism_trips','person_trips'), ('domestic_tourism_spend','CNY')])
def test_tourism_control_exact_quarter_whitelist_and_holiday_refusal(metric, unit):
    periods = [{"period": f"{2020+i//4}-Q{i%4+1}", "outcome": 100+i,
                "spend": {"owned": 10+i%3}} for i in range(16)]
    control = {"state":"AVAILABLE", "metric":metric, "unit":unit, "region":"CN-national",
               "as_of":"2026-10-17T00:00:00Z", "periods":[{
                   "period":row["period"], "value":str(100+i*i), "state":"AVAILABLE",
                   "aggregation":"holiday-total"} for i,row in enumerate(periods)]}
    data = {"periods": periods, "currency":"CNY", "outcome_unit":"trial", "filing_entity":"Owned national fixture",
            "disclosure_scope":"group", "spend_basis":"user_declared", "region":"CN-national",
            "_resolved_macro_controls":[control]}
    with pytest.raises(ValueError, match="CONTROL_AGGREGATION_INVALID"):
        brief._statistics_mmm(data)
    data['periods'] = periods[:1]
    control['periods'] = control['periods'][:1]
    control['periods'][0]['aggregation'] = 'explicit-reported-quarter-total'
    assert brief._statistics_mmm(data)['reason'] == 'NEED_AT_LEAST_12_REAL_QUARTERS'
    control['state'] = 'INSUFFICIENT'
    control['periods'][0].update(value=None, state='MISSING', reason='HOLIDAY_TOTAL_NOT_QUARTER')
    assert brief._statistics_mmm(data)['reason'] == 'MACRO_CONTROL_QUARTERS_UNAVAILABLE'


@pytest.mark.parametrize('metadata,reason', [
    ({'observation_frequency':'annual','original_observation_count':4}, 'RESAMPLED_PERIODS_NOT_INDEPENDENT'),
    ({'observation_frequency':'monthly'}, 'SOURCE_FREQUENCY_REQUIRES_VERIFIED_QUARTER_AGGREGATION'),
    ({'transformation':'interpolate'}, 'PERIOD_CONSTRUCTION_NOT_VERIFIED'),
    ({'transformation':'arbitrary-unverified-method'}, 'PERIOD_CONSTRUCTION_NOT_VERIFIED'),
    ({'original_observation_count':48}, 'ORIGINAL_OBSERVATION_COUNT_MISMATCH'),
])
def test_mmm_explicit_source_granularity_precedes_model(metadata,reason,monkeypatch):
    import builtins
    original=builtins.__import__
    def guarded(name,*args,**kwargs):
        if name=='pymc':raise AssertionError('No model permitted in granularity gate test')
        return original(name,*args,**kwargs)
    monkeypatch.setattr(builtins,'__import__',guarded)
    data={'periods':[{'period':f'{2020+i//4}-Q{i%4+1}','outcome':100+i,'spend':{'owned':10+i}} for i in range(16)],
          'currency':'USD','outcome_unit':'trial','filing_entity':'Engineering fixture',
          'disclosure_scope':'group','spend_basis':'user_declared',**metadata}
    r=brief._statistics_mmm(data)
    assert r['state']=='INSUFFICIENT' and r['reason']==reason
    assert r['verified_independent_observation_count'] is None
    assert r['roi_state']=='NOT_ESTABLISHED'


@pytest.mark.parametrize('metadata', [{}, {'observation_frequency':'quarter','original_observation_count':16,'transformation':'reported'}])
def test_mmm_declared_quarter_gate_preserves_original_path_without_claiming_verified_samples(metadata):
    # Constant channel stops before sampling; this checks admission, not fit quality.
    data={'periods':[{'period':f'{2020+i//4}-Q{i%4+1}','outcome':100+i,'spend':{'owned':10}} for i in range(16)],
          'currency':'USD','outcome_unit':'trial','filing_entity':'Engineering fixture',
          'disclosure_scope':'group','spend_basis':'user_declared',**metadata}
    r=brief._statistics_mmm(data)
    assert r['reason']=='NO_TRAINING_CHANNEL_OR_OUTCOME_VARIATION'
    assert r['declared_period_count']==16
    assert r['observation_frequency_verification']=='NOT_INDEPENDENTLY_VERIFIED'
    assert r['verified_independent_observation_count'] is None


def test_mmm_unrecognized_metadata_is_not_silently_discarded():
    with pytest.raises(ValueError,match='UNSUPPORTED_DATA_FIELDS'):
        brief._statistics_mmm({'source_frequency':'annual'})
