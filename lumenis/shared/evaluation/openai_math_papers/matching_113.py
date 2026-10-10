"""Family 113 DIRECT equation ports.

Sources: 01-introduction.tex intro:H, intro:FB, intro:main-bound;
03-entropy.tex ent:gibbs, ent:tilt-entropy, covariance K.
The support enumerator is a bounded implementation choice, NOT MatchingFPRAS.
Decimal transcendental values are numerical, not Lean-certified intervals.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction

from .core import Budget, MathInputError, decimal, integer, rat


@dataclass(frozen=True)
class Graph:
    vertices: int
    edges: tuple[tuple[int, int], ...]

    @staticmethod
    def read(value):
        from .core import strict_keys

        strict_keys(value, {"vertices", "edges"})
        n = integer(value["vertices"], 0, 24)
        if n % 2:
            raise MathInputError("EVEN_VERTEX_COUNT_REQUIRED")
        if not isinstance(value["edges"], list) or len(value["edges"]) > 256:
            raise MathInputError("EDGE_LIMIT")
        edges = []
        for e in value["edges"]:
            if not isinstance(e, list) or len(e) != 2:
                raise MathInputError("EDGE_SHAPE")
            u, v = integer(e[0], 0, n - 1), integer(e[1], 0, n - 1)
            if u == v:
                raise MathInputError("LOOPS_NOT_PERMITTED_BY_PAPER")
            edges.append((min(u, v), max(u, v)))
        # Keep parallel occurrences: the paper distinguishes them as coordinates.
        return Graph(n, tuple(edges))

    def check(self, matching):
        if (
            not isinstance(matching, (list, tuple))
            or len(matching) != self.vertices // 2
        ):
            return False
        seen = set()
        used = set()
        for e in matching:
            if type(e) is not int or not 0 <= e < len(self.edges) or e in used:
                return False
            u, v = self.edges[e]
            if u in seen or v in seen:
                return False
            used.add(e)
            seen.update((u, v))
        return len(seen) == self.vertices


def enumerate_matchings(g: Graph, b: Budget):
    adjacency = [[] for _ in range(g.vertices)]
    for i, (u, v) in enumerate(g.edges):
        adjacency[u].append((i, v))
        adjacency[v].append((i, u))
    found = []

    def walk(mask, chosen):
        b.tick()
        if mask == 0:
            found.append(tuple(sorted(chosen)))
            b.size(len(found))
            return
        u = (mask & -mask).bit_length() - 1
        for e, v in adjacency[u]:
            b.tick()
            if mask & (1 << v):
                walk(mask ^ (1 << u) ^ (1 << v), chosen + (e,))

    walk((1 << g.vertices) - 1, ())
    return tuple(sorted(found))


def _entropy(probabilities):
    # 0 log 0 = 0, natural logarithms, as in intro:FB.
    return -sum((p * p.ln() for p in probabilities if p), Decimal(0))


def entropy_bounds(g: Graph, means: list[Decimal]):
    with localcontext() as c:
        c.prec = 60
        if g.vertices == 0:
            return {
                "F": Decimal(0),
                "B": Decimal(0),
                "H_lower": Decimal(0),
                "H_upper": Decimal(0),
            }
        if len(means) != len(g.edges) or any(x < 0 or x > 1 for x in means):
            raise MathInputError("MARGINAL_RANGE")
        f = _entropy(means)
        comp = _entropy([1 - x for x in means])
        m = Decimal(g.vertices // 2)
        return {
            "F": f,
            "B": comp,
            "H_lower": max(Decimal(0), f - (2 - 2 / m) * comp),
            "H_upper": f,
            "scope": "maximum entropy among laws with THESE feasible edge marginals",
            "not_claimed": "lower bound on the entropy of an arbitrary supplied law",
        }


def gibbs(g: Graph, theta, b: Budget, *, covariance=False):
    if not isinstance(theta, list) or len(theta) != len(g.edges):
        raise MathInputError("THETA_SHAPE")
    exact = [rat(v) for v in theta]
    if any(abs(t) > 1000 for t in exact):
        raise MathInputError("NUMERICAL_THETA_BUDGET")
    support = enumerate_matchings(g, b)
    if not support:
        return {
            "state": "INFEASIBLE",
            "matching_count": 0,
            "distribution": [],
            "theorem_applicable": False,
            "reason": "NO_PERFECT_MATCHING",
        }
    with localcontext() as c:
        c.prec = 60
        scores = [decimal(sum((exact[e] for e in m), Fraction(0))) for m in support]
        shift = max(scores)
        w = [(s - shift).exp() for s in scores]
        z = sum(w, Decimal(0))
        p = [x / z for x in w]
        logz = shift + z.ln()
        mu = []
        for e in range(len(g.edges)):
            b.tick(len(support))
            indices = [i for i, m in enumerate(support) if e in m]
            # Structural endpoints are exact; don't manufacture >1 from a rounded sum.
            mu.append(
                Decimal(0)
                if not indices
                else Decimal(1)
                if len(indices) == len(support)
                else sum((p[i] for i in indices), Decimal(0))
            )
        h = _entropy(p)
        bounds = entropy_bounds(g, mu)
        result = {
            "state": "COMPUTED",
            "support": support,
            "matching_count": len(support),
            "distribution": p,
            "marginals": mu,
            "log_partition": logz,
            "entropy": h,
            "entropy_dual": logz
            - sum((decimal(exact[e]) * mu[e] for e in range(len(exact))), Decimal(0)),
            "entropy_bounds": bounds,
            "map_matching": support[max(range(len(scores)), key=scores.__getitem__)],
            "scope": "finite COMPLETE matching support; numerical ent:gibbs at its own mean",
            "complexity": "enumerative; NOT the general-graph FPRAS",
            "proof_status": "FORMAL_REPLAY_NOT_PERFORMED",
        }
        if covariance:
            if len(g.edges) > 64:
                raise MathInputError("COVARIANCE_DIMENSION_LIMIT")
            K = []
            for e in range(len(g.edges)):
                row = []
                for f in range(len(g.edges)):
                    b.tick(len(support))
                    row.append(
                        sum(
                            (p[i] for i, m in enumerate(support) if e in m and f in m),
                            Decimal(0),
                        )
                        - mu[e] * mu[f]
                    )
                K.append(row)
            result["covariance"] = K
        return result


def bounds_from_mixture(g: Graph, mixture: list, b: Budget):
    if not isinstance(mixture, list) or not mixture or len(mixture) > b.max_items:
        raise MathInputError("EXPLICIT_FEASIBLE_MIXTURE_REQUIRED")
    probs = []
    exact_mu = [Fraction(0) for _ in g.edges]
    atoms = {}
    mass = Fraction(0)
    for item in mixture:
        if (
            type(item) is not dict
            or set(item) != {"matching", "probability"}
            or not g.check(item["matching"])
        ):
            raise MathInputError("INVALID_MATCHING_MIXTURE")
        b.tick()
        q = rat(item["probability"])
        if q < 0:
            raise MathInputError("NEGATIVE_PROBABILITY")
        mass = b.rational(mass + q)
        key = tuple(sorted(item["matching"]))
        atoms[key] = b.rational(atoms.get(key, Fraction(0)) + q)
        for e in key:
            exact_mu[e] = b.rational(exact_mu[e] + q)
        probs.append(q)
    if sum(probs) != 1:
        raise MathInputError("MIXTURE_MASS_NOT_ONE")
    from .entropy_intervals import matching_bounds_intervals

    enclosures = matching_bounds_intervals(
        exact_mu, list(atoms.values()), g.vertices // 2, b
    )
    with localcontext() as c:
        c.prec = 60
        return {
            "state": "COMPUTED",
            "feasibility_witness": "explicit convex mixture of valid matchings",
            "exact_marginals": exact_mu,
            "provided_law_entropy": _entropy([decimal(q) for q in atoms.values()]),
            "maximum_entropy_bounds": entropy_bounds(g, [decimal(q) for q in exact_mu]),
            "numerical_status": "DECIMAL_60_DIGITS_NOT_DIRECTED_INTERVALS",
            "rational_enclosures": enclosures,
        }
