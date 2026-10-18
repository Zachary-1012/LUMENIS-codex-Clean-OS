"""Internal pure numerical methods of the existing Reporting owner.

No data acquisition, permissions, identity writes or persistence live here.
READY means bounded computation succeeded, not business or causal validation.
"""

from __future__ import annotations


def _statistics_numbers(values, *, minimum=0, maximum=10000):
    import math

    if (
        not isinstance(values, list)
        or not minimum <= len(values) <= maximum
        or any(
            type(x) not in (int, float) or not math.isfinite(x) or abs(x) > 1e12
            for x in values
        )
    ):
        raise ValueError("STATISTICS_NUMERIC_INPUT_INVALID")
    return values


def _statistics_network(data):
    """G148 observed directed relation graph, no inferred edges or follower proxy."""
    import networkx as nx

    nodes, edges = data.get("nodes"), data.get("edges")
    if (
        not isinstance(nodes, list)
        or not 1 <= len(nodes) <= 500
        or any(not isinstance(n, str) or not n.strip() for n in nodes)
        or len(set(nodes)) != len(nodes)
        or not isinstance(edges, list)
        or len(edges) > 5000
    ):
        raise ValueError("STATISTICS_NETWORK_INVALID")
    graph = nx.DiGraph()
    graph.add_nodes_from(nodes)
    for e in edges:
        if (
            not isinstance(e, dict)
            or set(e) != {"source", "target", "relation"}
            or not isinstance(e["source"], str)
            or not isinstance(e["target"], str)
            or not isinstance(e["relation"], str)
            or e["source"] not in graph
            or e["target"] not in graph
            or e["source"] == e["target"]
            or e["relation"] not in {"repost", "mention", "collaboration"}
        ):
            raise ValueError("STATISTICS_NETWORK_EDGE_INVALID")
        graph.add_edge(e["source"], e["target"])
    result = {
        "method": "observed-network@1",
        "state": "READY" if edges else "NO_DATA",
        "n": len(nodes),
        "edge_n": graph.number_of_edges(),
        "unit": "dimensionless centrality",
        "limitations": [
            "Only supplied observed edges; follower counts and inferred temporal links are excluded.",
            "Centrality is structural, not causal influence or population reach.",
        ],
    }
    if not edges:
        return result
    rank = nx.pagerank(graph, alpha=0.85, tol=1e-12, max_iter=1000)
    bridge = nx.betweenness_centrality(graph, normalized=True)
    result["nodes"] = [
        {"id": n, "pagerank": rank[n], "betweenness": bridge[n]} for n in nodes
    ]
    result["hits"] = {
        "state": "INSUFFICIENT",
        "reason": "DOMINANT_SINGULAR_VECTOR_MAY_BE_NONUNIQUE",
    }
    # HITS can be non-identifiable on repeated top singular values; report only a unique mode.
    import numpy as np

    adjacency = nx.to_numpy_array(graph, nodelist=nodes)
    u, s, vh = np.linalg.svd(adjacency)
    if len(s) == 1 or s[0] - s[1] > 1e-10 * max(1, s[0]):
        hubs, authorities = np.abs(u[:, 0]), np.abs(vh[0, :])
        result["hits"] = {
            "state": "READY",
            "hubs": dict(zip(nodes, (hubs / hubs.sum()).tolist())),
            "authorities": dict(zip(nodes, (authorities / authorities.sum()).tolist())),
        }
    return result


def _statistics_decision(data):
    """G157 explicit reciprocal AHP and vector-normalized TOPSIS, no guessed weights."""
    import numpy as np

    alternatives, matrix, pairwise, benefit = (
        data.get(k) for k in ("alternatives", "matrix", "pairwise", "benefit")
    )
    if (
        not isinstance(alternatives, list)
        or not 2 <= len(alternatives) <= 500
        or any(not isinstance(a, str) or not a.strip() for a in alternatives)
        or len(set(alternatives)) != len(alternatives)
        or not isinstance(benefit, list)
        or not 2 <= len(benefit) <= 10
        or any(type(x) is not bool for x in benefit)
    ):
        raise ValueError("STATISTICS_DECISION_INVALID")
    m = len(benefit)
    if (
        not isinstance(matrix, list)
        or len(matrix) != len(alternatives)
        or not isinstance(pairwise, list)
        or len(pairwise) != m
    ):
        raise ValueError("STATISTICS_DECISION_MATRIX_INVALID")
    for row in matrix:
        _statistics_numbers(row, minimum=m, maximum=m)
    for row in pairwise:
        _statistics_numbers(row, minimum=m, maximum=m)
    x, a = np.array(matrix, float), np.array(pairwise, float)
    if (
        np.any(a <= 0)
        or np.any(a > 9)
        or np.any(a < 1 / 9)
        or not np.allclose(np.diag(a), 1, rtol=0, atol=1e-8)
        or not np.allclose(a * a.T, 1, rtol=0, atol=1e-8)
        or np.any(x < 0)
    ):
        raise ValueError("STATISTICS_AHP_RECIPROCITY_REQUIRED")
    eig, vectors = np.linalg.eig(a)
    index = np.argmax(eig.real)
    weights = np.abs(vectors[:, index].real)
    weights /= weights.sum()
    ri = {
        2: 0,
        3: 0.58,
        4: 0.90,
        5: 1.12,
        6: 1.24,
        7: 1.32,
        8: 1.41,
        9: 1.45,
        10: 1.49,
    }[m]
    cr = max(0, float((eig[index].real - m) / (m - 1) / ri)) if ri else 0.0
    result = {
        "method": "ahp-topsis@1",
        "n": len(alternatives),
        "unit": "relative decision preference",
        "state": "READY" if cr < 0.1 else "INSUFFICIENT",
        "consistency_ratio": cr,
        "weights": weights.tolist(),
        "limitations": [
            "User judgments and included alternatives determine the ranking.",
            "Preference scores are not success probabilities.",
        ],
    }
    if cr >= 0.1:
        return {**result, "reason": "AHP_INCONSISTENT_JUDGMENTS"}
    norms = np.linalg.norm(x, axis=0)
    if np.any(norms == 0):
        return {**result, "state": "INSUFFICIENT", "reason": "ZERO_NORM_CRITERION"}

    def score(w):
        v = x / norms * w
        best = np.where(benefit, v.max(axis=0), v.min(axis=0))
        worst = np.where(benefit, v.min(axis=0), v.max(axis=0))
        dplus, dminus = np.linalg.norm(v - best, axis=1), np.linalg.norm(
            v - worst, axis=1
        )
        return np.divide(
            dminus, dplus + dminus, out=np.full(len(x), 0.5), where=dplus + dminus > 0
        )

    scores = score(weights)
    sensitivity = []
    for j in range(m):
        for factor in (0.8, 1.2):
            changed = weights.copy()
            changed[j] *= factor
            changed /= changed.sum()
            sensitivity.append(
                {
                    "criterion": j,
                    "multiplier": factor,
                    "scores": score(changed).tolist(),
                }
            )
    result.update(
        scores=[
            {"id": name, "score": float(value)}
            for name, value in zip(alternatives, scores)
        ],
        ranking=[alternatives[i] for i in np.argsort(-scores, kind="stable")],
        sensitivity=sensitivity,
    )
    return result


def _statistics_portfolio(data):
    """G158 actual binary MILP under explicit additive benefit/budget/coverage constraints."""
    import numpy as np
    from scipy.optimize import milp, Bounds, LinearConstraint

    items, budget, required = (
        data.get("items"),
        data.get("budget"),
        data.get("required_coverage", []),
    )
    if (
        not isinstance(items, list)
        or not 1 <= len(items) <= 300
        or not isinstance(required, list)
        or len(required) > 100
    ):
        raise ValueError("STATISTICS_PORTFOLIO_INVALID")
    _statistics_numbers([budget], minimum=1)
    if (
        budget < 0
        or any(not isinstance(r, str) or not r.strip() for r in required)
        or len(set(required)) != len(required)
    ):
        raise ValueError("STATISTICS_PORTFOLIO_INVALID")
    ids, costs, benefits, coverage = [], [], [], []
    for item in items:
        if not isinstance(item, dict) or set(item) != {
            "id",
            "cost",
            "benefit",
            "coverage",
        }:
            raise ValueError("STATISTICS_PORTFOLIO_ITEM_INVALID")
        _statistics_numbers([item["cost"], item["benefit"]], minimum=2)
        if (
            not isinstance(item["id"], str)
            or not item["id"].strip()
            or item["cost"] < 0
            or not isinstance(item["coverage"], list)
            or any(not isinstance(c, str) for c in item["coverage"])
        ):
            raise ValueError("STATISTICS_PORTFOLIO_ITEM_INVALID")
        ids.append(item["id"])
        costs.append(item["cost"])
        benefits.append(item["benefit"])
        coverage.append(item["coverage"])
    if len(set(ids)) != len(ids):
        raise ValueError("STATISTICS_PORTFOLIO_DUPLICATE_ID")
    a = [costs] + [[int(r in c) for c in coverage] for r in required]
    fit = milp(
        -np.array(benefits),
        integrality=np.ones(len(items)),
        bounds=Bounds(0, 1),
        constraints=LinearConstraint(
            np.array(a),
            [-np.inf] + [1] * len(required),
            [budget] + [np.inf] * len(required),
        ),
        options={"time_limit": 5, "mip_rel_gap": 0.0},
    )
    result = {
        "method": "scipy-highs-binary-milp@1",
        "state": "READY" if fit.success else "INSUFFICIENT",
        "n": len(items),
        "unit": data.get("unit"),
        "solver_status": int(fit.status),
        "budget": budget,
        "limitations": [
            "Additive supplied benefits are assumptions, not causal ROI.",
            "Coverage labels are declared constraints, not representative population reach.",
        ],
    }
    if not fit.success:
        return {
            **result,
            "reason": "INFEASIBLE" if fit.status == 2 else "OPTIMALITY_NOT_ESTABLISHED",
        }
    chosen = np.rint(fit.x).astype(int)
    if (
        not np.all((chosen == 0) | (chosen == 1))
        or np.dot(chosen, costs) > budget + 1e-7
        or any(
            sum(chosen[i] for i, c in enumerate(coverage) if r in c) < 1
            for r in required
        )
    ):
        raise RuntimeError("STATISTICS_OPTIMIZER_VERIFICATION_FAILED")
    result.update(
        selected=[ids[i] for i, v in enumerate(chosen) if v],
        cost=float(np.dot(chosen, costs)),
        benefit=float(np.dot(chosen, benefits)),
        mip_gap=float(fit.mip_gap),
    )
    return result


