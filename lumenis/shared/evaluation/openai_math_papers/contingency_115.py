"""Family 115: exact ports of D_XY, offset-count, first-success and residual-integers.

Source: build/sections/algorithms.tex at pinned fd4a..., equations named in functions.
Complete dense/small-chain theorem algorithm is NOT implemented. Finite support
enumeration below is transparent and bounded; no polynomial-time claim follows.
"""

from __future__ import annotations

import secrets
from fractions import Fraction

from .core import Budget, MathInputError, integer, rat


def translate_completion(delta_rows, delta_cols, reference_row=0, reference_col=0):
    """Paper's displayed D_XY matrix, including singleton rows/columns."""
    if not isinstance(delta_rows, list) or not isinstance(delta_cols, list):
        raise MathInputError("DELTA_SHAPE")
    r = [integer(x, -(10**9), 10**9) for x in delta_rows]
    c = [integer(x, -(10**9), 10**9) for x in delta_cols]
    if not r or not c or max(len(r), len(c)) > 64 or sum(r) != sum(c):
        raise MathInputError("DELTA_TOTAL_MISMATCH")
    i0 = integer(reference_row, 0, len(r) - 1)
    j0 = integer(reference_col, 0, len(c) - 1)
    d = [[0] * len(c) for _ in r]
    for i in range(len(r)):
        if i != i0:
            d[i][j0] = r[i]
    for j in range(len(c)):
        if j != j0:
            d[i0][j] = c[j]
    d[i0][j0] = r[i0] - sum(c[j] for j in range(len(c)) if j != j0)
    return d


def offset_counts(width: int, bits: int, b: Budget):
    """eq:offset-count numerators, denominator 2^bits. Not rounded probabilities."""
    width = integer(width, 1, b.max_items)
    bits = integer(bits, 0, min(4096, b.max_bits))
    v = 1 << bits

    def up(a):
        return (a + width - 1) // width

    return [up((u + 1) * v) - up(u * v) for u in range(width)]


def first_success_law(success, repeats: int, fallback: int, b: Budget):
    """eq:outer-geometric-law; success masses sum <=1, not conditional probabilities."""
    if not isinstance(success, list) or not success:
        raise MathInputError("SUCCESS_MASS_SHAPE")
    b.size(len(success))
    g = [rat(x) for x in success]
    repeats = integer(repeats, 0, 256)
    fallback = integer(fallback, 0, len(g) - 1)
    if any(x < 0 for x in g) or sum(g) > 1:
        raise MathInputError("INVALID_SUCCESS_MASSES")
    fail = 1 - sum(g)
    power = Fraction(1)
    series = Fraction(0)
    for _ in range(repeats):
        series = b.rational(series + power)
        power = b.rational(power * fail)
    out = [b.rational(x * series) for x in g]
    out[fallback] = b.rational(out[fallback] + power)
    return {
        "law": out,
        "all_failed_mass": power,
        "failed_each_trial": fail,
        "formula": "eq:outer-geometric-law",
    }


def residual_law(numerators, R: int, D: int, b: Budget):
    """eq:residual-integers n_z=2^(R+D)-M(2^D-1)a_z.

    Validate domination directly. No claim that an arbitrary proposal is the paper p_k.
    """
    if not isinstance(numerators, list) or not numerators:
        raise MathInputError("DYADIC_PROPOSAL_REQUIRED")
    M = len(numerators)
    b.size(M)
    R = integer(R, 0, 2048)
    D = integer(D, 1, 2048)
    if R + D + M.bit_length() > b.max_bits:
        raise MathInputError("RESIDUAL_BIT_LIMIT")
    a = []
    for x in numerators:
        if type(x) is not int or x < 0 or x > (1 << R):
            raise MathInputError("INVALID_PROPOSAL_NUMERATOR")
        a.append(x)
    if sum(a) != (1 << R):
        raise MathInputError("PROPOSAL_MASS_NOT_ONE")
    weights = [(1 << (R + D)) - M * ((1 << D) - 1) * v for v in a]
    if any(n < 0 for n in weights):
        raise MathInputError("POINTWISE_DOMINATION_NOT_SATISFIED")
    denom = M * (1 << R)
    if sum(weights) != denom:
        raise ArithmeticError("RESIDUAL_NORMALIZATION_FAILED")
    delta = Fraction(1, 1 << D)
    mix = [
        b.rational((1 - delta) * Fraction(v, 1 << R) + delta * Fraction(n, denom))
        for v, n in zip(a, weights)
    ]
    if any(v != Fraction(1, M) for v in mix):
        raise ArithmeticError("EXACT_MIXTURE_IDENTITY_FAILED")
    return {
        "weights": weights,
        "denominator": denom,
        "delta": delta,
        "mixture_law": mix,
        "target_law": [Fraction(1, M)] * M,
        "formula": "eq:residual-integers",
        "upstream_outer_chain_reproduced": False,
    }


