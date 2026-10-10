"""MatrixMultiplication.Arithmetic Gate.eval/Program.eval/MatrixAlgorithm.Correct port.

Registers use the Lean convention: register 0 is the most recently created value.
Exact rational sparse polynomials verify one supplied division-free program.
This neither constructs the paper's asymptotic algorithm nor accelerates GEMM.
"""

from fractions import Fraction

from .core import Budget, MathInputError, integer, rat


def verify_matrix_program(a, b, c, gates, outputs, budget: Budget):
    a = integer(a, 1, 4)
    b = integer(b, 1, 4)
    c = integer(c, 1, 4)
    if not isinstance(gates, list) or len(gates) > 2048:
        raise MathInputError("PROGRAM_LIMIT")
    if (
        not isinstance(outputs, list)
        or len(outputs) != a
        or any(not isinstance(x, list) or len(x) != c for x in outputs)
    ):
        raise MathInputError("OUTPUT_MATRIX")
    registers = []
    cost = 0

    def atom(side, i, j):
        if side == "A":
            integer(i, 0, a - 1)
            integer(j, 0, b - 1)
            return i * b + j
        if side == "B":
            integer(i, 0, b - 1)
            integer(j, 0, c - 1)
            return a * b + i * c + j
        raise MathInputError("MATRIX_INPUT_SIDE")

    def combine(p, q, subtract=False, multiply=False):
        out = {} if multiply else dict(p)
        if multiply:
            for x, u in p.items():
                for y, v in q.items():
                    budget.tick()
                    mon = tuple(sorted(x + y))
                    if len(mon) > 16:
                        raise MathInputError("POLYNOMIAL_DEGREE_BUDGET")
                    out[mon] = budget.rational(out.get(mon, Fraction(0)) + u * v)
                    if not out[mon]:
                        del out[mon]
                    budget.size(len(out))
        else:
            for x, v in q.items():
                budget.tick()
                out[x] = budget.rational(
                    out.get(x, Fraction(0)) + (-v if subtract else v)
                )
                if not out[x]:
                    del out[x]
                budget.size(len(out))
        return out

    for gate in gates:
        budget.tick()
        if not isinstance(gate, list) or not gate:
            raise MathInputError("GATE_FORMAT")
        op = gate[0]
        if op == "constant" and len(gate) == 2:
            q = rat(gate[1])
            poly = {(): q} if q else {}
        elif op == "input" and len(gate) == 4:
            poly = {(atom(gate[1], gate[2], gate[3]),): Fraction(1)}
        elif op in {"add", "sub", "mul"} and len(gate) == 3:
            x, y = (
                integer(gate[1], 0, len(registers) - 1),
                integer(gate[2], 0, len(registers) - 1),
            )
            poly = combine(
                registers[x], registers[y], subtract=op == "sub", multiply=op == "mul"
            )
            cost += 1
        else:
            raise MathInputError("UNKNOWN_OR_MALFORMED_DIVISION_FREE_GATE")
        registers.insert(0, poly)
    differences = []
    for i in range(a):
        for k in range(c):
            idx = integer(outputs[i][k], 0, len(registers) - 1)
            target = {
                tuple(sorted((i * b + j, a * b + j * c + k))): Fraction(1)
                for j in range(b)
            }
            delta = combine(registers[idx], target, subtract=True)
            if delta:
                differences.append(
                    {
                        "output": [i, k],
                        "nonzero_coefficients": [
                            {"monomial": m, "coefficient": v}
                            for m, v in sorted(delta.items())
                        ],
                    }
                )
    return {
        "state": "IDENTITY_VERIFIED" if not differences else "IDENTITY_REJECTED",
        "arithmetic_gate_cost": cost,
        "registers": len(registers),
        "differences": differences,
        "verification_domain": "all rational A,B of the supplied fixed dimensions via polynomial coefficients",
        "cost_model": "add/sub/mul each cost one, input/constant zero; not bit cost",
        "register_order": "index zero newest as Program.eval Fin.cases",
        "paper_exponent_bound": "NOT_IMPLEMENTED_OR_BENCHMARKED",
    }