def _statistics_calibration(data):
    """G150 held-out calibration; reject known overlap without claiming unknown lineage."""
    import numpy as np
    from sklearn.isotonic import IsotonicRegression

    if not isinstance(data, dict) or set(data) - {"rows", "model_provenance"}:
        raise ValueError("STATISTICS_CALIBRATION_INVALID")
    rows = data.get("rows")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 10000:
        raise ValueError("STATISTICS_CALIBRATION_INVALID")
    ids = set()
    parts = {"calibration": [], "test": []}
    for row in rows:
        if (
            not isinstance(row, dict)
            or set(row) != {"id", "partition", "score", "label"}
            or not isinstance(row["id"], str)
            or not row["id"]
            or row["id"] in ids
            or not isinstance(row["partition"], str)
            or row["partition"] not in parts
            or type(row["label"]) is not int
            or row["label"] not in (0, 1)
        ):
            raise ValueError("STATISTICS_CALIBRATION_PARTITION_INVALID")
        _statistics_numbers([row["score"]], minimum=1)
        if not 0 <= row["score"] <= 1:
            raise ValueError("STATISTICS_CALIBRATION_SCORE_INVALID")
        ids.add(row["id"])
        parts[row["partition"]].append(row)
    # This manifest can disprove declared split integrity; it cannot prove that
    # a model really trained on only those rows, or that labels are measured truth.
    provenance = data.get("model_provenance")
    lineage_state = "NOT_PROVIDED"
    if provenance is not None:
        required = {"model_id", "model_version", "training_ids",
                    "calibration_model_version", "test_model_version", "population"}
        if (not isinstance(provenance, dict) or set(provenance) != required
                or any(not isinstance(provenance[k], str) or not provenance[k].strip()
                       for k in required - {"training_ids"})
                or not isinstance(provenance["training_ids"], list)
                or not 1 <= len(provenance["training_ids"]) <= 100000
                or any(not isinstance(v, str) or not v.strip() for v in provenance["training_ids"])):
            raise ValueError("STATISTICS_CALIBRATION_PROVENANCE_INVALID")
        training_ids = provenance["training_ids"]
        if len(set(training_ids)) != len(training_ids) or ids.intersection(training_ids):
            raise ValueError("STATISTICS_CALIBRATION_TRAINING_LEAKAGE")
        if not (provenance["model_version"] == provenance["calibration_model_version"]
                == provenance["test_model_version"]):
            raise ValueError("STATISTICS_CALIBRATION_MODEL_VERSION_MISMATCH")
        lineage_state = "DECLARED_DISJOINT_NOT_INDEPENDENTLY_VERIFIED"
    result = {
        "method": "isotonic-heldout@1",
        "lineage_state": lineage_state,
        "model_provenance": provenance,
        "ctr_deployment_eligible": False,
        "probability_state": "NOT_ESTABLISHED",
        "prediction_interval": None,
        "prediction_interval_state": "NOT_ESTABLISHED",
        "state": "INSUFFICIENT",
        "n": len(rows),
        "unit": "probability",
        "limitations": [
            "Input scores must come from a model trained on a separate dataset.",
            "Unique row IDs prevent direct overlap, not undocumented training leakage.",
            "Calibration is distribution-specific; no CTR deployment is implied.",
            "A declared split manifest does not independently verify training exclusion or label provenance.",
            "This calibration curve provides no individual prediction uncertainty interval.",
        ],
    }
    train, test = parts["calibration"], parts["test"]
    if min(len(train), len(test)) < 20 or len({r["label"] for r in train}) < 2:
        return {**result, "reason": "NEED_20_PER_DISJOINT_PARTITION_AND_BOTH_CLASSES"}
    model = IsotonicRegression(out_of_bounds="clip").fit(
        [r["score"] for r in train], [r["label"] for r in train]
    )
    scores = model.predict([r["score"] for r in test])
    labels = np.array([r["label"] for r in test])
    bins = []
    ece = 0.0
    for i in range(10):
        mask = (scores >= i / 10) & (
            (scores < (i + 1) / 10) if i < 9 else (scores <= 1)
        )
        n = int(mask.sum())
        confidence = float(scores[mask].mean()) if n else None
        observed = float(labels[mask].mean()) if n else None
        if n:
            ece += n / len(test) * abs(confidence - observed)
        bins.append(
            {
                "lower": i / 10,
                "upper": (i + 1) / 10,
                "n": n,
                "confidence": confidence,
                "observed": observed,
            }
        )
    return {
        **result,
        "state": "READY",
        "probability_state": "EMPIRICAL_CALIBRATION_ONLY",
        "calibration_n": len(train),
        "test_n": len(test),
        "ece": ece,
        "brier": float(np.mean((scores - labels) ** 2)),
        "bins": bins,
        "mapping": {
            "score": model.X_thresholds_.tolist(),
            "probability": model.y_thresholds_.tolist(),
        },
    }


def _statistics_experiment(data):
    """G152 Beta-Bernoulli posterior and optional seeded Thompson recommendation.

    This never allocates traffic or publishes content. Stopping rule is supplied,
    posterior-based, and does not promise frequentist optional-stopping control.
    """
    import numpy as np
    from scipy.stats import beta
    from scipy.integrate import quad
    from canonical_metrics import binomial_confidence

    arms = data.get("arms")
    threshold = data.get("stop_probability")
    minimum = data.get("minimum_trials")
    if (
        not isinstance(arms, list)
        or not 2 <= len(arms) <= 20
        or type(minimum) is not int
        or minimum < 1
        or type(threshold) not in (int, float)
        or not 0.5 < threshold < 1
        or type(data.get("enable_thompson")) is not bool
        or type(data.get("seed")) is not int
        or not 0 <= data["seed"] < 2**32
    ):
        raise ValueError("STATISTICS_EXPERIMENT_INPUT_INVALID")
    ids = []
    posterior = []
    for arm in arms:
        if (
            not isinstance(arm, dict)
            or set(arm) != {"id", "successes", "trials"}
            or not isinstance(arm["id"], str)
            or not arm["id"]
        ):
            raise ValueError("STATISTICS_EXPERIMENT_ARM_INVALID")
        confidence = binomial_confidence(arm["successes"], arm["trials"])
        ids.append(arm["id"])
        a, b = arm["successes"] + 1, arm["trials"] - arm["successes"] + 1
        posterior.append(
            {
                "id": arm["id"],
                "n": arm["trials"],
                "alpha": a,
                "beta": b,
                "mean": a / (a + b),
                "credible_interval": beta.ppf([0.025, 0.975], a, b).tolist(),
                "wilson": confidence,
            }
        )
    if len(set(ids)) != len(ids):
        raise ValueError("STATISTICS_EXPERIMENT_DUPLICATE_ARM")
    result = {
        "method": "beta-bernoulli-thompson@1",
        "state": "READY",
        "n": sum(x["n"] for x in posterior),
        "unit": "Bernoulli success probability",
        "prior": {"alpha": 1, "beta": 1},
        "arms": posterior,
        "stop_rule": {
            "minimum_trials_per_arm": minimum,
            "posterior_probability": threshold,
        },
        "limitations": [
            "Independent Bernoulli outcomes and stable arms assumed.",
            "Bayesian posterior decision rule is not a frequentist sequential significance test.",
            "Recommendation only; no traffic allocation or external action.",
        ],
    }
    if len(arms) == 2:
        first, second = posterior
        probability, error = quad(
            lambda p: beta.pdf(p, first["alpha"], first["beta"])
            * beta.cdf(p, second["alpha"], second["beta"]),
            0,
            1,
            epsabs=1e-9,
            limit=200,
            points=sorted(
                set(
                    beta.ppf(
                        [0.0001, 0.01, 0.1, 0.5, 0.9, 0.99, 0.9999],
                        first["alpha"],
                        first["beta"],
                    ).tolist()
                )
            ),
        )
        if error > 1e-6:
            return {
                **result,
                "state": "INSUFFICIENT",
                "reason": "POSTERIOR_INTEGRATION_NOT_CONVERGED",
            }
        ready = all(x["n"] >= minimum for x in posterior)
        result["comparison"] = {
            "probability_first_better": probability,
            "numerical_error_estimate": error,
            "stop_recommended": ready
            and max(probability, 1 - probability) >= threshold,
            "winner": (
                ids[int(probability < 0.5)]
                if ready and max(probability, 1 - probability) >= threshold
                else None
            ),
        }
    if data["enable_thompson"]:
        rng = np.random.default_rng(data["seed"])
        draws = [float(rng.beta(x["alpha"], x["beta"])) for x in posterior]
        result["thompson_recommendation"] = {
            "id": ids[int(np.argmax(draws))],
            "draws": draws,
            "seed": data["seed"],
        }
    return result


def _statistics_discrete_novelty(data):
    """G155 discrete KL in nats, with no silent zero-bin smoothing."""
    import numpy as np
    from scipy.special import rel_entr

    current, historical = data.get("current_counts"), data.get("historical_counts")
    if (
        not isinstance(current, dict)
        or not isinstance(historical, dict)
        or not current
        or set(current) != set(historical)
        or len(current) > 10000
        or any(not isinstance(k, str) for k in current)
        or any(
            type(v) is not int or v < 0 or v > 10**12
            for v in [*current.values(), *historical.values()]
        )
    ):
        raise ValueError("STATISTICS_NOVELTY_DISTRIBUTION_INVALID")
    result = {
        "method": "discrete-kl@1",
        "state": "READY",
        "n": sum(current.values()),
        "unit": "nats",
        "historical_n": sum(historical.values()),
        "limitations": [
            "Requires the same fixed category vocabulary and counting rule.",
            "Distribution shift is not evidence of commercial value or semantic novelty.",
        ],
    }
    if not sum(current.values()) or not sum(historical.values()):
        return {**result, "state": "NO_DATA", "kl": None}
    p = np.array(list(current.values()), float)
    q = np.array([historical[k] for k in current], float)
    p /= p.sum()
    q /= q.sum()
    unseen = [k for i, k in enumerate(current) if p[i] > 0 and q[i] == 0]
    if unseen:
        return {
            **result,
            "kl": None,
            "divergence_state": "POSITIVE_INFINITY",
            "unseen_categories": unseen,
            "reason": "CURRENT_MASS_OUTSIDE_HISTORICAL_SUPPORT",
        }
    return {
        **result,
        "kl": float(np.sum(rel_entr(p, q))),
        "surprisal": {
            k: float(-np.log(q[i])) if q[i] > 0 else None for i, k in enumerate(current)
        },
    }


