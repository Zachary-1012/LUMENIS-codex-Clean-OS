"""MeanPayoff.Game/play/meanPayoff: exact eventually-periodic positional play.

This is NOT the paper's randomized quasipolynomial winning-set algorithm.
"""

from fractions import Fraction

from .core import Budget, MathInputError, integer


def positional_play(game, start, max_policy, min_policy, b: Budget):
    if type(game) is not dict or set(game) != {"vertices", "max_owner", "edges"}:
        raise MathInputError("GAME_FIELDS")
    n = integer(game["vertices"], 1, 512)
    owners = game["max_owner"]
    edges = game["edges"]
    if (
        not isinstance(owners, list)
        or len(owners) != n
        or any(type(x) is not bool for x in owners)
    ):
        raise MathInputError("OWNER_VECTOR")
    if not isinstance(edges, list) or not 1 <= len(edges) <= 4096:
        raise MathInputError("EDGE_LIST")
    es = []
    adj = [[] for _ in range(n)]
    for i, e in enumerate(edges):
        if not isinstance(e, list) or len(e) != 3:
            raise MathInputError("EDGE_SHAPE")
        u, v, w = (
            integer(e[0], 0, n - 1),
            integer(e[1], 0, n - 1),
            integer(e[2], -(10**9), 10**9),
        )
        es.append((u, v, w))
        adj[u].append(i)
    if any(not a for a in adj):
        raise MathInputError("PAPER_TOTAL_GAME_REQUIRED")
    for p in (max_policy, min_policy):
        if not isinstance(p, list) or len(p) != n:
            raise MathInputError("POSITIONAL_POLICY_SHAPE")
    for v in range(n):
        p = max_policy if owners[v] else min_policy
        e = integer(p[v], 0, len(es) - 1)
        if es[e][0] != v:
            raise MathInputError("POLICY_EDGE_WRONG_TAIL")
    seen = {}
    path = []
    vertex = integer(start, 0, n - 1)
    while vertex not in seen:
        b.tick()
        seen[vertex] = len(path)
        edge = (max_policy if owners[vertex] else min_policy)[vertex]
        path.append(edge)
        vertex = es[edge][1]
    cut = seen[vertex]
    cycle = path[cut:]
    value = Fraction(sum(es[e][2] for e in cycle), len(cycle))
    return {
        "state": "COMPUTED",
        "prefix_edges": path[:cut],
        "cycle_edges": cycle,
        "liminf_mean_payoff": value,
        "nonnegative_for_this_strategy_pair": value >= 0,
        "winning_for_all_opponents": "NOT_EVALUATED",
        "paper_symbols": ["Game", "play", "meanPayoff"],
        "qp_algorithm": "NOT_IMPLEMENTED",
    }
