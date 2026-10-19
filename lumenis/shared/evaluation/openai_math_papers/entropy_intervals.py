"""Independent rational enclosure for 113's log expressions at exact marginals.

This uses the classical atanh log series, not an unpublished OpenAI algorithm.
The analytic tail is bounded before any decimal display; no floating-point or
Decimal logarithm is used as a proof of enclosure. It does not prove the paper.
"""

from fractions import Fraction

from .core import Budget, MathInputError


def log_interval(q: Fraction, b: Budget, terms: int = 48):
    q = b.rational(q)
    if q <= 0:
        raise MathInputError("LOG_POSITIVE_ARGUMENT_REQUIRED")
    # q = 2**k * y with 1 <= y < 2; |(y-1)/(y+1)| <= 1/3.
    k = q.numerator.bit_length() - q.denominator.bit_length()
    scale = b.rational(Fraction(2**k) if k >= 0 else Fraction(1, 2 ** (-k)))
    y = b.rational(q / scale)
    if y < 1:
        k -= 1
        y = b.rational(y * 2)

    def series(z):
        # Check every intermediate, not only the final interval: the series
        # powers can grow far beyond the size of the admitted input rational.
        t = b.rational(b.rational(z - 1) / b.rational(z + 1))
        t_squared = b.rational(t * t)
        p, s = t, Fraction(0)
        for i in range(terms):
            term = b.rational(b.rational(2 * p) / (2 * i + 1))
            s = b.rational(s + term)
            p = b.rational(p * t_squared)
        tail_numerator = b.rational(2 * abs(p))
        tail_denominator = b.rational(
            (2 * terms + 1) * b.rational(1 - t_squared)
        )
        tail = b.rational(tail_numerator / tail_denominator)
        return b.rational(s - tail), b.rational(s + tail)

    lo, hi = series(y)
    l2, h2 = series(Fraction(2))
    low_shift, high_shift = (l2, h2) if k >= 0 else (h2, l2)
    return (
        b.rational(lo + b.rational(k * low_shift)),
        b.rational(hi + b.rational(k * high_shift)),
    )


def entropy_interval(probabilities, b: Budget):
    lo, hi = Fraction(0), Fraction(0)
    for p in probabilities:
        p = b.rational(p)
        if not 0 <= p <= 1:
            raise MathInputError("PROBABILITY_RANGE")
        if p:
            a, z = log_interval(p, b)
            lo = b.rational(lo - b.rational(p * z))
            hi = b.rational(hi - b.rational(p * a))
    return lo, hi


def matching_bounds_intervals(marginals, law, m, b: Budget):
    f = entropy_interval(marginals, b)
    complement = entropy_interval([b.rational(1 - p) for p in marginals], b)
    h = entropy_interval(law, b)
    coefficient = (
        b.rational(Fraction(2) - b.rational(Fraction(2, m)))
        if m else Fraction(0)
    )
    lower = max(
        Fraction(0), b.rational(f[0] - b.rational(coefficient * complement[1]))
    )
    upper = f[1]

    def bounds(v):
        return {"lower": v[0], "upper": v[1], "width": b.rational(v[1] - v[0])}

    return {
        "F": bounds(f),
        "B": bounds(complement),
        "provided_law_entropy": bounds(h),
        "maximum_entropy_outer_bounds": {"lower": lower, "upper": upper},
        "method": "exact-rational atanh series, 48 terms, explicit analytic remainder",
        "scope": "numeric enclosure of expressions; theorem applicability from feasible matching mixture",
        "formal_paper_replay": "NOT_PERFORMED",
    }