def _statistics_conformal(data):
    """G150 split conformal absolute-residual interval with disjoint test coverage."""
    import math

    rows = data.get("rows")
    alpha = data.get("alpha", 0.1)
    if (
        not isinstance(rows, list)
        or not 1 <= len(rows) <= 10000
        or type(alpha) not in (int, float)
        or not 0 < alpha < 1
    ):
        raise ValueError("STATISTICS_CONFORMAL_INVALID")
    ids = set()
    parts = {"calibration": [], "test": []}
    for row in rows:
        if (
            not isinstance(row, dict)
            or set(row) != {"id", "partition", "prediction", "observed"}
            or not isinstance(row["id"], str)
            or not row["id"]
            or row["id"] in ids
            or not isinstance(row["partition"], str)
            or row["partition"] not in parts
        ):
            raise ValueError("STATISTICS_CONFORMAL_PARTITION_INVALID")
        _statistics_numbers([row["prediction"], row["observed"]], minimum=2)
        ids.add(row["id"])
        parts[row["partition"]].append(row)
    calibration, test = parts["calibration"], parts["test"]
    n = len(calibration)
    rank = math.ceil((n + 1) * (1 - alpha))
    result = {
        "method": "split-conformal-absolute-residual@1",
        "state": "INSUFFICIENT",
        "n": len(rows),
        "nominal_coverage": 1 - alpha,
        "calibration_n": n,
        "test_n": len(test),
        "limitations": [
            "Pretrained predictions must not use calibration or test outcomes.",
            "Finite-sample marginal coverage requires exchangeability, not arbitrary time-series dependence.",
            "Nominal ±5% observed holdout coverage is an acceptance measurement, not guaranteed for every dataset.",
        ],
    }
    if not test or rank > n or n < 20:
        return {**result, "reason": "INSUFFICIENT_CALIBRATION_OR_TEST"}
    quantile = sorted(abs(r["observed"] - r["prediction"]) for r in calibration)[
        rank - 1
    ]
    intervals = [
        {
            "id": r["id"],
            "lower": r["prediction"] - quantile,
            "upper": r["prediction"] + quantile,
            "covered": abs(r["observed"] - r["prediction"]) <= quantile,
        }
        for r in test
    ]
    coverage = sum(x["covered"] for x in intervals) / len(test)
    return {
        **result,
        "state": "READY",
        "residual_quantile": quantile,
        "order_statistic_rank": rank,
        "test_coverage": coverage,
        "coverage_within_five_percentage_points": abs(coverage - (1 - alpha)) <= 0.05,
        "intervals": intervals,
    }


def _statistics_did(data):
    """G149 two-series DiD with explicit pretrend equivalence gate and HAC uncertainty.

    Passing an equivalence diagnostic does not prove parallel counterfactual trends.
    No causal conclusion is promoted from observational data alone.
    """
    import numpy as np
    import statsmodels.api as sm

    treated, control = data.get("treated"), data.get("control")
    _statistics_numbers(treated, minimum=0, maximum=1000)
    _statistics_numbers(control, minimum=len(treated), maximum=len(treated))
    intervention, tolerance = data.get("intervention_index"), data.get(
        "pretrend_tolerance"
    )
    if type(intervention) is not int or not 0 <= intervention <= len(treated):
        raise ValueError("STATISTICS_DID_INTERVENTION_INVALID")
    _statistics_numbers([tolerance], minimum=1)
    if tolerance <= 0 or data.get("design_assumptions_confirmed") is not True:
        raise ValueError("STATISTICS_DID_DESIGN_ASSUMPTIONS_REQUIRED")
    result = {
        "method": "paired-series-did-hac@1",
        "state": "INSUFFICIENT",
        "n": len(treated),
        "unit": data.get("unit"),
        "effect": None,
        "interval": None,
        "assumptions": [
            "No treatment anticipation, no spillovers, comparable composition and no differential co-intervention.",
            "Counterfactual parallel trends remain an identifying assumption, not a fact proved by a pretest.",
        ],
        "limitations": [
            "Observational association is not established causality.",
            "HAC is a large-sample approximation; small samples and few independent units limit inference.",
        ],
    }
    if intervention < 8 or len(treated) - intervention < 4:
        return {**result, "reason": "NEED_8_PRE_AND_4_POST_OBSERVATIONS"}
    diff = np.array(treated) - np.array(control)
    pre = sm.OLS(diff[:intervention], sm.add_constant(np.arange(intervention))).fit(
        cov_type="HAC", cov_kwds={"maxlags": 1}, use_t=True
    )
    # TOST equivalence at alpha .05 uses the 90% two-sided confidence interval.
    ci = pre.conf_int(alpha=0.1)[1]
    equivalent = bool(ci[0] > -tolerance and ci[1] < tolerance)
    result["pretrend"] = {
        "slope": float(pre.params[1]),
        "interval_90": ci.tolist(),
        "tolerance": tolerance,
        "equivalence_passed": equivalent,
    }
    if not equivalent:
        return {**result, "reason": "PARALLEL_PRETREND_EQUIVALENCE_NOT_ESTABLISHED"}
    post = np.arange(len(diff)) >= intervention
    fitted = sm.OLS(diff, sm.add_constant(post.astype(int))).fit(
        cov_type="HAC", cov_kwds={"maxlags": 1}, use_t=True
    )
    return {
        **result,
        "state": "READY",
        "effect": float(fitted.params[1]),
        "interval": fitted.conf_int(alpha=0.05)[1].tolist(),
        "confidence": 0.95,
        "pre_n": intervention,
        "post_n": len(diff) - intervention,
        "claim_type": "conditional_DiD_estimate; causal_identification_not_verified",
    }


def _statistics_hawkes(data):
    """G147 exponential Hawkes MLE, finite observation window, time-split prediction."""
    import math
    import numpy as np
    from scipy.optimize import minimize

    times = data.get("times")
    end = data.get("observation_end")
    if not isinstance(data.get("time_unit"), str) or not data["time_unit"].strip():
        raise ValueError("STATISTICS_HAWKES_TIME_UNIT_REQUIRED")
    _statistics_numbers(times, maximum=10000)
    _statistics_numbers([end], minimum=1)
    if (
        end <= 0
        or any(t <= 0 or t >= end for t in times)
        or any(times[i] <= times[i - 1] for i in range(1, len(times)))
    ):
        raise ValueError("STATISTICS_HAWKES_TIMESTAMPS_INVALID")
    result = {
        "method": "exponential-hawkes-mle@1",
        "state": "INSUFFICIENT",
        "n": len(times),
        "time_unit": data.get("time_unit"),
        "limitations": [
            "Complete event capture and empty history at observation start assumed.",
            "Stationary univariate exponential kernel; no exogenous covariates or causal claim.",
            "Point estimates only; parameter and forecast uncertainty not quantified.",
        ],
    }
    split = end / 2
    train = np.array([t for t in times if t < split])
    all_times = np.array(times)
    if len(times) < 30 or len(train) < 30:
        return {
            **result,
            "reason": "NEED_30_EVENTS_IN_FIRST_HALF_FOR_DISJOINT_BACKTEST",
        }

    def fit(ts, T):
        # Dimensionless time makes numeric bounds inspectable across time units.
        ts = ts / T

        def loss(params):
            mu, eta, beta = params
            recurrent = 0.0
            last = 0.0
            logs = 0.0
            for t in ts:
                recurrent = (
                    math.exp(-beta * (t - last)) * (1 + recurrent) if last else 0.0
                )
                logs += math.log(mu + eta * beta * recurrent)
                last = t
            return mu + eta * float(np.sum(-np.expm1(-beta * (1 - ts)))) - logs

        candidates = []
        bounds = [(1e-6, len(ts) * 10), (1e-6, 0.999), (1e-3, 1e4)]
        for eta in (0.1, 0.5, 0.8):
            fitted = minimize(
                loss,
                [len(ts) * (1 - eta), eta, 20.0],
                method="L-BFGS-B",
                bounds=bounds,
                options={"maxiter": 500, "ftol": 1e-11},
            )
            if fitted.success and np.isfinite(fitted.fun):
                candidates.append(fitted)
        if not candidates:
            return None
        fitted = min(candidates, key=lambda f: f.fun)
        # Boundary fits indicate non-identifiability/truncation, not reliable diffusion parameters.
        if any(
            abs(v - lo) <= 1e-5 * max(1, abs(lo))
            or abs(v - hi) <= 1e-5 * max(1, abs(hi))
            for v, (lo, hi) in zip(fitted.x, bounds)
        ):
            return None
        mu, eta, beta = fitted.x
        return (
            float(mu / T),
            float(eta),
            float(beta / T),
            float(fitted.fun),
            int(fitted.nit),
        )

    baseline = fit(train, split)
    full = fit(all_times, end)
    if baseline is None or full is None:
        return {**result, "reason": "MLE_NOT_CONVERGED_OR_BOUNDARY_NONIDENTIFIABILITY"}

    def expected(fitted, ts, T, h):
        mu, eta, beta, *_ = fitted
        excitation = eta * beta * float(np.exp(-beta * (T - ts)).sum())
        rate = beta * (1 - eta)
        stationary = mu / (1 - eta)
        return (
            stationary * h
            + (excitation + mu - stationary) * (-math.expm1(-rate * h)) / rate
        )

    predicted = expected(baseline, train, split, split)
    observed = len(times) - len(train)
    mu, eta, beta, loss, iterations = full
    return {
        **result,
        "state": "READY",
        "baseline_intensity": mu,
        "branching_ratio": eta,
        "decay_rate": beta,
        "kernel_half_life": math.log(2) / beta,
        "mean_relaxation_half_life": math.log(2) / (beta * (1 - eta)),
        "negative_log_likelihood_dimensionless": loss,
        "optimizer_iterations": iterations,
        "holdout": {
            "split_time": split,
            "train_n": len(train),
            "test_n": observed,
            "predicted_count": predicted,
            "absolute_count_error": abs(predicted - observed),
            "relative_count_error": (
                abs(predicted - observed) / observed if observed else None
            ),
        },
        "expected_count_next_equal_window": expected(full, all_times, end, end),
        "finite_peak_time": None,
        "peak_reason": "Conditional expected exponential Hawkes intensity is monotone toward equilibrium; no finite interior peak.",
    }


