"""Family 140: PosteriorReplicas.rowGram/liftLabel/kernelComponent/baseFiber.

Exact rational row projection; numerical square roots for the spherical map.
NOT the streaming lower-bound theorem, not a KV-cache theorem, not causal inference.
"""

from __future__ import annotations

import secrets
from decimal import localcontext
from fractions import Fraction

from .core import (
    Budget,
    MathInputError,
    decimal,
    integer,
    rat,
    rational_matrix,
    solve_square,
)


def project(rows, labels, point, b: Budget):
    A = rational_matrix(rows, max_dim=24)
    if not isinstance(point, list):
        raise MathInputError("POINT_REQUIRED")
    d = integer(len(point), 1, 24)
    k = len(A)
    if k >= d or any(len(a) != d for a in A):
        raise MathInputError("INDEPENDENT_FEWER_ROWS_THAN_DIMENSION_REQUIRED")
    if not isinstance(labels, list) or len(labels) != k:
        raise MathInputError("LABEL_SHAPE")
    y = [rat(v) for v in labels]
    x = [rat(v) for v in point]
    G = [
        [b.rational(sum((a * z for a, z in zip(ai, aj)), Fraction(0))) for aj in A]
        for ai in A
    ]

    def lift(v):
        co = solve_square(G, v, b)
        return [
            b.rational(sum((co[i] * A[i][j] for i in range(k)), Fraction(0)))
            for j in range(d)
        ]

    mean = lift(y)
    Ax = [b.rational(sum((a * z for a, z in zip(row, x)), Fraction(0))) for row in A]
    projected = lift(Ax)
    kernel = [b.rational(x[j] - projected[j]) for j in range(d)]
    mean_labels = [
        b.rational(sum((a * z for a, z in zip(row, mean)), Fraction(0))) for row in A
    ]
    kernel_labels = [
        b.rational(sum((a * z for a, z in zip(row, kernel)), Fraction(0))) for row in A
    ]
    if mean_labels != y or any(kernel_labels):
        raise ArithmeticError("PROJECTION_CERTIFICATE_FAILED")
    radius2 = b.rational(1 - sum((v * v for v in mean), Fraction(0)))
    return {
        "state": "COMPUTED",
        "row_gram": G,
        "lift_label": mean,
        "kernel_component": kernel,
        "exact_row_checks": {"A_lift_equals_y": True, "A_kernel_equals_zero": True},
        "sphere_radius_squared": radius2,
        "dimension": d,
        "observed_rows": k,
        "paper_definitions": ["rowGram", "liftLabel", "kernelComponent"],
        "claim_scope": "rational finite-input projection identity; no lower-bound inference",
    }


def fiber_point(rows, labels, point, b: Budget, base="gaussian"):
    if base not in {"gaussian", "spherical"}:
        raise MathInputError("BASE_LAW")
    out = project(rows, labels, point, b)
    m = out["lift_label"]
    z = out["kernel_component"]
    if base == "gaussian":
        out["fiber_point"] = [b.rational(a + u) for a, u in zip(m, z)]
        out["arithmetic"] = (
            "exact rational transform; distribution requires supplied point ~ N(0,I)"
        )
    else:
        if out["sphere_radius_squared"] < 0:
            raise MathInputError("SPHERICAL_LABEL_OUTSIDE_SUPPORT")
        norm2 = sum((v * v for v in z), Fraction(0))
        if norm2 == 0:
            raise MathInputError("KERNEL_POINT_ZERO_NO_UNIFORM_DIRECTION")
        with localcontext() as c:
            c.prec = 60
            scale = (decimal(out["sphere_radius_squared"]) / decimal(norm2)).sqrt()
            out["fiber_point"] = [decimal(a) + scale * decimal(u) for a, u in zip(m, z)]
        out["arithmetic"] = (
            "Decimal60 spherical transform; no exact-distribution bit guarantee"
        )
    out["paper_definition"] = "PosteriorReplicas.baseFiber"
    out["output_role"] = (
        "conditional mathematical hypothesis, not recovered source fact"
    )
    return out


def draw_fiber(rows, labels, dimension, b: Budget, base="gaussian"):
    d = integer(dimension, 1, 24)
    rng = secrets.SystemRandom()
    # Finite-precision independent normal draws. Do NOT call these exact Gaussian samples.
    x = [str(rng.gauss(0, 1)) for _ in range(d)]
    out = fiber_point(rows, labels, x, b, base)
    out["randomness"] = (
        "SystemRandom normal floating approximation; no TV/error theorem claimed"
    )
    return out
