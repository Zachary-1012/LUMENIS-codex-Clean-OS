"""CommonBasesFPRAS.ExactOracles/commonBaseCount for two PARTITION MATROIDS.

Attribution: OpenAI/math, paper 114, ExactOracles/commonBaseCount; source identity is
pinned in lumenis.shared.evaluation.openai_math_papers.provenance.REGISTRY
at upstream fd4aeeb2ee4fc729c18d98444fed42fd0529eeeb.
This bounded Python specialization is not the full paper algorithm or proof.
Upstream paper/source rights remain separate; see LICENSING.md and the
third-party register. This header does not assert a new upstream license grant.


Independence is derived from partition capacities, not trusted arbitrary callbacks.
Exact finite enumeration; NOT the common-bases FPRAS.
"""

from collections import Counter
from itertools import combinations

from .core import Budget, MathInputError, integer


def _partition(obj, n):
    if type(obj) is not dict or set(obj) != {"groups", "capacities"}:
        raise MathInputError("PARTITION_FIELDS")
    groups = obj["groups"]
    caps = obj["capacities"]
    if (
        not isinstance(groups, list)
        or len(groups) != n
        or not isinstance(caps, list)
        or len(caps) > 32
    ):
        raise MathInputError("PARTITION_SIZE")
    cp = [integer(v, 0, n) for v in caps]
    gs = [integer(v, 0, len(cp) - 1) for v in groups]
    sizes = Counter(gs)
    rank = sum(min(sizes[k], c) for k, c in enumerate(cp))
    return gs, cp, rank


def common_bases(n, first, second, b: Budget):
    n = integer(n, 0, 32)
    g1, c1, r1 = _partition(first, n)
    g2, c2, r2 = _partition(second, n)
    if r1 != r2:
        raise MathInputError("PAPER_EQUAL_RANK_REQUIRED")
    found = []
    for subset in combinations(range(n), r1):
        b.tick()
        a = Counter(g1[i] for i in subset)
        z = Counter(g2[i] for i in subset)
        if all(a[k] <= v for k, v in enumerate(c1)) and all(
            z[k] <= v for k, v in enumerate(c2)
        ):
            found.append(subset)
            b.size(len(found))
    return {
        "state": "COMPUTED" if found else "INFEASIBLE",
        "rank": r1,
        "common_base_count": len(found),
        "bases": found,
        "oracle_validity": "structural partition matroids; exact finite capacities",
        "paper_symbols": ["ExactOracles", "commonBaseCount"],
        "complexity": "exhaustive n choose rank, NOT FPRAS",
        "invalid_extension": "arbitrary monetary budget constraints are NOT automatically matroids",
    }