def _statistics_entity_matching(data):
    """G154 supervised Fellegi-Sunter conditional-independence log likelihood ratios.

    No identities are merged. Ambiguous probabilities go to a proposed review list.
    """
    import numpy as np
    from scipy.special import expit
    from sklearn.metrics import precision_score, recall_score

    rows = data.get("rows")
    threshold = data.get("match_threshold", 0.95)
    nonmatch = data.get("nonmatch_threshold", 0.05)
    if (
        not isinstance(rows, list)
        or not 1 <= len(rows) <= 10000
        or type(threshold) not in (int, float)
        or type(nonmatch) not in (int, float)
        or not 0 < nonmatch < threshold < 1
    ):
        raise ValueError("STATISTICS_MATCH_INPUT_INVALID")
    partitions = {"train": [], "test": [], "candidate": []}
    seen = set()
    dimension = None
    for row in rows:
        if (
            not isinstance(row, dict)
            or not {"id", "partition", "agreements", "label"}.issubset(row)
            or set(row) - {"id", "partition", "agreements", "label", "identity_pair"}
            or not isinstance(row["id"], str)
            or not row["id"]
            or row["id"] in seen
            or not isinstance(row["partition"], str)
            or row["partition"] not in partitions
            or not isinstance(row["agreements"], list)
            or not 1 <= len(row["agreements"]) <= 30
            or any(type(x) is not bool for x in row["agreements"])
        ):
            raise ValueError("STATISTICS_MATCH_ROWS_INVALID")
        if "identity_pair" in row:
            if row["partition"] != "candidate":
                raise ValueError("STATISTICS_MATCH_PAIR_ONLY_FOR_CANDIDATE")
            pair = row["identity_pair"]
            if pair is not None:
                if not isinstance(pair, dict) or set(pair) != {"left", "right"}:
                    raise ValueError("STATISTICS_MATCH_IDENTITY_PAIR_INVALID")
                for identity in pair.values():
                    if (
                        not isinstance(identity, dict)
                        or set(identity)
                        != {
                            "label",
                            "registry_subject_id",
                            "source_evidence_id",
                            "start",
                            "end",
                            "quote",
                        }
                        or not isinstance(identity["label"], str)
                        or not identity["label"].strip()
                        or len(identity["label"]) > 300
                        or (
                            identity["registry_subject_id"] is not None
                            and (
                                not isinstance(identity["registry_subject_id"], str)
                                or not identity["registry_subject_id"].strip()
                            )
                        )
                        or type(identity["source_evidence_id"]) is not int
                        or identity["source_evidence_id"] <= 0
                        or type(identity["start"]) is not int
                        or identity["start"] < 0
                        or type(identity["end"]) is not int
                        or identity["end"] <= identity["start"]
                        or not isinstance(identity["quote"], str)
                        or not identity["quote"]
                        or len(identity["quote"]) > 10000
                        or identity["end"] - identity["start"] != len(identity["quote"])
                        or identity["label"] not in identity["quote"]
                    ):
                        raise ValueError("STATISTICS_MATCH_IDENTITY_REFERENCE_INVALID")
        if row["partition"] == "candidate":
            if row["label"] is not None:
                raise ValueError("STATISTICS_MATCH_CANDIDATE_LABEL_INVALID")
        elif type(row["label"]) is not int or row["label"] not in (0, 1):
            raise ValueError("STATISTICS_MATCH_LABEL_REQUIRED")
        dimension = len(row["agreements"]) if dimension is None else dimension
        if dimension != len(row["agreements"]):
            raise ValueError("STATISTICS_MATCH_DIMENSION_MISMATCH")
        seen.add(row["id"])
        partitions[row["partition"]].append(row)
    train, test = partitions["train"], partitions["test"]
    positive = [r["agreements"] for r in train if r["label"] == 1]
    negative = [r["agreements"] for r in train if r["label"] == 0]
    result = {
        "method": "supervised-fellegi-sunter@1",
        "state": "INSUFFICIENT",
        "n": len(rows),
        "unit": "conditional match probability",
        "limitations": [
            "Comparison fields assumed conditionally independent given match status.",
            "Labeled sample class balance supplies the prior; blocking/selection bias can invalidate it.",
            "No automatic merge or identity permission change; review is required.",
            "Supplied labels and Registry IDs are identity claims, not official-name verification; source quotes only establish custody.",
        ],
    }
    if min(len(positive), len(negative)) < 10 or len(test) < 20:
        return {**result, "reason": "NEED_10_TRAIN_PER_CLASS_AND_20_DISJOINT_TEST"}
    # Explicit Beta(1,1) smoothing keeps absent agreements finite.
    m = (np.sum(positive, axis=0) + 1) / (len(positive) + 2)
    u = (np.sum(negative, axis=0) + 1) / (len(negative) + 2)
    prior = (len(positive) + 1) / (len(train) + 2)

    def probability(row):
        agreements = np.array(row["agreements"])
        log_ratio = np.where(agreements, np.log(m / u), np.log((1 - m) / (1 - u))).sum()
        return float(expit(np.log(prior / (1 - prior)) + log_ratio))

    predictions = [int(probability(r) >= threshold) for r in test]
    labels = [r["label"] for r in test]
    candidates = []
    for row in partitions["candidate"]:
        p = probability(row)
        candidates.append(
            {
                "id": row["id"],
                "identity_pair": row.get("identity_pair"),
                "source_binding_state": (
                    "NOT_VERIFIED" if row.get("identity_pair") else "NOT_PROVIDED"
                ),
                "registry_identity_state": "REQUIRES_SEPARATE_REGISTRY_REVIEW",
                "probability": p,
                "recommendation": (
                    "MATCH_REVIEW"
                    if p >= threshold
                    else "NONMATCH" if p <= nonmatch else "MANUAL_REVIEW"
                ),
            }
        )
    return {
        **result,
        "state": "READY",
        "m_probabilities": m.tolist(),
        "u_probabilities": u.tolist(),
        "class_prior": prior,
        "smoothing": "Beta(1,1)",
        "match_threshold": threshold,
        "nonmatch_threshold": nonmatch,
        "train_n": len(train),
        "positive_train_n": len(positive),
        "negative_train_n": len(negative),
        "probability_calibration_state": "NOT_ESTABLISHED",
        "test_n": len(test),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "candidates": candidates,
    }


def _statistics_classifier_evaluation(data):
    """G153 explicit held-out per-language evaluation, abstaining below threshold."""
    from sklearn.metrics import f1_score, confusion_matrix

    rows = data.get("rows")
    threshold = data.get("confidence_threshold")
    if (
        not isinstance(rows, list)
        or not 1 <= len(rows) <= 10000
        or type(threshold) not in (int, float)
        or not 0 < threshold <= 1
        or not isinstance(data.get("model_version"), str)
        or not data["model_version"]
        or data.get("heldout_declared") is not True
    ):
        raise ValueError("STATISTICS_CLASSIFIER_EVALUATION_INVALID")
    labels = ["positive", "neutral", "negative"]
    grouped = {language: [] for language in ("zh", "en", "ko")}
    ids = set()
    for row in rows:
        if (
            not isinstance(row, dict)
            or set(row) != {"id", "language", "label", "probabilities"}
            or not isinstance(row["id"], str)
            or not row["id"]
            or row["id"] in ids
            or not isinstance(row["language"], str)
            or row["language"] not in grouped
            or row["label"] not in labels
        ):
            raise ValueError("STATISTICS_CLASSIFIER_ROW_INVALID")
        values = row["probabilities"]
        if not isinstance(values, dict) or set(values) != set(labels):
            raise ValueError("STATISTICS_CLASSIFIER_PROBABILITIES_INVALID")
        _statistics_numbers(list(values.values()), minimum=3)
        if (
            any(not 0 <= p <= 1 for p in values.values())
            or abs(sum(values.values()) - 1) > 1e-8
        ):
            raise ValueError("STATISTICS_CLASSIFIER_PROBABILITIES_INVALID")
        ids.add(row["id"])
        predicted = max(labels, key=lambda label: values[label])
        grouped[row["language"]].append((row["label"], predicted, values[predicted]))
    results = {}
    for language, records in grouped.items():
        if not records:
            results[language] = {"state": "NO_DATA", "n": 0}
            continue
        accepted = [r for r in records if r[2] >= threshold]
        bins = []
        for i in range(10):
            selected = [
                r
                for r in records
                if i / 10 <= r[2] and (r[2] < (i + 1) / 10 if i < 9 else r[2] <= 1)
            ]
            bins.append(
                {
                    "n": len(selected),
                    "confidence": (
                        sum(r[2] for r in selected) / len(selected)
                        if selected
                        else None
                    ),
                    "accuracy": (
                        sum(r[0] == r[1] for r in selected) / len(selected)
                        if selected
                        else None
                    ),
                }
            )
        results[language] = {
            "state": "READY",
            "n": len(records),
            "accepted_n": len(accepted),
            "unknown_n": len(records) - len(accepted),
            "coverage": len(accepted) / len(records),
            "macro_f1_all": float(
                f1_score(
                    [r[0] for r in records],
                    [r[1] for r in records],
                    labels=labels,
                    average="macro",
                    zero_division=0,
                )
            ),
            "macro_f1_accepted": (
                float(
                    f1_score(
                        [r[0] for r in accepted],
                        [r[1] for r in accepted],
                        labels=labels,
                        average="macro",
                        zero_division=0,
                    )
                )
                if accepted
                else None
            ),
            "accepted_prediction_counts": {
                label: sum(r[1] == label for r in accepted) for label in labels
            },
            "ratio_denominator": len(accepted),
            "calibration_bins": bins,
        }
    return {
        "method": "heldout-language-classifier-evaluation@1",
        "state": "READY",
        "n": len(rows),
        "unit": "classification evaluation",
        "model_version": data["model_version"],
        "languages": results,
        "limitations": [
            "Held-out provenance is declared, not independently verified against model training records.",
            "This evaluates supplied predictions; it does not implement BERTopic or train a classifier.",
        ],
    }


