"""Independent file evaluation of already frozen paper113 policy parameters.

Model predictions are fixed before target scoring. Exact-support decoding remains
constrained inference and cannot be represented as tool-free prediction.
No pretrained LLM performance or business improvement is inferred here.
"""

import argparse
import json
from decimal import Decimal, localcontext
from pathlib import Path

from lumenis.shared.evaluation.openai_math_papers.core import (
    Budget,
    MathInputError,
    digest,
    wire,
)
from lumenis.shared.evaluation.openai_math_papers.matching_113 import Graph

from .gibbs_policy import GibbsMatchingPolicy
from .train import implementation_identity, load_data, read_json


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--checkpoint", type=Path, required=True)
    p.add_argument("--split", choices=["validation", "holdout"], default="holdout")
    p.add_argument("--seconds", type=float, default=120)
    args = p.parse_args()
    rows, sha = load_data(args.data)
    c = read_json(args.checkpoint)
    if digest(c["payload"]) != c["payload_sha256"]:
        raise MathInputError("CHECKPOINT_HASH")
    if sha != c["payload"]["protocol"]["data_sha256"]:
        raise MathInputError("FROZEN_SPLIT_DATA_CHANGED")
    if c["payload"]["protocol"].get("implementation") != implementation_identity():
        raise MathInputError("EVALUATION_IMPLEMENTATION_CHANGED")
    s = c["payload"]["model"]
    model = GibbsMatchingPolicy([Decimal(v) for v in s["weights"]], s["step"])
    baseline = GibbsMatchingPolicy([Decimal(0)] * len(model.weights))
    selected = [r for r in rows if r["split"] == args.split]
    if not selected:
        raise MathInputError("NO_INDEPENDENT_SPLIT")
    budget = Budget(seconds=args.seconds, max_steps=2_000_000, max_items=10000)
    for r in selected:
        g = Graph.read(r["graph"])
        pred = model.predict(g, r["features"], budget)
        prior = baseline.predict(g, r["features"], budget)
        # Only now read labels for scoring; they never enter predict().
        gold = set(r["target"])
        if pred["state"] != "COMPUTED":
            raise MathInputError("FROZEN_CASE_HAS_NO_MODEL_RESULT")
        idx = next(i for i, m in enumerate(pred["support"]) if set(m) == gold)
        with localcontext() as ctx:
            ctx.prec = 60
            nll = -pred["distribution"][idx].ln()
            base_nll = -prior["distribution"][idx].ln()
        print(
            json.dumps(
                wire(
                    {
                        "id": r["id"],
                        "split": args.split,
                        "checkpoint_sha": c["payload_sha256"],
                        "gold_match": set(pred["map_matching"]) == gold,
                        "baseline_gold_match": set(prior["map_matching"]) == gold,
                        "model_step": model.step,
                        "nll": nll,
                        "baseline_nll": base_nll,
                        "constraint_valid": g.check(pred["map_matching"]),
                        "inference_type": "enumeration-constrained exponential-family model",
                        "business_result": "NOT_EVALUATED",
                    }
                )
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
