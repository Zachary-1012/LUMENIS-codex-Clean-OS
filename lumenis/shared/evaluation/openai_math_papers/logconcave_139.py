"""Family 139: Admissible / gibbsDensity / firstOrderReply on QUADRATIC potentials.

This is the exact-rational quadratic subfamily V(x)=x^T A x/2, I<=A<=2I.
It is NOT the general measurable-oracle subpolynomial-query sampler.
"""

from decimal import localcontext
from fractions import Fraction

from .core import Budget, MathInputError, decimal, rat, rational_matrix


def positive_semidefinite(matrix, b: Budget):
    # Exact rational Schur-complement elimination, including singular PSD boundary.
    M = [row[:] for row in matrix]
    while M:
        b.tick()
        if any(M[i][i] < 0 for i in range(len(M))):
            return False
        p = next((i for i in range(len(M)) if M[i][i] > 0), None)
        if p is None:
            return not any(v for row in M for v in row)
        ix = [i for i in range(len(M)) if i != p]
        pivot = M[p][p]
        M = [[b.rational(M[i][j] - M[i][p] * M[p][j] / pivot) for j in ix] for i in ix]
    return True


def quadratic_reply(hessian, point, b: Budget):
    A = rational_matrix(hessian, max_dim=20)
    d = len(A)
    if (
        not d
        or any(len(row) != d for row in A)
        or any(A[i][j] != A[j][i] for i in range(d) for j in range(d))
    ):
        raise MathInputError("SYMMETRIC_SQUARE_HESSIAN_REQUIRED")
    if not isinstance(point, list) or len(point) != d:
        raise MathInputError("POINT_DIMENSION")
    low = [[A[i][j] - (1 if i == j else 0) for j in range(d)] for i in range(d)]
    high = [[(2 if i == j else 0) - A[i][j] for j in range(d)] for i in range(d)]
    if not positive_semidefinite(low, b) or not positive_semidefinite(high, b):
        raise MathInputError("PAPER_GLOBAL_HESSIAN_BOUNDS_FAIL")
    x = [rat(z) for z in point]
    gradient = [
        b.rational(sum((a * z for a, z in zip(row, x)), Fraction(0))) for row in A
    ]
    v = b.rational(sum((a * z for a, z in zip(x, gradient)), Fraction(0)) / 2)
    with localcontext() as ctx:
        ctx.prec = 60
        density = (-decimal(v)).exp()
    return {
        "state": "COMPUTED",
        "V": v,
        "gradient": gradient,
        "unnormalized_gibbs_density": density,
        "admissible_subfamily": "constant rational Hessian, C2, V(0)=0, grad V(0)=0, I<=A<=2I",
        "oracle_calls": 1,
        "density_is_numerical": True,
        "sampler_claim": "NOT_IMPLEMENTED_GENERAL_QUERY_ALGORITHM",
        "paper_scope": "definitions of normalized potential and first-order reply, not theorem complexity",
    }
