"""Authority is paper identity + exact implemented part, never a generic brand label."""

UPSTREAM_REPO = "openai/math"
UPSTREAM_COMMIT = "fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb"
REGISTRY = {
    "102": {
        "relation": "DIRECT_DEFINITION_PORT",
        "path": "lean/ComparatorChallenges/UniqueGamesTheorem.lean",
        "blob": "5e0e18daac92b039a30dc500decc576b91fddb91",
        "symbols": [
            "Foundations.Target.PermutationTable",
            "Constraint.satisfied",
            "countSatisfied",
        ],
        "implemented": "finite permutation-constraint labeling evaluation preserving multiplicities",
        "not_implemented": "hardness reductions, Unique Games theorem proof or approximation algorithm",
    },
    "103": {
        "relation": "DIRECT_FINITE_SEMANTICS_PORT",
        "path": "lean/ComparatorChallenges/LogspaceEquality.lean",
        "blob": "692a4bdc0de7de093d83abdcb7a2bb1ccb7d476b",
        "symbols": [
            "Machine.step",
            "Machine.run",
            "spaceThrough",
            "acceptanceProbability",
        ],
        "implemented": "full finite transition-table semantics within a bounded clock; exact rational coin-law",
        "not_implemented": "asymptotic log-space derandomization machine or L=RL=BPL proof",
    },
    "104": {
        "relation": "DIRECT_POSITIONAL_SPECIALIZATION",
        "path": "lean/ComparatorChallenges/RandomizedMeanPayoff.lean",
        "blob": "cc70577163b98c4489466ec919a6985ee03397f1",
        "symbols": ["Game", "play", "meanPayoff"],
        "implemented": "exact eventual-cycle liminf payoff for specified positional strategy pair",
        "not_implemented": "history-dependent universal winning set, randomized quasipolynomial algorithm",
    },
    "107": {
        "relation": "DIRECT_ARITHMETIC_MODEL_PORT",
        "path": "lean/ComparatorChallenges/MatrixMultiplication.lean",
        "blob": "877d7ee3901c51382cf5bcb059a50d8dbb3cde77",
        "symbols": [
            "Arithmetic.Gate.eval",
            "Gate.cost",
            "Program.eval",
            "MatrixAlgorithm.Correct",
        ],
        "implemented": "division-free program semantics with newest-first registers; rational symbolic identity replay",
        "not_implemented": "the 9/4 exponent construction, fast-GEMM replacement or bit-complexity claim",
    },
    "113": {
        "relation": "DIRECT_PAPER_EQUATION_PORT",
        "path": "preprints/Entropy-and-Face-Dimension-of-the-Perfect-Matching-Polytope-September-23-2026/build/sections/03-entropy.tex",
        "blob": "bf0bc368e2243f9628a8ed7ff175bd5c18f50978",
        "symbols": ["ent:gibbs", "ent:tilt-entropy", "covariance K"],
        "additional_path": "preprints/Entropy-and-Face-Dimension-of-the-Perfect-Matching-Polytope-September-23-2026/build/sections/01-introduction.tex",
        "additional_blob": "14f70966c1e972cfd314f1c610ebc6ed8d6c3f7e",
        "additional_symbols": ["intro:H", "intro:FB", "intro:main-bound"],
        "implemented": "matching Gibbs law/marginals/covariance/entropy and stated pointwise bound; exact finite support, numerical exp/log",
        "not_implemented": "general matching FPRAS, complete face geometry proof, rigorous real intervals",
    },
    "114": {
        "relation": "DIRECT_PARTITION_MATROID_SPECIALIZATION",
        "path": "lean/ComparatorChallenges/CommonBasesFPRAS.lean",
        "blob": "b03428bbdc26dbe79be12218920c3313a5df5695",
        "symbols": ["ExactOracles", "commonBaseCount"],
        "implemented": "exact common-base count for two structurally valid partition matroids of equal rank",
        "not_implemented": "general independence-oracle FPRAS or polynomial resource guarantee",
    },
    "115": {
        "relation": "DIRECT_PAPER_EQUATION_PORT_WITH_EXPLICIT_FINITE_WRAPPER",
        "path": "preprints/Exact-Uniform-Sampling-of-Contingency-Tables-with-Arbitrary-Margins-September-24-2026/build/sections/algorithms.tex",
        "blob": "878d6bf097d032795e18c38b5c8755b981b9dd13",
        "symbols": [
            "D_XY",
            "eq:offset-count",
            "eq:outer-geometric-law",
            "eq:residual-integers",
            "eq:outer-parameters",
        ],
        "implemented": "exact-rational residual correction + first-success law, translation, finite table support wrapper",
        "not_implemented": "complete dense and small-state sampler, arbitrary-margin polynomial expected-time theorem or cell-bounded FPRAS",
    },
    "139": {
        "relation": "DIRECT_QUADRATIC_SUBFAMILY",
        "path": "lean/ComparatorChallenges/LogConcaveQuery.lean",
        "blob": "bb5e705b7f6a62aee93a071473d7a06d9dc735d3",
        "symbols": ["Admissible", "gibbsDensity", "firstOrderReply"],
        "implemented": "exact admissibility and value/gradient for rational quadratic Hessians I<=A<=2I; numerical density",
        "not_implemented": "general subpolynomial-query sampler or arithmetic/bit bound",
    },
    "140": {
        "relation": "DIRECT_PROJECTION_AND_FIBER_PORT",
        "path": "lean/ComparatorChallenges/PosteriorReplicas.lean",
        "blob": "be840922beb1feff22f51fa3d0c5b1d21f2f2211",
        "symbols": ["rowGram", "liftLabel", "kernelComponent", "baseFiber"],
        "implemented": "exact rational row projections and conditional Gaussian/spherical fiber map; finite-precision random draws",
        "not_implemented": "memory/sample lower-bound proof, Gaussian equal-label integral theorem or LLM-memory theorem",
    },
}


def source_card(family):
    c = dict(REGISTRY[family])
    c["family"] = family
    c["commit"] = UPSTREAM_COMMIT
    c["url"] = f"https://github.com/{UPSTREAM_REPO}/blob/{UPSTREAM_COMMIT}/{c['path']}"
    c["upstream_authorship"] = (
        "OpenAI paper/formal specification; code implementation independently written for this package"
    )
    c["formal_replay"] = (
        "NOT_PERFORMED; ComparatorChallenges contain target statements, not automatic proof evidence"
    )
    c["production_acceptance"] = "NOT_VERIFIED"
    return c