def _statistics_beta_ranking(data):
    """G146 Beta-binomial empirical Bayes by marginal maximum likelihood."""
    import numpy as np
    from scipy.optimize import minimize
    from scipy.special import betaln
    from scipy.stats import beta
    from canonical_metrics import binomial_confidence

    groups = data.get("groups")
    if not isinstance(groups, list) or not 1 <= len(groups) <= 1000:
        raise ValueError("STATISTICS_RANKING_INVALID")
    seen = set()
    for group in groups:
        if (
            not isinstance(group, dict)
            or set(group) != {"id", "successes", "trials"}
            or not isinstance(group["id"], str)
            or not group["id"]
            or group["id"] in seen
        ):
            raise ValueError("STATISTICS_RANKING_GROUP_INVALID")
        seen.add(group["id"])
        binomial_confidence(group["successes"], group["trials"])
    informative = [g for g in groups if g["trials"] > 0]
    result = {
        "method": "beta-binomial-empirical-bayes@1",
        "state": "INSUFFICIENT",
        "n": len(groups),
        "unit": "shrunken success probability",
        "limitations": [
            "Groups must be exchangeable Bernoulli samples with comparable opportunity definitions.",
            "Intervals condition on the fitted hyperparameters; hyperparameter uncertainty is omitted.",
            "Ranking is not causal effectiveness and does not remove selection bias.",
        ],
    }
    if len(informative) < 5:
        return {**result, "reason": "NEED_FIVE_NONEMPTY_COMPARABLE_GROUPS"}
    k = np.array([g["successes"] for g in informative])
    n = np.array([g["trials"] for g in informative])

    def objective(log_ab):
        a, b = np.exp(log_ab)
        return -float(np.sum(betaln(k + a, n - k + b) - betaln(a, b)))

    fits = [
        minimize(
            objective, np.log(start), method="L-BFGS-B", bounds=[(-7, 14), (-7, 14)]
        )
        for start in ((1, 1), (2, 8), (8, 2))
    ]
    fits = [fit for fit in fits if fit.success and np.isfinite(fit.fun)]
    if not fits:
        return {**result, "reason": "HYPERPARAMETER_OPTIMIZATION_FAILED"}
    fit = min(fits, key=lambda fit: fit.fun)
    if any(abs(value + 7) < 1e-3 or abs(value - 14) < 1e-3 for value in fit.x):
        return {
            **result,
            "reason": "HYPERPARAMETERS_NOT_IDENTIFIABLE_AT_NUMERICAL_BOUNDARY",
        }
    a, b = np.exp(fit.x)
    rows = []
    for group in groups:
        trials, successes = group["trials"], group["successes"]
        rows.append(
            {
                "id": group["id"],
                "n": trials,
                "state": "READY" if trials else "NO_DATA",
                "posterior_mean": (
                    float((a + successes) / (a + b + trials)) if trials else None
                ),
                "credible_interval": (
                    beta.ppf(
                        [0.025, 0.975], a + successes, b + trials - successes
                    ).tolist()
                    if trials
                    else None
                ),
                "wilson": binomial_confidence(successes, trials),
            }
        )
    return {
        **result,
        "state": "READY",
        "alpha": float(a),
        "beta": float(b),
        "groups": rows,
        "ranking": [
            row["id"]
            for row in sorted(
                [r for r in rows if r["n"]], key=lambda r: -r["posterior_mean"]
            )
        ],
    }


def _statistics_attribution(data):
    """G149 finite absorbing Markov and exact Shapley removal attribution.

    Removed channels absorb into nonconversion (no invented rerouting).
    This is descriptive attribution of supplied observed paths, not causal uplift.
    """
    import math
    import numpy as np

    paths = data.get("paths")
    if not isinstance(paths, list) or not 1 <= len(paths) <= 10000:
        raise ValueError("STATISTICS_ATTRIBUTION_PATHS_INVALID")
    ids = set()
    channels = set()
    for path in paths:
        if (
            not isinstance(path, dict)
            or set(path) != {"id", "channels", "converted"}
            or not isinstance(path["id"], str)
            or not path["id"]
            or path["id"] in ids
            or not isinstance(path["channels"], list)
            or not 1 <= len(path["channels"]) <= 100
            or any(not isinstance(c, str) or not c.strip() for c in path["channels"])
            or type(path["converted"]) is not bool
        ):
            raise ValueError("STATISTICS_ATTRIBUTION_PATH_INVALID")
        channels.update(path["channels"])
        ids.add(path["id"])
    if len(channels) > 8:
        raise ValueError("STATISTICS_EXACT_SHAPLEY_CHANNEL_LIMIT")
    channels = sorted(channels)
    m = len(channels)
    index = {c: i + 1 for i, c in enumerate(channels)}
    counts = np.zeros((m + 1, m + 3))
    for path in paths:
        sequence = (
            [0]
            + [index[c] for c in path["channels"]]
            + [m + 1 if path["converted"] else m + 2]
        )
        for source, target in zip(sequence, sequence[1:]):
            counts[source, target] += 1
    transitions = counts / counts.sum(axis=1)[:, None]

    def coalition_value(mask):
        p = transitions.copy()
        for j in range(m):
            if not mask & (1 << j):
                p[:, m + 2] += p[:, j + 1]
                p[:, j + 1] = 0
        probabilities = np.linalg.solve(np.eye(m + 1) - p[:, : m + 1], p[:, m + 1])
        if np.any(probabilities < -1e-8) or np.any(probabilities > 1 + 1e-8):
            raise RuntimeError("STATISTICS_ATTRIBUTION_ABSORPTION_INVALID")
        return float(probabilities[0])

    values = [coalition_value(mask) for mask in range(1 << m)]
    baseline = values[-1]
    if baseline <= 0:
        return {
            "method": "absorbing-markov-exact-shapley@1",
            "state": "NO_DATA",
            "n": len(paths),
            "reason": "NO_OBSERVED_CONVERSIONS",
            "unit": "observed conversion probability",
        }
    shapley = []
    for j in range(m):
        score = 0.0
        for mask in range(1 << m):
            if mask & (1 << j):
                continue
            size = mask.bit_count()
            weight = (
                math.factorial(size) * math.factorial(m - size - 1) / math.factorial(m)
            )
            score += weight * (values[mask | (1 << j)] - values[mask])
        shapley.append(score)
    if abs(sum(shapley) - (baseline - values[0])) > 1e-8:
        raise RuntimeError("STATISTICS_SHAPLEY_EFFICIENCY_FAILED")
    return {
        "method": "absorbing-markov-exact-shapley@1",
        "state": "READY",
        "n": len(paths),
        "unit": "observed conversion probability",
        "baseline_probability": baseline,
        "channels": [
            {
                "id": c,
                "removal_effect": (baseline - values[((1 << m) - 1) ^ (1 << j)])
                / baseline,
                "shapley": shapley[j],
                "attribution_share": shapley[j] / baseline,
            }
            for j, c in enumerate(channels)
        ],
        "limitations": [
            "First-order Markov path model; only supplied path observations are represented.",
            "Removing a channel redirects incoming flow to nonconversion; this is a model convention.",
            "Descriptive attribution is not causal incrementality or private sales inference.",
            "No sampling confidence intervals are estimated by this finite exact calculation.",
        ],
    }


def _statistics_bass(data):
    """G147 constrained Bass cumulative diffusion fit and first-half-time backtest."""
    import math
    import numpy as np
    from scipy.optimize import least_squares

    times, cumulative = data.get("times"), data.get("cumulative")
    _statistics_numbers(times, maximum=1000)
    _statistics_numbers(cumulative, minimum=len(times), maximum=len(times))
    if (
        any(t <= 0 for t in times)
        or any(times[i] <= times[i - 1] for i in range(1, len(times)))
        or any(c < 0 for c in cumulative)
        or any(cumulative[i] < cumulative[i - 1] for i in range(1, len(cumulative)))
        or not isinstance(data.get("time_unit"), str)
        or not data["time_unit"].strip()
    ):
        raise ValueError("STATISTICS_BASS_INPUT_INVALID")
    result = {
        "method": "bass-nonlinear-least-squares@1",
        "state": "INSUFFICIENT",
        "n": len(times),
        "time_unit": data["time_unit"],
        "unit": "cumulative adopters",
        "limitations": [
            "Closed fixed market potential, one adoption per unit and launch at time zero assumed.",
            "Cumulative residuals are correlated; no independent-error confidence interval is claimed.",
            "Point fit does not establish adoption population coverage or causal diffusion.",
        ],
    }
    if len(times) < 30 or not cumulative or cumulative[-1] <= 0:
        return {**result, "reason": "NEED_30_OBSERVATIONS_AND_POSITIVE_ADOPTIONS"}
    t = np.array(times)
    y = np.array(cumulative)
    split = int(np.searchsorted(t, t[-1] / 2, side="right"))
    if split < 10 or len(t) - split < 5:
        return {**result, "reason": "INSUFFICIENT_FIRST_HALF_TIME_BACKTEST"}

    def fit(tx, yx):
        scale_t = tx[-1]
        scale_y = max(yx[-1], 1)

        def curve(params, where):
            p, q, m = np.exp(params)
            z = np.exp(-(p + q) * where / scale_t)
            return scale_y * m * (1 - z) / (1 + q / p * z)

        candidates = []
        for start in ((0.1, 1.0, 2.0), (0.5, 2.0, 3.0), (0.01, 5.0, 10.0)):
            fitted = least_squares(
                lambda params: (curve(params, tx) - yx) / scale_y,
                np.log(start),
                bounds=([-12, -12, 0], [5, 7, 12]),
                max_nfev=3000,
            )
            if (
                fitted.success
                and np.linalg.matrix_rank(fitted.jac) == 3
                and np.linalg.cond(fitted.jac) < 1e8
            ):
                if np.any(abs(fitted.x - np.array([-12, -12, 0])) < 1e-4) or np.any(
                    abs(fitted.x - np.array([5, 7, 12])) < 1e-4
                ):
                    continue
                candidates.append(fitted)
        if not candidates:
            return None
        fit = min(candidates, key=lambda f: f.cost)
        p, q, m = np.exp(fit.x)
        return {
            "innovation": p / scale_t,
            "imitation": q / scale_t,
            "market_potential": m * scale_y,
            "cost": float(fit.cost),
            "jacobian_condition": float(np.linalg.cond(fit.jac)),
            "predict": lambda where: curve(fit.x, where),
        }

    baseline, full = fit(t[:split], y[:split]), fit(t, y)
    if baseline is None or full is None:
        return {
            **result,
            "reason": "BASS_PARAMETERS_NOT_IDENTIFIABLE_OR_OPTIMIZER_FAILED",
        }
    predicted = baseline["predict"](t[split:])
    p, q = full["innovation"], full["imitation"]
    return {
        **result,
        "state": "READY",
        **{k: float(v) for k, v in full.items() if k != "predict"},
        "peak_time_from_launch": max(0.0, math.log(q / p) / (p + q)),
        "holdout": {
            "train_n": split,
            "test_n": len(t) - split,
            "split_time": float(t[-1] / 2),
            "predicted_cumulative": predicted.tolist(),
            "mae": float(np.mean(abs(predicted - y[split:]))),
            "final_cumulative_relative_error": float(
                abs(predicted[-1] - y[-1]) / y[-1]
            ),
        },
    }