def exact_randbelow(n: int, b: Budget, rng=None):
    # The paper's rejection sampler. A timeout produces no sample, never biased fallback.
    rng = rng or secrets.SystemRandom()
    if type(n) is not int or n < 1 or n.bit_length() > b.max_bits:
        raise MathInputError("DRAW_RANGE")
    if n == 1:
        return 0
    bits = (n - 1).bit_length()
    while True:
        b.tick()
        v = rng.getrandbits(bits)
        if v < n:
            return v


def draw_weights(weights, b: Budget, rng=None):
    total = sum(weights)
    v = exact_randbelow(total, b, rng)
    for i, w in enumerate(weights):
        b.tick()
        v -= w
        if v < 0:
            return i
    raise ArithmeticError("WEIGHT_SELECTION_FAILED")


def corrected_index(numerators, R: int, D: int, b: Budget, rng=None):
    law = residual_law(numerators, R, D, b)
    rng = rng or secrets.SystemRandom()
    b.tick()
    correction = rng.getrandbits(D) == 0
    idx = draw_weights(law["weights"] if correction else numerators, b, rng)
    return {
        "index": idx,
        "correction_branch": correction,
        "support_size": len(numerators),
        "uniformity": "exact in the unbounded ideal unbiased-bit model; deadline may censor runs",
        "bounded_completion_conditioning": "NO_UNIFORMITY_GUARANTEE_CONDITIONAL_ON_COMPLETING_WITHIN_RESOURCE_CUTOFF",
        "algorithm_scope": "paper residual-mixture equation for supplied fully tabulated law",
    }


def table_space(rows, columns, b: Budget, upper=None):
    """Explicit finite table enumeration allowed in prop:law-tabulation, NOT the FPRAS."""
    if (
        not isinstance(rows, list)
        or not isinstance(columns, list)
        or not rows
        or not columns
        or max(len(rows), len(columns)) > 8
    ):
        raise MathInputError("TABLE_DIMENSION_LIMIT")
    r = [integer(x, 0, 200) for x in rows]
    c = [integer(x, 0, 200) for x in columns]
    if sum(r) != sum(c):
        raise MathInputError("MARGINS_HAVE_DIFFERENT_TOTALS")
    m, n = len(r), len(c)
    if upper is None:
        u = [[min(r[i], c[j]) for j in range(n)] for i in range(m)]
    else:
        if (
            not isinstance(upper, list)
            or len(upper) != m
            or any(not isinstance(v, list) or len(v) != n for v in upper)
        ):
            raise MathInputError("CELL_BOUND_SHAPE")
        u = [[integer(v, 0, 200) for v in row] for row in upper]
    found = []
    current = [0] * (m * n)
    rr = r[:]
    cc = c[:]

    def walk(pos):
        b.tick()
        if pos == m * n:
            if not any(rr) and not any(cc):
                found.append(
                    tuple(tuple(current[i * n : (i + 1) * n]) for i in range(m))
                )
                b.size(len(found))
            return
        i, j = divmod(pos, n)
        high = min(rr[i], cc[j], u[i][j])
        low = max(
            0,
            rr[i] - sum(u[i][k] for k in range(j + 1, n)),
            cc[j] - sum(u[k][j] for k in range(i + 1, m)),
        )
        for val in range(low, high + 1):
            b.tick()
            rr[i] -= val
            cc[j] -= val
            current[pos] = val
            if (j != n - 1 or rr[i] == 0) and (i != m - 1 or cc[j] == 0):
                walk(pos + 1)
            rr[i] += val
            cc[j] += val

    walk(0)
    return found


def sample_finite_tables(rows, columns, b: Budget, upper=None):
    support = table_space(rows, columns, b, upper)
    if not support:
        return {"state": "INFEASIBLE", "count": 0}
    M = len(support)
    D = 2
    R = max(1, (M - 1).bit_length()) + D + 1
    a = offset_counts(M, R, b)
    draw = corrected_index(a, R, D, b)
    return {
        "state": "SAMPLED",
        "table": support[draw["index"]],
        "count": M,
        "draw": draw,
        "proposal": "finite index offset-count law; NOT paper dense/small-state sampler",
        "complexity": "bounded exhaustive support, may be exponential",
        "output_role": "synthetic constrained configuration, never missing observed data",
    }


def paper_outer_parameters(d: int, bits: int, k: int):
    # Exact disclosed schedule: never silently replace d^200 with an arbitrary small loop.
    d = integer(d, 14, 10000)
    bits = integer(bits, d, 100000)
    k = integer(k, 1, 100000)
    return {
        "J_o": d**4 * (k + 1),
        "T": d**200 * (k + bits) ** 2,
        "h": d**4 * (k + bits) ** 2,
        "formula": "eq:outer-parameters",
        "execution": "NOT_IMPLEMENTED_FULL_CHAIN",
    }
