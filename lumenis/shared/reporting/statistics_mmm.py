"""Optional finite CPU Bayesian MMM implementation inside Reporting.

Sources, authorization and SavedWork remain in business_brief and their original owners.
"""

from __future__ import annotations
import re
from .statistics_methods import _statistics_numbers


def _mmm_diagnostics(summary, parameter_sizes):
    """Validate every scalar diagnostic before aggregation; no skip-NaN success."""
    import numpy as np

    expected = [label for name, size in parameter_sizes.items()
                for label in ([name] if size is None else [f"{name}[{i}]" for i in range(size)])]
    failures = []
    if (not summary.index.is_unique or set(summary.index) != set(expected)
            or not {"r_hat", "ess_bulk"}.issubset(summary.columns)):
        return {"max_rhat": None, "min_ess_bulk": None,
                "diagnostic_failures": [{"reason": "REQUIRED_PARAMETER_DIAGNOSTICS_MISSING_OR_DUPLICATED"}]}
    values = []
    for name in expected:
        try:
            rhat, ess = (float(summary.loc[name, key]) for key in ("r_hat", "ess_bulk"))
        except (TypeError, ValueError, OverflowError):
            failures.append({"parameter": name, "reason": "DIAGNOSTICS_NOT_NUMERIC"})
            continue
        if not np.isfinite([rhat, ess]).all():
            failures.append({"parameter": name, "reason": "DIAGNOSTICS_NOT_FINITE"})
            continue
        values.append((rhat, ess))
        if rhat <= 0 or rhat > 1.05 or ess < 200:
            failures.append({"parameter": name, "reason": "DIAGNOSTICS_THRESHOLD_NOT_PASSED"})
    complete = len(values) == len(expected) and bool(values)
    return {"max_rhat": max(v[0] for v in values) if complete else None,
            "min_ess_bulk": min(v[1] for v in values) if complete else None,
            "diagnostic_failures": failures}