def _statistics_topics(data):
    """G153 genuine lightweight BERTopic + HDBSCAN, no model/API/GPU dependency.

    Character TF-IDF/SVD embeddings are the explicit lexical backend, not a claim
    of pretrained neural semantic capability. Documents must be same-language.
    """
    import warnings
    import numpy as np

    documents = data.get("documents")
    if (
        not isinstance(documents, list)
        or len(documents) > 500
        or any(
            not isinstance(text, str) or not text.strip() or len(text) > 5000
            for text in documents
        )
        or data.get("language") not in {"zh", "en", "ko"}
    ):
        raise ValueError("STATISTICS_TOPICS_INPUT_INVALID")
    result = {
        "method": "bertopic-lexical-svd-hdbscan@1",
        "state": "INSUFFICIENT",
        "n": len(documents),
        "unit": "observed document topics",
        "language": data["language"],
        "limitations": [
            "Character TF-IDF/SVD is lexical similarity, not pretrained neural semantic understanding.",
            "HDBSCAN membership strength is not a calibrated topic probability.",
            "Topic terms are extracted character n-grams and require human interpretation.",
            "Clustering is descriptive and does not infer sentiment, stance, causality or population prevalence.",
        ],
    }
    if len(documents) < 20:
        return {**result, "reason": "NEED_20_DOCUMENTS_FOR_BOUNDED_TOPIC_CLUSTERING"}
    # BERTopic itself installs warning filters on import; contain them locally.
    try:
        with warnings.catch_warnings():
            from bertopic import BERTopic
            from bertopic.dimensionality import BaseDimensionalityReduction
    except ImportError:
        return {
            **result,
            "state": "UNAVAILABLE",
            "reason": "OPTIONAL_BERTOPIC_DEPENDENCIES_UNAVAILABLE",
        }
    from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
    from sklearn.decomposition import TruncatedSVD
    from sklearn.preprocessing import normalize
    from sklearn.cluster import HDBSCAN

    vectorizer = TfidfVectorizer(
        analyzer="char", ngram_range=(2, 4), min_df=2, max_features=5000
    )
    try:
        sparse = vectorizer.fit_transform(documents)
    except ValueError:
        return {**result, "reason": "NO_SHARED_LEXICAL_VOCABULARY"}
    dimension = min(32, sparse.shape[0] - 1, sparse.shape[1] - 1)
    if dimension < 2:
        return {**result, "reason": "INSUFFICIENT_LEXICAL_DIMENSIONS"}
    embeddings = normalize(
        TruncatedSVD(n_components=dimension, random_state=20261017).fit_transform(
            sparse
        )
    )
    model = BERTopic(
        embedding_model=None,
        umap_model=BaseDimensionalityReduction(),
        hdbscan_model=HDBSCAN(min_cluster_size=5, min_samples=3, metric="euclidean"),
        vectorizer_model=CountVectorizer(
            analyzer="char", ngram_range=(2, 4), min_df=1, max_features=5000
        ),
        calculate_probabilities=False,
        verbose=False,
    )
    topics, probabilities = model.fit_transform(documents, embeddings=embeddings)
    identified = sorted(set(topics) - {-1})
    if not identified:
        return {
            **result,
            "reason": "NO_STABLE_DENSITY_CLUSTERS",
            "assignments": [int(t) for t in topics],
            "outlier_n": len(documents),
        }
    terms = {
        str(topic): [
            {"term": term, "class_tfidf": float(weight)}
            for term, weight in model.get_topic(topic)
        ]
        for topic in identified
    }
    return {
        **result,
        "state": "READY",
        "assignments": [int(t) for t in topics],
        "outlier_n": sum(t == -1 for t in topics),
        "topics": terms,
        "membership_strength": (
            np.asarray(probabilities).tolist() if probabilities is not None else None
        ),
        "parameters": {
            "embedding": "character-tfidf-truncated-svd",
            "svd_dimensions": dimension,
            "min_cluster_size": 5,
            "min_samples": 3,
            "seed": 20261017,
        },
    }


def _statistics_novelty(data):
    """G155 optional categorical shift and same-version embedding distances."""
    if not isinstance(data, dict) or set(data) - {
        "current_counts",
        "historical_counts",
        "embeddings",
    }:
        raise ValueError("STATISTICS_NOVELTY_INPUT_INVALID")
    has_counts = "current_counts" in data or "historical_counts" in data
    if not has_counts and "embeddings" not in data:
        raise ValueError("STATISTICS_NOVELTY_INPUT_REQUIRED")
    result = (
        _statistics_discrete_novelty(data)
        if has_counts
        else {
            "method": "same-version-embedding-distance@1",
            "state": "READY",
            "unit": "cosine distance [0,2]",
            "limitations": [],
        }
    )
    if "embeddings" not in data:
        return result
    import numpy as np
    from scipy.spatial.distance import cdist

    block = data["embeddings"]
    if not isinstance(block, dict) or set(block) != {
        "current_model",
        "historical_model",
        "current",
        "historical",
    }:
        raise ValueError("STATISTICS_EMBEDDING_INPUT_INVALID")
    model = block["current_model"]
    if (
        not isinstance(model, dict)
        or set(model) != {"model_id", "version", "preprocessing_id"}
        or any(not isinstance(v, str) or not v.strip() for v in model.values())
        or block["historical_model"] != model
    ):
        raise ValueError("STATISTICS_EMBEDDING_MODEL_MISMATCH")
    matrices, record_ids, dimension = [], [], None
    for partition in ("current", "historical"):
        rows = block[partition]
        if not isinstance(rows, list) or len(rows) > 500:
            raise ValueError("STATISTICS_EMBEDDING_ROWS_INVALID")
        ids, vectors = [], []
        for row in rows:
            if (
                not isinstance(row, dict)
                or set(row) != {"id", "vector"}
                or not isinstance(row["id"], str)
                or not row["id"].strip()
            ):
                raise ValueError("STATISTICS_EMBEDDING_ROW_INVALID")
            vector = _statistics_numbers(row["vector"], minimum=2, maximum=2048)
            dimension = len(vector) if dimension is None else dimension
            if len(vector) != dimension or np.linalg.norm(vector) <= 0:
                raise ValueError("STATISTICS_EMBEDDING_DIMENSION_OR_ZERO_NORM")
            ids.append(row["id"])
            vectors.append(vector)
        if len(set(ids)) != len(ids):
            raise ValueError("STATISTICS_EMBEDDING_DUPLICATE_ID")
        matrices.append(np.array(vectors, dtype=float))
        record_ids.append(ids)
    if set(record_ids[0]) & set(record_ids[1]):
        raise ValueError("STATISTICS_EMBEDDING_PARTITION_OVERLAP")
    details = {
        "method": "nearest-historical-cosine-distance@1",
        "unit": "cosine distance [0,2]",
        "model": model,
        "n": len(record_ids[0]),
        "historical_n": len(record_ids[1]),
        "model_binding_state": "DECLARED_NOT_INDEPENDENTLY_VERIFIED",
        "limitations": [
            "Same embedding model/version/preprocessing declared; vectors are supplied, not generated or independently authenticated here.",
            "Distance describes representation geometry, not semantic truth, commercial value, or an automatic new-topic threshold.",
            "Nearest-history distance depends on historical corpus coverage; duplicate text with distinct record IDs may legitimately have zero distance.",
        ],
    }
    if not all(record_ids):
        details.update(state="NO_DATA", nearest=None)
    else:
        distances = np.clip(cdist(matrices[0], matrices[1], metric="cosine"), 0, 2)
        if not np.isfinite(distances).all():
            raise ValueError("STATISTICS_EMBEDDING_DISTANCE_NOT_FINITE")
        nearest = np.argmin(distances, axis=1)
        details.update(
            state="READY",
            nearest=[
                {
                    "id": identity,
                    "historical_id": record_ids[1][int(nearest[i])],
                    "distance": float(distances[i, nearest[i]]),
                }
                for i, identity in enumerate(record_ids[0])
            ],
        )
    result["embedding_distance"] = details
    result["limitations"].extend(details["limitations"])
    if not has_counts:
        result.update(
            state=details["state"], n=details["n"], historical_n=details["historical_n"]
        )
    return result


