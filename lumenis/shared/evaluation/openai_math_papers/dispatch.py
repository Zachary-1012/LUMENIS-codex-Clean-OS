"""Bounded typed dispatch; no eval/exec/shell/network/model calls."""

from .core import Budget, MathInputError, digest, strict_keys, wire
from .provenance import source_card, assert_review

OPERATIONS = {
    "unique_games.evaluate": (
        "102",
        {"vertices", "alphabet", "constraints", "labeling"},
        set(),
    ),
    "machine.acceptance": ("103", {"machine", "word", "clock"}, set()),
    "mean_payoff.pair": ("104", {"game", "start", "max_policy", "min_policy"}, set()),
    "matrix.program_identity": ("107", {"a", "b", "c", "gates", "outputs"}, set()),
    "matching.gibbs": ("113", {"graph", "theta"}, {"covariance"}),
    "matching.entropy_bounds": ("113", {"graph", "mixture"}, set()),
    "matroid.common_bases": ("114", {"n", "first", "second"}, set()),
    "contingency.residual_law": ("115", {"numerators", "R", "D"}, set()),
    "contingency.first_success": ("115", {"success", "repeats", "fallback"}, set()),
    "contingency.translation": (
        "115",
        {"delta_rows", "delta_cols"},
        {"reference_row", "reference_col"},
    ),
    "contingency.finite_sample": ("115", {"rows", "columns"}, {"upper"}),
    "contingency.outer_parameters": ("115", {"d", "bits", "k"}, set()),
    "logconcave.quadratic_reply": ("139", {"hessian", "point"}, set()),
    "posterior.project": ("140", {"rows", "labels", "point"}, set()),
    "posterior.fiber_point": ("140", {"rows", "labels", "point"}, {"base"}),
    "posterior.draw_fiber": ("140", {"rows", "labels", "dimension"}, {"base"}),
}


def execute(request, *, budget=None, offline_review=False):
    strict_keys(request, {"operation", "parameters"})
    op = request["operation"]
    p = request["parameters"]
    if not isinstance(op, str) or op not in OPERATIONS:
        raise MathInputError("UNSUPPORTED_PAPER_OPERATION")
    family, required, optional = OPERATIONS[op]
    strict_keys(p, required, optional)
    if type(offline_review) is not bool:
        raise MathInputError("OFFLINE_REVIEW_FLAG")
    review = ({"status": "OFFLINE_PIN_REVIEW_ONLY",
               "review_revision": "fixed-source-registry-only",
               "current_withdrawal_status": "NOT_VERIFIED",
               "publishable": False} if offline_review else assert_review(family))
    b = budget or Budget()
    b.tick()
    if op == "unique_games.evaluate":
        from .unique_games_102 import check_instance

        result = check_instance(**p, b=b)
    elif op == "machine.acceptance":
        from .machine_103 import acceptance_probability

        result = acceptance_probability(**p, b=b)
    elif op == "mean_payoff.pair":
        from .games_104 import positional_play

        result = positional_play(**p, b=b)
    elif op == "matrix.program_identity":
        from .arithmetic_107 import verify_matrix_program

        result = verify_matrix_program(**p, budget=b)
    elif op.startswith("matching."):
        from .matching_113 import Graph, bounds_from_mixture, gibbs

        g = Graph.read(p["graph"])
        if op == "matching.gibbs":
            if "covariance" in p and type(p["covariance"]) is not bool:
                raise MathInputError("COVARIANCE_FLAG")
            result = gibbs(g, p["theta"], b, covariance=p.get("covariance", False))
        else:
            result = bounds_from_mixture(g, p["mixture"], b)
    elif op == "matroid.common_bases":
        from .common_bases_114 import common_bases

        result = common_bases(**p, b=b)
    elif op.startswith("contingency."):
        from . import contingency_115 as c

        if op.endswith("residual_law"):
            result = c.residual_law(**p, b=b)
        elif op.endswith("first_success"):
            result = c.first_success_law(**p, b=b)
        elif op.endswith("translation"):
            result = {"translation": c.translate_completion(**p), "formula": "D_XY"}
        elif op.endswith("finite_sample"):
            result = c.sample_finite_tables(**p, b=b)
        else:
            result = c.paper_outer_parameters(**p)
    elif op == "logconcave.quadratic_reply":
        from .logconcave_139 import quadratic_reply

        result = quadratic_reply(**p, b=b)
    else:
        from . import posterior_140 as c

        fn = {
            "posterior.project": c.project,
            "posterior.fiber_point": c.fiber_point,
            "posterior.draw_fiber": c.draw_fiber,
        }[op]
        result = fn(**p, b=b)
    b.tick()
    if not offline_review:
        assert_review(family, review)
    return wire(
        {
            "operation": op,
            "input_sha256": digest(request),
            "result": result,
            "paper": {**source_card(family), "review": review},
            "computation": b.receipt(),
            "base_math": "COMPLETED_COMPUTATION_ONLY",
            "business_outcome": "NOT_OBSERVED",
            "AI_enhancement": "NOT_CALLED",
            "full_paper_main_algorithm_reproduced": False,
            "not_fact_creation": True,
        }
    )
