"""Port of UniqueGamesTheorem.Foundations.Target definitions, NOT its hardness proof.

Parallel constraint occurrences retain multiplicity. No weighted/max-cut substitutions.
"""

from fractions import Fraction

from .core import Budget, MathInputError, integer


def check_instance(vertices, alphabet, constraints, labeling, b: Budget):
    n = integer(vertices, 1, 128)
    q = integer(alphabet, 1, 256)
    if not isinstance(constraints, list) or not 1 <= len(constraints) <= 4096:
        raise MathInputError("NONEMPTY_CONSTRAINTS_REQUIRED")
    if not isinstance(labeling, list) or len(labeling) != n:
        raise MathInputError("LABELING_SIZE")
    lab = [integer(x, 0, q - 1) for x in labeling]
    satisfied = []
    failed = []
    for idx, e in enumerate(constraints):
        b.tick()
        if type(e) is not dict or set(e) != {"source", "target", "images"}:
            raise MathInputError("CONSTRAINT_FIELDS")
        u, v = integer(e["source"], 0, n - 1), integer(e["target"], 0, n - 1)
        if not isinstance(e["images"], list) or len(e["images"]) != q:
            raise MathInputError("PERMUTATION_SIZE")
        perm = [integer(x, 0, q - 1) for x in e["images"]]
        if set(perm) != set(range(q)):
            raise MathInputError("NONBIJECTIVE_PERMUTATION")
        (satisfied if perm[lab[u]] == lab[v] else failed).append(idx)
    return {
        "state": "EVALUATED",
        "count_satisfied": len(satisfied),
        "constraint_occurrences": len(constraints),
        "value": Fraction(len(satisfied), len(constraints)),
        "violated_indices": failed,
        "paper_symbols": ["Constraint.satisfied", "countSatisfied"],
        "claim_scope": "evaluation of one finite labeling, NOT Unique Games reduction/approximation theorem",
    }
