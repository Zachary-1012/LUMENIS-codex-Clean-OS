"""Independent rational enclosure for 113's log expressions at exact marginals.

This uses the classical atanh log series, not an unpublished OpenAI algorithm.
The analytic tail is bounded before any decimal display; no floating-point or
Decimal logarithm is used as a proof of enclosure. It does not prove the paper.
"""

from fractions import Fraction

from .core import Budget, MathInputError


def log_interval(q: Fraction, b: Budget, terms: int = 48):
    if q <= 0:
        raise MathInputError("LOG_POSITIVE_ARGUMENT_REQUIRED")
    # q = 2**k * y with 1 <= y < 2; |(y-1)/(y+1)| <= 1/3.
    k = q.numerator.bit_length() - q.denominator.bit_length()
    scale = Fraction(2**k) if k >= 0 else Fraction(1, 2 ** (-k))
    y = q / scale
    if y < 1:
        k -= 1
        y *= 2

    def series(z):
        t = (z - 1) / (z + 1)
        p, s = t, Fraction(0)
        for i in range(terms):
            b.tick()
            s += 2 * p / (2 * i + 1)
            p *= t * t
        tail = 2 * abs(p) / ((2 * terms + 1) * (1 - t * t))
        return s - tail, s + tail

    lo, hi = series(y)
    l2, h2 = series(Fraction(2))
    return (lo + k * l2, hi + k * h2) if k >= 0 else (lo + k * h2, hi + k * l2)


def entropy_interval(probabilities, b: Budget):
    lo, hi = Fraction(0), Fraction(0)
    for p in probabilities:
        if not 0 <= p <= 1:
            raise MathInputError("PROBABILITY_RANGE")
        if p:
            a, z = log_interval(p, b)
            lo -= p * z
            hi -= p * a
    return lo, hi


def matching_bounds_intervals(marginals, law, m, b: Budget):
    f = entropy_interval(marginals, b)
    complement = entropy_interval([1 - p for p in marginals], b)
    h = entropy_interval(law, b)
    coefficient = Fraction(2) - Fraction(2, m) if m else Fraction(0)
    lower = max(Fraction(0), f[0] - coefficient * complement[1])
    upper = f[1]

    def bounds(v):
        return {"lower": v[0], "upper": v[1], "width": v[1] - v[0]}

    return {
        "F": bounds(f),
        "B": bounds(complement),
        "provided_law_entropy": bounds(h),
        "maximum_entropy_outer_bounds": {"lower": lower, "upper": upper},
        "method": "exact-rational atanh series, 48 terms, explicit analytic remainder",
        "scope": "numeric enclosure of expressions; theorem applicability from feasible matching mixture",
        "formal_paper_replay": "NOT_PERFORMED",
    }