def _statistics_synthetic_control(data):
    """G149 outcome-only simplex synthetic control with heldout pre-period checks.

    Restricted Abadie/Diamond/Hainmueller design: equal pre-outcome predictor
    importance; no optimized covariate weighting or causal identification proof.
    """
    import numpy as np
    from scipy.optimize import minimize
    from datetime import date

    required = {
        "periods",
        "frequency",
        "treated",
        "donors",
        "pre_periods",
        "max_pre_rmse",
        "design",
    }
    if not isinstance(data, dict) or set(data) != required:
        raise ValueError("STATISTICS_SYNTHETIC_CONTROL_INPUT_INVALID")
    periods = data["periods"]
    if (
        not isinstance(periods, list)
        or len(periods) > 500
        or not isinstance(data["frequency"], str)
        or data["frequency"] not in {"day", "month", "quarter", "year"}
        or type(data["pre_periods"]) is not int
        or not 0 <= data["pre_periods"] <= len(periods)
    ):
        raise ValueError("STATISTICS_SYNTHETIC_CONTROL_PERIODS_INVALID")
    serial = []
    for value in periods:
        try:
            day = date.fromisoformat(value)
            if day.isoformat() != value:
                raise ValueError()
            if data["frequency"] == "day":
                position = day.toordinal()
            elif data["frequency"] == "month" and day.day == 1:
                position = day.year * 12 + day.month - 1
            elif (
                data["frequency"] == "quarter"
                and day.day == 1
                and day.month in {1, 4, 7, 10}
            ):
                position = day.year * 4 + (day.month - 1) // 3
            elif data["frequency"] == "year" and day.day == day.month == 1:
                position = day.year
            else:
                raise ValueError()
        except (TypeError, ValueError) as exc:
            raise ValueError("STATISTICS_SYNTHETIC_CONTROL_TIME_GRID_INVALID") from exc
        serial.append(position)
    if any(serial[i] - serial[i - 1] != 1 for i in range(1, len(serial))):
        raise ValueError("STATISTICS_SYNTHETIC_CONTROL_TIME_GRID_INVALID")
    _statistics_numbers([data["max_pre_rmse"]], minimum=1)
    if data["max_pre_rmse"] <= 0:
        raise ValueError("STATISTICS_SYNTHETIC_CONTROL_ERROR_TOLERANCE_REQUIRED")
    design = data["design"]
    declarations = {"no_anticipation", "no_spillovers", "comparable_measurement"}
    if (
        not isinstance(design, dict)
        or set(design) != declarations | {"selection_protocol"}
        or any(type(design[k]) is not bool for k in declarations)
        or not isinstance(design["selection_protocol"], str)
        or not design["selection_protocol"].strip()
    ):
        raise ValueError("STATISTICS_SYNTHETIC_CONTROL_DESIGN_REQUIRED")
    donors = data["donors"]
    if not isinstance(donors, list) or not 2 <= len(donors) <= 20:
        raise ValueError("STATISTICS_SYNTHETIC_CONTROL_DONORS_INVALID")
    identities, outcomes = [], []
    for i, row in enumerate([data["treated"], *donors]):
        keys = (
            {"id", "outcomes"} if i == 0 else {"id", "outcomes", "untreated_declared"}
        )
        if (
            not isinstance(row, dict)
            or set(row) != keys
            or not isinstance(row["id"], str)
            or not row["id"].strip()
            or (i and row["untreated_declared"] is not True)
        ):
            raise ValueError("STATISTICS_SYNTHETIC_CONTROL_UNIT_INVALID")
        _statistics_numbers(row["outcomes"], maximum=500)
        if len(row["outcomes"]) != len(periods):
            raise ValueError("STATISTICS_SYNTHETIC_CONTROL_UNBALANCED_PANEL")
        identities.append(row["id"])
        outcomes.append(row["outcomes"])
    if len(set(identities)) != len(identities):
        raise ValueError("STATISTICS_SYNTHETIC_CONTROL_DUPLICATE_UNIT")
    result = {
        "method": "outcome-only-simplex-synthetic-control@1",
        "state": "INSUFFICIENT",
        "n": len(periods),
        "donor_n": len(donors),
        "unit": "input outcome units",
        "pre_n": data["pre_periods"],
        "post_n": len(periods) - data["pre_periods"],
        "causal_claim": "NOT_ESTABLISHED",
        "design": design,
        "design_verification": "USER_DECLARED_NOT_INDEPENDENTLY_VERIFIED",
        "interval": None,
        "interval_state": "NOT_ESTABLISHED",
        "limitations": [
            "Outcome-only synthetic control with equal pre-outcome importance and nonnegative weights summing to one; not the full covariate-V selection procedure.",
            "Treated pre-outcomes alone train weights; a disjoint pre-intervention segment checks fit before all pre-periods are refitted. Post outcomes never tune weights or thresholds.",
            "Donor nonexposure, no anticipation/spillovers and comparable measurement are declared assumptions, not established facts.",
            "Post-period discrepancy is descriptive unless causal design assumptions hold; no confidence interval or causal proof is supplied.",
            "In-space donor placebos are sensitivity diagnostics, not randomized-treatment p-values; poor prefit placebos remain visible and excluded from comparison.",
        ],
    }
    pre = data["pre_periods"]
    if pre < 12 or len(periods) - pre < 2:
        return {**result, "reason": "NEED_12_PRE_AND_2_POST_PERIODS"}
    if not all(design[k] for k in declarations):
        return {**result, "reason": "DECLARED_DESIGN_ASSUMPTIONS_NOT_MET"}
    train = pre - max(4, pre // 4)
    panel = np.asarray(outcomes, dtype=float).T
    tolerance = float(data["max_pre_rmse"])

    def fit(target, pool, stop):
        y, x = target[:stop], pool[:stop]
        scale = max(float(np.std(y)), float(np.std(x)), 1.0)
        y, x = y / scale, x / scale
        difference = x[:, :-1] - x[:, -1:]
        singular = np.linalg.svd(difference, compute_uv=False)
        if len(singular) and (
            len(singular) < x.shape[1] - 1
            or singular[-1] <= 1e-8 * max(singular[0], 1e-12)
        ):
            return None, "DONOR_WEIGHTS_NOT_IDENTIFIABLE"
        if x.shape[1] == 1:
            return np.ones(1), None
        objective = lambda w: float(np.mean((x @ w - y) ** 2))
        gradient = lambda w: 2 * x.T @ (x @ w - y) / len(y)
        fitted = minimize(
            objective,
            np.full(x.shape[1], 1 / x.shape[1]),
            jac=gradient,
            method="SLSQP",
            bounds=[(0.0, 1.0)] * x.shape[1],
            constraints={
                "type": "eq",
                "fun": lambda w: float(w.sum() - 1),
                "jac": lambda w: np.ones_like(w),
            },
            options={"ftol": 1e-12, "maxiter": 2000},
        )
        w = fitted.x
        if not fitted.success or abs(w.sum() - 1) > 1e-7 or np.min(w) < -1e-8:
            return None, "SIMPLEX_OPTIMIZER_NOT_CONVERGED"
        # Remove only bound-roundoff after the raw feasibility check, then recheck KKT.
        w = np.maximum(w, 0.0)
        w /= w.sum()
        g = gradient(w)
        active = w > 1e-7
        lagrange = float(np.mean(g[active]))
        residual = max(
            float(np.max(np.abs(g[active] - lagrange))),
            (
                float(np.max(np.maximum(lagrange - g[~active], 0)))
                if (~active).any()
                else 0.0
            ),
        )
        if residual > 1e-5:
            return None, "SIMPLEX_KKT_CHECK_FAILED"
        return w, None

    def evaluate(target, pool):
        training_weights, error = fit(target, pool, train)
        if error:
            return {"state": "INSUFFICIENT", "reason": error}
        validation = pool[train:pre] @ training_weights
        training_rmse = float(
            np.sqrt(np.mean((target[:train] - pool[:train] @ training_weights) ** 2))
        )
        validation_rmse = float(np.sqrt(np.mean((target[train:pre] - validation) ** 2)))
        record = {
            "training_n": train,
            "validation_n": pre - train,
            "training_rmse": training_rmse,
            "validation_rmse": validation_rmse,
            "max_pre_rmse": tolerance,
        }
        if max(training_rmse, validation_rmse) > tolerance:
            return {
                **record,
                "state": "INSUFFICIENT",
                "reason": "PRE_FIT_OR_HOLDOUT_ERROR_EXCEEDS_DECLARED_TOLERANCE",
            }
        weights, error = fit(target, pool, pre)
        if error:
            return {**record, "state": "INSUFFICIENT", "reason": error}
        synthetic = pool @ weights
        gaps = target - synthetic
        pre_rmse = float(np.sqrt(np.mean(gaps[:pre] ** 2)))
        post_rmse = float(np.sqrt(np.mean(gaps[pre:] ** 2)))
        ratio = (
            post_rmse / pre_rmse
            if pre_rmse > max(1.0, float(np.max(np.abs(target)))) * 1e-10
            else None
        )
        return {
            **record,
            "state": "READY",
            "weights": weights.tolist(),
            "synthetic": synthetic.tolist(),
            "pre_rmse": pre_rmse,
            "post_rmse": post_rmse,
            "post_pre_rmse_ratio": ratio,
            "ratio_state": (
                "FINITE" if ratio is not None else "PRE_ERROR_NEAR_ZERO_RATIO_UNDEFINED"
            ),
            "post_observed_minus_synthetic": gaps[pre:].tolist(),
            "mean_post_gap": float(np.mean(gaps[pre:])),
        }

    fitted = evaluate(panel[:, 0], panel[:, 1:])
    result["fit"] = fitted
    if fitted["state"] != "READY":
        return {**result, "reason": fitted["reason"]}
    placebos = []
    for index, identity in enumerate(identities[1:], start=1):
        controls = [i for i in range(1, len(identities)) if i != index]
        placebo = evaluate(panel[:, index], panel[:, controls])
        placebos.append({"unit_id": identity, **placebo})
    result.update(
        state="READY",
        periods=periods,
        donor_weights=dict(zip(identities[1:], fitted["weights"])),
        placebos=placebos,
        placebo_comparison={
            "eligible_n": sum(p["state"] == "READY" for p in placebos),
            "p_value": None,
            "reason": "OBSERVATIONAL_PLACEBOS_DO_NOT_ESTABLISH_RANDOMIZED_ASSIGNMENT",
        },
    )
    return result


def _statistics_schedule(data):
    """G158 official OR-Tools CP-SAT optional-task portfolio and finite-slot scheduling."""
    import re
    from datetime import datetime, timedelta, timezone
    from ortools.sat.python import cp_model
    import ortools

    required = {
        "tasks",
        "resource_ids",
        "budget_minor",
        "currency",
        "benefit_unit",
        "start_at",
        "slot_minutes",
        "horizon",
        "required_coverage",
        "mandatory_tasks",
        "prerequisites",
        "exclusions",
    }
    if not isinstance(data, dict) or set(data) != required:
        raise ValueError("STATISTICS_SCHEDULE_INPUT_INVALID")
    for key, lower, upper in (
        ("budget_minor", 0, 10**12),
        ("slot_minutes", 1, 1440),
        ("horizon", 1, 10000),
    ):
        if type(data[key]) is not int or not lower <= data[key] <= upper:
            raise ValueError("STATISTICS_SCHEDULE_INTEGER_UNITS_REQUIRED")
    if (
        not isinstance(data["currency"], str)
        or re.fullmatch(r"[A-Z]{3}", data["currency"]) is None
        or not isinstance(data["benefit_unit"], str)
        or not data["benefit_unit"].strip()
    ):
        raise ValueError("STATISTICS_SCHEDULE_UNITS_REQUIRED")
    try:
        origin = datetime.fromisoformat(data["start_at"])
        if origin.utcoffset() != timedelta(0) or origin.second or origin.microsecond:
            raise ValueError()
        origin = origin.astimezone(timezone.utc)
        origin + timedelta(minutes=data["horizon"] * data["slot_minutes"])
    except (ValueError, TypeError, AttributeError, OverflowError) as exc:
        raise ValueError("STATISTICS_SCHEDULE_UTC_ORIGIN_REQUIRED") from exc

    def identifiers(values, maximum):
        if (
            not isinstance(values, list)
            or len(values) > maximum
            or any(not isinstance(x, str) or not x.strip() for x in values)
            or len(values) != len(set(values))
        ):
            raise ValueError("STATISTICS_SCHEDULE_IDENTIFIERS_INVALID")
        return values

    resources = identifiers(data["resource_ids"], 50)
    required_coverage = identifiers(data["required_coverage"], 50)
    mandatory = identifiers(data["mandatory_tasks"], 50)
    tasks = data["tasks"]
    if not resources or not isinstance(tasks, list) or not 1 <= len(tasks) <= 50:
        raise ValueError("STATISTICS_SCHEDULE_TASKS_REQUIRED")
    by_id = {}
    for row in tasks:
        if (
            not isinstance(row, dict)
            or set(row)
            != {
                "id",
                "cost_minor",
                "benefit",
                "duration",
                "earliest_start",
                "latest_end",
                "resources",
                "coverage",
            }
            or not isinstance(row["id"], str)
            or not row["id"].strip()
            or row["id"] in by_id
        ):
            raise ValueError("STATISTICS_SCHEDULE_TASK_INVALID")
        for key, lower, upper in (
            ("cost_minor", 0, 10**12),
            ("benefit", 0, 10**9),
            ("duration", 1, data["horizon"]),
            ("earliest_start", 0, data["horizon"]),
            ("latest_end", 1, data["horizon"]),
        ):
            if type(row[key]) is not int or not lower <= row[key] <= upper:
                raise ValueError("STATISTICS_SCHEDULE_TASK_INTEGER_INVALID")
        if row["earliest_start"] + row["duration"] > row["latest_end"]:
            raise ValueError("STATISTICS_SCHEDULE_TASK_WINDOW_INVALID")
        used = identifiers(row["resources"], 50)
        identifiers(row["coverage"], 50)
        if not used or not set(used).issubset(resources):
            raise ValueError("STATISTICS_SCHEDULE_RESOURCE_INVALID")
        by_id[row["id"]] = row
    if not set(mandatory).issubset(by_id):
        raise ValueError("STATISTICS_SCHEDULE_MANDATORY_UNKNOWN")
    relations = {}
    for key in ("prerequisites", "exclusions"):
        pairs = data[key]
        if (
            not isinstance(pairs, list)
            or len(pairs) > 500
            or any(
                not isinstance(pair, list)
                or len(pair) != 2
                or any(not isinstance(v, str) or v not in by_id for v in pair)
                or pair[0] == pair[1]
                for pair in pairs
            )
        ):
            raise ValueError("STATISTICS_SCHEDULE_RELATIONS_INVALID")
        relations[key] = pairs
    model = cp_model.CpModel()
    selected, starts, ends = {}, {}, {}
    intervals = {resource: [] for resource in resources}
    for identity, row in by_id.items():
        chosen = model.new_bool_var("selected_" + identity)
        start = model.new_int_var(
            row["earliest_start"],
            row["latest_end"] - row["duration"],
            "start_" + identity,
        )
        end = model.new_int_var(
            row["earliest_start"] + row["duration"],
            row["latest_end"],
            "end_" + identity,
        )
        interval = model.new_optional_interval_var(
            start, row["duration"], end, chosen, "interval_" + identity
        )
        selected[identity], starts[identity], ends[identity] = chosen, start, end
        for resource in row["resources"]:
            intervals[resource].append(interval)
    for group in intervals.values():
        model.add_no_overlap(group)
    model.add(
        sum(selected[k] * row["cost_minor"] for k, row in by_id.items())
        <= data["budget_minor"]
    )
    for identity in mandatory:
        model.add(selected[identity] == 1)
    for segment in required_coverage:
        model.add(
            sum(selected[k] for k, row in by_id.items() if segment in row["coverage"])
            >= 1
        )
    for before, after in relations["prerequisites"]:
        model.add(selected[after] <= selected[before])
        model.add(ends[before] <= starts[after]).only_enforce_if(selected[after])
    for first, second in relations["exclusions"]:
        model.add(selected[first] + selected[second] <= 1)
    model.maximize(sum(selected[k] * row["benefit"] for k, row in by_id.items()))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 10.0
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 20261017
    status = solver.solve(model)
    result = {
        "method": "ortools-cp-sat-budgeted-resource-schedule@1",
        "state": "INSUFFICIENT",
        "n": len(tasks),
        "unit": data["benefit_unit"],
        "currency": data["currency"],
        "cost_unit": "currency minor units",
        "solver": {
            "library": "ortools",
            "version": ortools.__version__,
            "status": solver.status_name(status),
            "time_limit_seconds": 10,
            "workers": 1,
            "seed": 20261017,
        },
        "limitations": [
            "Costs/benefits are explicitly supplied integers; no silent rounding or expected-sales inference.",
            "Coverage is declared segment-set coverage, not verified audience reach or population representation.",
            "Resources have capacity one; fixed task durations and finite UTC time slots are assumed.",
            "Prerequisite selection implies prerequisite completion before dependent start; exclusions prohibit both selections.",
            "Only proven optimal solutions are recommended. No publishing, booking, creator commitment or traffic allocation occurs.",
        ],
    }
    if status == cp_model.INFEASIBLE:
        return {**result, "reason": "DECLARED_SCHEDULE_CONSTRAINTS_INFEASIBLE"}
    if status != cp_model.OPTIMAL:
        return {**result, "reason": "SCHEDULE_OPTIMALITY_NOT_PROVEN_WITHIN_LIMIT"}
    chosen = {identity for identity in by_id if solver.value(selected[identity])}
    plan = []
    for identity in sorted(chosen):
        row = by_id[identity]
        start, end = solver.value(starts[identity]), solver.value(ends[identity])
        plan.append(
            {
                "id": identity,
                "start_slot": start,
                "end_slot": end,
                "starts_at": (
                    origin + timedelta(minutes=start * data["slot_minutes"])
                ).isoformat(),
                "ends_at": (
                    origin + timedelta(minutes=end * data["slot_minutes"])
                ).isoformat(),
                "cost_minor": row["cost_minor"],
                "benefit": row["benefit"],
                "resources": row["resources"],
                "coverage": row["coverage"],
            }
        )
    total_cost = sum(row["cost_minor"] for row in plan)
    benefit = sum(row["benefit"] for row in plan)
    covered = {segment for row in plan for segment in row["coverage"]}
    valid = (
        total_cost <= data["budget_minor"]
        and set(mandatory).issubset(chosen)
        and set(required_coverage).issubset(covered)
    )
    times = {row["id"]: row for row in plan}
    for row in plan:
        raw = by_id[row["id"]]
        valid &= (
            raw["earliest_start"] <= row["start_slot"]
            and row["end_slot"] <= raw["latest_end"]
            and row["end_slot"] - row["start_slot"] == raw["duration"]
        )
    for i, first in enumerate(plan):
        for second in plan[i + 1 :]:
            if set(first["resources"]) & set(second["resources"]):
                valid &= (
                    first["end_slot"] <= second["start_slot"]
                    or second["end_slot"] <= first["start_slot"]
                )
    for before, after in relations["prerequisites"]:
        if after in chosen:
            valid &= (
                before in chosen
                and times[before]["end_slot"] <= times[after]["start_slot"]
            )
    valid &= all(not ({a, b} <= chosen) for a, b in relations["exclusions"])
    valid &= (
        abs(solver.objective_value - benefit) <= 1e-6
        and abs(solver.best_objective_bound - benefit) <= 1e-6
    )
    if not valid:
        return {**result, "reason": "SCHEDULE_INDEPENDENT_FEASIBILITY_CHECK_FAILED"}
    result.update(
        state="READY",
        schedule=plan,
        total_cost_minor=total_cost,
        objective=benefit,
        best_bound=solver.best_objective_bound,
        covered_segments=sorted(covered),
        independent_feasibility_check="PASS",
        start_at=origin.isoformat(),
        slot_minutes=data["slot_minutes"],
    )
    return result
