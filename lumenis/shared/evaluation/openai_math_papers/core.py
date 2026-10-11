"""Infrastructure only, not attributed as a mathematical contribution."""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal, localcontext
from fractions import Fraction
from typing import Any


class MathInputError(ValueError):
    pass


class ResourceBound(RuntimeError):
    pass


@dataclass
class Budget:
    seconds: float = 20.0
    max_steps: int = 200_000
    max_items: int = 10_000
    max_bits: int = 8192
    cancelled: Callable[[], bool] | None = None
    _start: float = field(default_factory=time.monotonic, init=False)
    steps: int = field(default=0, init=False)

    def __post_init__(self):
        if not 0 < self.seconds <= 120 or not 1 <= self.max_steps <= 2_000_000:
            raise MathInputError("INVALID_EXECUTION_BUDGET")
        if not 1 <= self.max_items <= 100_000 or not 64 <= self.max_bits <= 32768:
            raise MathInputError("INVALID_STORAGE_BUDGET")

    def tick(self, amount: int = 1):
        self.steps += amount
        if self.cancelled and self.cancelled():
            raise ResourceBound("CANCELLED")
        if self.steps > self.max_steps:
            raise ResourceBound("OPERATION_BUDGET_EXCEEDED")
        if time.monotonic() - self._start > self.seconds:
            raise ResourceBound("DEADLINE_EXCEEDED")

    def size(self, n: int):
        self.tick()
        if n > self.max_items:
            raise ResourceBound("ENUMERATION_BUDGET_EXCEEDED")

    def rational(self, v: Fraction):
        self.tick()
        if (
            max(abs(v.numerator).bit_length(), v.denominator.bit_length())
            > self.max_bits
        ):
            raise ResourceBound("EXACT_ARITHMETIC_BIT_BUDGET_EXCEEDED")
        return v

    def receipt(self):
        return {
            "operations": self.steps,
            "elapsed_seconds": time.monotonic() - self._start,
            "cooperative_deadline_seconds": self.seconds,
            "deadline_enforcement": "CHECKED_AT_BUDGET_TICKS_NOT_OS_PREEMPTION",
            "limits_applied": True,
        }


def integer(v: Any, lo: int = 0, hi: int = 10**9) -> int:
    if type(v) is not int or not lo <= v <= hi:
        raise MathInputError("INTEGER_OUT_OF_RANGE")
    return v


def rat(v: Any) -> Fraction:
    # No float-to-fact coercion and no executable expressions.
    if type(v) is int:
        if v.bit_length() > 4096:
            raise MathInputError("RATIONAL_TOO_LARGE")
        return Fraction(v)
    if isinstance(v, Fraction):
        if max(abs(v.numerator).bit_length(), v.denominator.bit_length()) > 4096:
            raise MathInputError("RATIONAL_TOO_LARGE")
        return v
    if type(v) is str and 0 < len(v) <= 512:
        # Bound the exponent BEFORE Fraction constructs a potentially huge integer.
        literal = re.fullmatch(
            r"[-+]?(?:[0-9]+/[0-9]+|(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE]([-+]?[0-9]{1,4}))?)",
            v,
        )
        if literal is None or (
            literal.group(1) is not None and abs(int(literal.group(1))) > 1024
        ):
            raise MathInputError("INVALID_OR_OVERSIZED_RATIONAL_LITERAL")
        try:
            q = Fraction(v)
        except (ValueError, ZeroDivisionError, OverflowError) as e:
            raise MathInputError("INVALID_RATIONAL") from e
        if max(abs(q.numerator).bit_length(), q.denominator.bit_length()) > 4096:
            raise MathInputError("RATIONAL_TOO_LARGE")
        return q
    raise MathInputError("RATIONAL_REQUIRES_INTEGER_OR_EXACT_STRING")


def decimal(v: Any) -> Decimal:
    q = rat(v)
    with localcontext() as c:
        c.prec = 60
        return Decimal(q.numerator) / Decimal(q.denominator)


def strict_keys(obj: dict, required: set[str], optional: set[str] = frozenset()):
    if (
        type(obj) is not dict
        or not required <= obj.keys()
        or set(obj) - required - optional
    ):
        raise MathInputError("INVALID_FIELDS")


def wire(x: Any):
    if isinstance(x, Fraction):
        return f"{x.numerator}/{x.denominator}"
    if isinstance(x, Decimal):
        return str(x)
    if isinstance(x, dict):
        return {str(k): wire(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [wire(v) for v in x]
    if isinstance(x, float) and not math.isfinite(x):
        raise MathInputError("NONFINITE_OUTPUT")
    return x


def digest(x: Any):
    return hashlib.sha256(
        json.dumps(
            wire(x),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def rational_matrix(x: Any, *, max_dim=24):
    if not isinstance(x, list) or len(x) > max_dim:
        raise MathInputError("MATRIX_SIZE")
    n = len(x[0]) if x else 0
    if n > max_dim or any(not isinstance(r, list) or len(r) != n for r in x):
        raise MathInputError("RAGGED_MATRIX")
    return [[rat(v) for v in row] for row in x]


def solve_square(a: list[list[Fraction]], y: list[Fraction], b: Budget):
    n = len(a)
    if len(y) != n or any(len(r) != n for r in a):
        raise MathInputError("SQUARE_SYSTEM_REQUIRED")
    m = [list(r) + [y[i]] for i, r in enumerate(a)]
    for j in range(n):
        pivot = next((i for i in range(j, n) if m[i][j]), None)
        if pivot is None:
            raise MathInputError("SINGULAR_GRAM_MATRIX")
        m[j], m[pivot] = m[pivot], m[j]
        z = m[j][j]
        m[j] = [b.rational(v / z) for v in m[j]]
        for i in range(n):
            if i == j:
                continue
            z = m[i][j]
            if z:
                m[i] = [b.rational(u - z * v) for u, v in zip(m[i], m[j])]
    return [m[i][-1] for i in range(n)]
