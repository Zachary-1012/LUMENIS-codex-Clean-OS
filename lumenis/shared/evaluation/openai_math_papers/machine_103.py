"""ExactDerandomization Machine.step/run/acceptanceProbability finite semantic port.

Finite clock only; no claim of L=RL=BPL algorithm or asymptotic logarithmic space.
"""

from fractions import Fraction

from .core import Budget, MathInputError, integer


def acceptance_probability(machine, word, clock, b: Budget):
    if type(machine) is not dict or set(machine) != {
        "states",
        "initial",
        "outputs",
        "input_heads",
        "work_tapes",
        "transitions",
    }:
        raise MathInputError("MACHINE_FIELDS")
    n = integer(machine["states"], 1, 64)
    initial = integer(machine["initial"], 0, n - 1)
    h = integer(machine["input_heads"], 0, 2)
    w = integer(machine["work_tapes"], 0, 2)
    T = integer(clock, 0, 24)
    if (
        not isinstance(word, list)
        or len(word) > 128
        or any(type(x) is not bool for x in word)
    ):
        raise MathInputError("BOOLEAN_WORD_REQUIRED")
    outputs = machine["outputs"]
    if (
        not isinstance(outputs, list)
        or len(outputs) != n
        or any(x is not None and type(x) is not bool for x in outputs)
    ):
        raise MathInputError("OUTPUT_TABLE")
    transitions = {}
    entries = machine["transitions"]
    if not isinstance(entries, list) or len(entries) > 10000:
        raise MathInputError("TRANSITION_LIMIT")

    def bools(x, length):
        if (
            not isinstance(x, list)
            or len(x) != length
            or any(type(z) is not bool for z in x)
        ):
            raise MathInputError("BOOL_VECTOR")
        return tuple(x)

    def directions(x, length):
        if not isinstance(x, list) or len(x) != length:
            raise MathInputError("DIRECTION_VECTOR")
        return tuple(integer(z, -1, 1) for z in x)

    for tr in entries:
        b.tick()
        if type(tr) is not dict or set(tr) != {
            "state",
            "input",
            "work",
            "coin",
            "next",
            "write",
            "input_move",
            "work_move",
        }:
            raise MathInputError("TRANSITION_FIELDS")
        syms = tr["input"]
        if (
            not isinstance(syms, list)
            or len(syms) != h
            or any(s not in ("L", "0", "1", "R") for s in syms)
        ):
            raise MathInputError("INPUT_SYMBOL")
        if type(tr["coin"]) is not bool:
            raise MathInputError("COIN_BIT")
        key = (
            integer(tr["state"], 0, n - 1),
            tuple(syms),
            bools(tr["work"], w),
            tr["coin"],
        )
        action = (
            integer(tr["next"], 0, n - 1),
            bools(tr["write"], w),
            directions(tr["input_move"], h),
            directions(tr["work_move"], w),
        )
        if key in transitions:
            raise MathInputError("DUPLICATE_TRANSITION")
        transitions[key] = action
    # Canonical finite-support work tapes: only cells containing true are retained.
    # Visit sets are part of the DP state so finite-clock space accounting is exact.
    cfg = (
        initial,
        (0,) * h,
        (0,) * w,
        tuple(() for _ in range(w)),
        tuple((0,) for _ in range(w)),
    )
    dist = {cfg: 1}
    for _ in range(T):
        nxt = {}
        for cfg, mass in dist.items():
            b.tick()
            state, ipos, wpos, tapes, visited = cfg
            if outputs[state] is not None:
                nxt[cfg] = nxt.get(cfg, 0) + 2 * mass
                continue
            ins = tuple(
                "L"
                if i == 0
                else "R"
                if i == len(word) + 1
                else ("1" if word[i - 1] else "0")
                for i in ipos
            )
            work = tuple(wpos[j] in tapes[j] for j in range(w))
            for coin in (False, True):
                key = (state, ins, work, coin)
                if key not in transitions:
                    raise MathInputError("REACHABLE_TRANSITION_UNDEFINED")
                ns, write, im, wm = transitions[key]
                nt = []
                nv = []
                np = tuple(wpos[j] + wm[j] for j in range(w))
                for j in range(w):
                    tape = set(tapes[j])
                    tape.add(wpos[j]) if write[j] else tape.discard(wpos[j])
                    nt.append(tuple(sorted(tape)))
                    nv.append(tuple(sorted(set(visited[j]) | {np[j]})))
                nc = (
                    ns,
                    tuple(
                        max(0, min(len(word) + 1, ipos[j] + im[j])) for j in range(h)
                    ),
                    np,
                    tuple(nt),
                    tuple(nv),
                )
                nxt[nc] = nxt.get(nc, 0) + mass
            b.size(len(nxt))
        dist = nxt
    accepted = sum(v for cfg, v in dist.items() if outputs[cfg[0]] is True)
    rejected = sum(v for cfg, v in dist.items() if outputs[cfg[0]] is False)
    total = 1 << T
    return {
        "state": "COMPUTED",
        "acceptance_probability": Fraction(accepted, total),
        "rejection_probability": Fraction(rejected, total),
        "unhalted_probability": Fraction(total - accepted - rejected, total),
        "all_tapes_halt_by_clock": accepted + rejected == total,
        "coin_tapes": total,
        "space_through_clock_max": max(sum(len(v) for v in cfg[4]) for cfg in dist),
        "paper_symbols": [
            "Machine.step",
            "Machine.run",
            "spaceThrough",
            "acceptanceProbability",
        ],
        "asymptotic_logspace_or_derandomization": "NOT_IMPLEMENTED",
    }