def _statistics_mmm(data):
    """G151 finite Bayesian geometric-adstock/Michaelis-Menten MMM on quarterly data.

    CPU-only NUTS estimates a specified statistical model, not an owned LLM.
    Declared financial units/scope/proxy assumptions remain visible. No causal ROI.
    """
    import numpy as np

    allowed_fields = {"periods", "currency", "outcome_unit", "filing_entity", "disclosure_scope",
                      "spend_basis", "budget", "region", "macro_controls", "_resolved_macro_controls",
                      "observation_frequency", "original_observation_count", "transformation"}
    if not isinstance(data, dict) or set(data) - allowed_fields:
        raise ValueError("STATISTICS_MMM_UNSUPPORTED_DATA_FIELDS")
    periods = data.get("periods")
    if (
        not isinstance(periods, list)
        or len(periods) > 200
        or not isinstance(data.get("currency"), str)
        or not re.fullmatch(r"[A-Z]{3}", data["currency"])
        or not isinstance(data.get("outcome_unit"), str)
        or not data["outcome_unit"].strip()
        or not isinstance(data.get("filing_entity"), str)
        or not data["filing_entity"].strip()
        or data.get("disclosure_scope") not in {"group", "brand", "store"}
        or data.get("spend_basis") not in {"reported", "public_proxy", "user_declared"}
    ):
        raise ValueError("STATISTICS_MMM_DATASET_INVALID")
    if any(not isinstance(row, dict) for row in periods):
        raise ValueError("STATISTICS_MMM_PERIOD_INVALID")
    controls = data.get("_resolved_macro_controls", [])
    if "macro_controls" in data or not isinstance(controls, list) or len(controls) > 3:
        raise ValueError("STATISTICS_MMM_CONTROLS_REQUIRE_SOURCE_OWNER")
    if controls and data.get("region") != "CN-national":
        raise ValueError("STATISTICS_MMM_CONTROL_REGION_MISMATCH")
    control_metrics = set()
    for control in controls:
        if (not isinstance(control, dict) or not isinstance(control.get("metric"), str)
                or control.get("metric") in control_metrics
                or not isinstance(control.get("periods"), list)
                or any(not isinstance(row, dict) for row in control["periods"])):
            raise ValueError("STATISTICS_MMM_CONTROL_INVALID")
        control_metrics.add(control.get("metric"))
        unit = {"cpi_yoy_percent": "percent_yoy", "retail_sales": "CNY",
                "domestic_tourism_trips": "person_trips", "domestic_tourism_spend": "CNY"}.get(control.get("metric"))
        if (unit is None or control.get("unit") != unit
                or control.get("region") != data.get("region")
                or [r.get("period") for r in control.get("periods", [])]
                != [r.get("period") for r in periods]):
            raise ValueError("STATISTICS_MMM_CONTROL_ALIGNMENT_INVALID")
    if len({c.get("as_of") for c in controls}) > 1:
        raise ValueError("STATISTICS_MMM_CONTROL_VINTAGE_MISMATCH")
    channels = None
    serial = []
    x, y = [], []
    for row in periods:
        if (
            not isinstance(row, dict)
            or set(row) != {"period", "outcome", "spend"}
            or not isinstance(row["period"], str)
            or not re.fullmatch(r"[12][0-9]{3}-Q[1-4]", row["period"])
            or not isinstance(row["spend"], dict)
            or not 1 <= len(row["spend"]) <= 6
            or any(not isinstance(key, str) or not key.strip() for key in row["spend"])
        ):
            raise ValueError("STATISTICS_MMM_PERIOD_INVALID")
        channels = sorted(row["spend"]) if channels is None else channels
        if set(row["spend"]) != set(channels):
            raise ValueError("STATISTICS_MMM_CHANNELS_CHANGED")
        _statistics_numbers([row["outcome"], *row["spend"].values()], minimum=2)
        if row["outcome"] < 0 or any(v < 0 for v in row["spend"].values()):
            raise ValueError("STATISTICS_MMM_NEGATIVE_AMOUNT")
        serial.append(int(row["period"][:4]) * 4 + int(row["period"][-1]) - 1)
        x.append([row["spend"][c] for c in channels])
        y.append(row["outcome"])
    if any(serial[i] - serial[i - 1] != 1 for i in range(1, len(serial))):
        raise ValueError("STATISTICS_MMM_NONCONTIGUOUS_QUARTERS")
    result = {
        "method": "bayesian-geometric-michaelis-menten-mmm@1",
        "state": "INSUFFICIENT",
        "n": len(periods),
        "currency": data["currency"],
        "unit": data["outcome_unit"],
        "filing_entity": data["filing_entity"],
        "disclosure_scope": data["disclosure_scope"],
        "spend_basis": data["spend_basis"],
        "roi_state": "NOT_ESTABLISHED",
        "limitations": [
            "Declared source dataset; unit/scope integrity is not independent verification of financial truth.",
            "Public spend proxies can contain measurement error; this model does not correct that error.",
            "Nonnegative additive channel model with finite geometric carryover and concave saturation.",
            "No causal identification, omitted-confounder correction, profit ROI or group-to-brand allocation.",
            "Zero pre-window carryover assumed; at most eight prior quarters contribute.",
        ],
    }
    # Retained source bytes establish custody, not the observational frequency.
    # Keep declaration/independence separate; labels alone never verify quarters.
    frequency = data.get("observation_frequency")
    original_count = data.get("original_observation_count")
    construction = data.get("transformation")
    if frequency is not None and (not isinstance(frequency, str) or frequency not in {"quarter", "annual", "month", "monthly", "week", "weekly", "day", "daily"}):
        raise ValueError("STATISTICS_MMM_OBSERVATION_FREQUENCY_INVALID")
    if original_count is not None and (type(original_count) is not int or original_count < 0):
        raise ValueError("STATISTICS_MMM_ORIGINAL_OBSERVATION_COUNT_INVALID")
    if construction is not None and (not isinstance(construction, str) or not construction.strip()):
        raise ValueError("STATISTICS_MMM_TRANSFORMATION_INVALID")
    result.update(
        declared_period_count=len(periods),
        declared_original_observation_count=original_count,
        verified_independent_observation_count=None,
        observation_frequency=frequency,
        observation_frequency_verification="NOT_INDEPENDENTLY_VERIFIED",
        period_construction=construction,
    )
    result["limitations"].append(
        "Quarter labels and row count are declared inputs, not verified independent observations. "
        "Missing source frequency/construction remains unverified; model fit cannot establish it."
    )
    # Fail closed for explicit disaggregation, contradictory source frequency or
    # unsupported transformations. This is a positive construction allowlist,
    # not an attempt to detect arbitrary falsification by keyword matching.
    if original_count is not None and original_count < len(periods):
        return {**result, "reason": "RESAMPLED_PERIODS_NOT_INDEPENDENT"}
    if frequency is not None and frequency != "quarter":
        return {**result, "reason": "SOURCE_FREQUENCY_REQUIRES_VERIFIED_QUARTER_AGGREGATION"}
    if construction is not None and construction not in {"reported", "none"}:
        return {**result, "reason": "PERIOD_CONSTRUCTION_NOT_VERIFIED"}
    if original_count is not None and original_count != len(periods):
        return {**result, "reason": "ORIGINAL_OBSERVATION_COUNT_MISMATCH"}
    if controls:
        result["method"] = "bayesian-geometric-michaelis-menten-mmm-with-macro@2"
        result["macro_controls"] = controls
        result["control_interpretation"] = (
            "National contextual covariates with declared national outcome geography; "
            "CPI is the mean of monthly year-on-year rates, not quarter-on-quarter inflation. "
            "Capture-as-of is not a historical release-time reconstruction; holdout evaluation "
            "is conditional on observed covariates and is not an ex-ante forecast."
        )
        if any(c.get("state") != "AVAILABLE" for c in controls):
            return {**result, "reason": "MACRO_CONTROL_QUARTERS_UNAVAILABLE"}
    if len(periods) < 12:
        return {**result, "reason": "NEED_AT_LEAST_12_REAL_QUARTERS"}
    split = len(periods) - max(4, int(len(periods) * 0.2))
    if split < 12:
        return {**result, "reason": "NEED_12_TRAIN_AND_4_DISJOINT_TEST_QUARTERS"}
    # Reject invalid constraints before any expensive posterior sampling.
    budget = data.get("budget")
    if budget is not None:
        if not isinstance(budget, dict) or set(budget) != {"total", "lower", "upper"}:
            raise ValueError("STATISTICS_MMM_BUDGET_INVALID")
        _statistics_numbers([budget["total"]], minimum=1)
        if (
            budget["total"] < 0
            or not isinstance(budget["lower"], dict)
            or not isinstance(budget["upper"], dict)
            or set(budget["lower"]) != set(channels)
            or set(budget["upper"]) != set(channels)
        ):
            raise ValueError("STATISTICS_MMM_BUDGET_INVALID")
        lower, upper = [budget["lower"][c] for c in channels], [
            budget["upper"][c] for c in channels
        ]
        _statistics_numbers(lower, minimum=len(channels))
        _statistics_numbers(upper, minimum=len(channels))
        if any(lo < 0 or hi < lo for lo, hi in zip(lower, upper)) or not sum(
            lower
        ) <= budget["total"] <= sum(upper):
            raise ValueError("STATISTICS_MMM_BUDGET_INFEASIBLE")
    x, y = np.asarray(x, float), np.asarray(y, float)
    if np.any(np.std(x[:split], axis=0) <= 1e-10) or np.std(y[:split]) <= 1e-10:
        return {**result, "reason": "NO_TRAINING_CHANNEL_OR_OUTCOME_VARIATION"}
    scale = x[:split].mean(axis=0)
    if np.any(scale <= 0):
        return {**result, "reason": "CHANNEL_SCALE_NOT_ESTIMABLE"}
    ymean, yscale = float(y[:split].mean()), float(y[:split].std())
    scaled = x / scale
    lag_count = min(8, split)
    lagged = np.zeros((len(x), len(channels), lag_count))
    for lag in range(lag_count):
        lagged[lag:, :, lag] = scaled[: len(x) - lag]
    time = (np.arange(len(x)) - (split - 1) / 2) / split
    seasonal = np.column_stack(
        [
            np.sin(2 * np.pi * np.arange(len(x)) / 4),
            np.cos(2 * np.pi * np.arange(len(x)) / 4),
        ]
    )
    control_matrix = None
    control_means = control_scales = None
    if controls:
        allowed_aggregation = {
            "cpi_yoy_percent": {"arithmetic-mean-monthly-yoy-percent"},
            "retail_sales": {"sum-complete-monthly-totals", "explicit-reported-quarter-total"},
            "domestic_tourism_trips": {"explicit-reported-quarter-total"},
            "domestic_tourism_spend": {"explicit-reported-quarter-total"},
        }
        for control in controls:
            if any(row.get("state") != "AVAILABLE"
                   or row.get("aggregation") not in allowed_aggregation[control["metric"]]
                   for row in control["periods"]):
                raise ValueError("STATISTICS_MMM_CONTROL_AGGREGATION_INVALID")
        try:
            values = np.array([[float(c["periods"][i]["value"]) for c in controls]
                               for i in range(len(periods))], dtype=float)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("STATISTICS_MMM_CONTROL_VALUES_INVALID") from exc
        if not np.isfinite(values).all():
            raise ValueError("STATISTICS_MMM_CONTROL_VALUES_INVALID")
        control_means, control_scales = values[:split].mean(axis=0), values[:split].std(axis=0)
        if np.any(control_scales <= 1e-10):
            return {**result, "reason": "NO_TRAINING_MACRO_CONTROL_VARIATION"}
        control_matrix = (values - control_means) / control_scales
        design = np.column_stack([np.ones(split), time[:split], seasonal[:split], control_matrix[:split]])
        if np.linalg.matrix_rank(design) < design.shape[1]:
            return {**result, "reason": "MACRO_CONTROL_DESIGN_NOT_IDENTIFIABLE"}
    import pymc as pm
    import pytensor.tensor as pt
    import arviz as az

    with pm.Model() as model:
        alpha = pm.Beta("adstock_alpha", 2, 2, shape=len(channels))
        half = pm.LogNormal("half_saturation", 0, 0.5, shape=len(channels))
        beta = pm.HalfNormal("channel_beta", 1, shape=len(channels))
        intercept = pm.Normal("intercept", 0, 1)
        trend = pm.Normal("trend", 0, 0.5)
        season = pm.Normal("season", 0, 0.5, shape=2)
        sigma = pm.HalfNormal("sigma", 1)
        weights = alpha[:, None] ** np.arange(lag_count)[None, :]
        adstock = (
            pt.sum(lagged * weights[None, :, :], axis=2)
            / pt.sum(weights, axis=1)[None, :]
        )
        contribution = beta[None, :] * adstock / (half[None, :] + adstock)
        mu = (
            intercept
            + trend * time
            + pt.dot(seasonal, season)
            + pt.sum(contribution, axis=1)
        )
        if control_matrix is not None:
            control_beta = pm.Normal("macro_control_beta", 0, 0.5, shape=len(controls))
            control_contribution = pt.dot(control_matrix, control_beta)
            mu = mu + control_contribution
            pm.Deterministic("macro_control_contribution", yscale * control_matrix * control_beta)
        pm.Deterministic("expected_outcome", ymean + yscale * mu)
        pm.Deterministic("channel_contribution", yscale * contribution)
        pm.Normal(
            "observed",
            mu=mu[:split],
            sigma=sigma,
            observed=(y[:split] - ymean) / yscale,
        )
        trace = pm.sample(
            draws=500,
            tune=750,
            chains=2,
            cores=1,
            random_seed=20261017,
            target_accept=0.95,
            progressbar=False,
            compute_convergence_checks=True,
        )
    parameters = [
        "adstock_alpha",
        "half_saturation",
        "channel_beta",
        "intercept",
        "trend",
        "season",
        "sigma",
    ]
    if controls:
        parameters.append("macro_control_beta")
    # Raw precision is necessary at the acceptance thresholds.
    summary = az.summary(trace, var_names=parameters, round_to="none")
    parameter_sizes = {name: (len(channels) if name in {"adstock_alpha", "half_saturation", "channel_beta"}
                             else 2 if name == "season" else len(controls) if name == "macro_control_beta"
                             else None) for name in parameters}
    diagnostics = _mmm_diagnostics(summary, parameter_sizes)
    divergences = int(trace.sample_stats["diverging"].sum())
    result["sampling"] = {
        "library": "pymc",
        "version": pm.__version__,
        "chains": 2,
        "cores": 1,
        "draws_per_chain": 500,
        "tune_per_chain": 750,
        "seed": 20261017,
        "target_accept": 0.95,
        "divergences": divergences,
        **diagnostics,
    }
    result["priors"] = {
        "adstock_alpha": "Beta(2,2)",
        "half_saturation": "LogNormal(0,0.5)",
        "channel_beta": "HalfNormal(1)",
        "intercept": "Normal(0,1)",
        "trend_and_season": "Normal(0,0.5)",
        "sigma": "HalfNormal(1)",
        "scaling": "training channel means and training outcome standard deviation",
    }
    if controls:
        result["priors"]["macro_control_beta"] = "Normal(0,0.5); signed additive standardized contextual effect"
        result["control_scaling"] = {
            "basis": "training partition only", "train_n": split,
            "means": control_means.tolist(), "standard_deviations": control_scales.tolist(),
        }
    if diagnostics["diagnostic_failures"] or divergences:
        return {**result, "reason": "POSTERIOR_DIAGNOSTICS_NOT_PASSED"}

    def draws(name):
        array = np.asarray(trace.posterior[name])
        return array.reshape((-1, *array.shape[2:]))

    expected = draws("expected_outcome")
    sigma_draws = draws("sigma") * yscale
    rng = np.random.default_rng(20261017)
    posterior_predictive = (
        expected + rng.normal(size=expected.shape) * sigma_draws[:, None]
    )
    predictions = expected.mean(axis=0)
    intervals = np.quantile(posterior_predictive, [0.025, 0.975], axis=0).T
    errors = predictions[split:] - y[split:]
    nonzero = y[split:] != 0
    contribution_draws = draws("channel_contribution")
    contribution_summary = np.quantile(
        contribution_draws[:, :split].mean(axis=1), [0.025, 0.5, 0.975], axis=0
    ).T
    result.update(
        state="READY",
        train_n=split,
        test_n=len(y) - split,
        channels=[
            {
                "id": channel,
                "mean_quarter_contribution_interval": contribution_summary[i].tolist(),
            }
            for i, channel in enumerate(channels)
        ],
        holdout={
            "periods": [p["period"] for p in periods[split:]],
            "prediction": predictions[split:].tolist(),
            "predictive_intervals_95": intervals[split:].tolist(),
            "mae": float(np.abs(errors).mean()),
            "mape": (
                float(np.mean(np.abs(errors / y[split:]))) if np.all(nonzero) else None
            ),
            "mape_reason": None if np.all(nonzero) else "ZERO_OUTCOME_DENOMINATOR",
            "coverage": float(
                np.mean(
                    (y[split:] >= intervals[split:, 0])
                    & (y[split:] <= intervals[split:, 1])
                )
            ),
        },
    )
    if controls:
        coefficient = draws("macro_control_beta") * yscale / control_scales
        bounds = np.quantile(coefficient, [0.025, 0.5, 0.975], axis=0).T
        result["macro_control_coefficients"] = [
            {"metric": c["metric"], "unit": data["outcome_unit"] + " per " + c["unit"],
             "posterior_interval_95_and_median": bounds[i].tolist(),
             "causal_claim": "NOT_ESTABLISHED"}
            for i, c in enumerate(controls)
        ]
    budget = data.get("budget")
    if budget is not None:
        from scipy.optimize import minimize

        betas, halves = draws("channel_beta") * yscale, draws("half_saturation")

        def utility(amount):
            normalized = amount / scale
            return np.mean(np.sum(betas * normalized / (halves + normalized), axis=1))

        initial = np.array(lower) + (budget["total"] - sum(lower)) * (
            np.array(upper) - lower
        ) / max(1e-12, sum(upper) - sum(lower))
        optimized = minimize(
            lambda amount: -utility(amount),
            initial,
            method="SLSQP",
            bounds=list(zip(lower, upper)),
            constraints={
                "type": "eq",
                "fun": lambda amount: sum(amount) - budget["total"],
            },
            options={"maxiter": 500, "ftol": 1e-9},
        )
        if not optimized.success or abs(sum(optimized.x) - budget["total"]) > 1e-5:
            result["budget_scenario"] = {
                "state": "INSUFFICIENT",
                "reason": "OPTIMIZATION_NOT_CONVERGED",
            }
        else:
            allocation = optimized.x
            normalized = allocation / scale
            derivatives = betas * halves / (halves + normalized) ** 2 / scale
            result["budget_scenario"] = {
                "state": "READY",
                "currency": data["currency"],
                "allocation": dict(zip(channels, allocation.tolist())),
                "objective": float(utility(allocation)),
                "marginal_outcome_per_currency_intervals": dict(
                    zip(
                        channels,
                        np.quantile(
                            derivatives, [0.025, 0.5, 0.975], axis=0
                        ).T.tolist(),
                    )
                ),
                "assumption": "Hypothetical steady-state spend, normalized geometric carryover; positive concave posterior response. Not a spending action or causal ROI.",
            }
    return result
