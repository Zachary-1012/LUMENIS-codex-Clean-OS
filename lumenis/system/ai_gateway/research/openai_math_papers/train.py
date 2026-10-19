"""Finite, restartable Gibbs-policy training. NO training is performed on import.

Requires a local consent record with decision_ref and permitted dataset digest.
That record is audit input, not a replacement for LUMENIS Permission/C2 admission.
Final product promotion must use the existing owned-service admission path.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from decimal import Decimal
from pathlib import Path

from lumenis.shared.evaluation.openai_math_papers.core import (
    Budget,
    MathInputError,
    digest,
    wire,
)
from lumenis.shared.evaluation.openai_math_papers.matching_113 import Graph

from .gibbs_policy import GibbsMatchingPolicy

MAX_BYTES = 8_000_000


def read_json(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise MathInputError("UNSAFE_LOCAL_FILE")
    return json.loads(path.read_text(encoding="utf-8"))


def save_new(path, obj):
    # Exclusive create; old checkpoints are never overwritten.
    data = json.dumps(
        wire(obj), ensure_ascii=False, sort_keys=True, allow_nan=False
    ).encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    # An interrupted partial file remains evidence and is never claimed resumable.
    with os.fdopen(fd, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())


def topology_isomorphic(a, b, budget):
    """Exact multigraph topology check, bounded and fail-closed on audit exhaustion.

    Intentionally ignores edge features: the split policy is stricter than merely
    rejecting identical feature-labelled tasks. Parallel edges remain distinct.
    """
    if a.vertices != b.vertices or len(a.edges) != len(b.edges):
        return False
    n = a.vertices
    def adjacency(g):
        m = [[0] * n for _ in range(n)]
        for u, v in g.edges:
            m[u][v] += 1
            m[v][u] += 1
        return m
    aa, bb = adjacency(a), adjacency(b)
    signatures_a = [tuple(sorted(row)) for row in aa]
    signatures_b = [tuple(sorted(row)) for row in bb]
    if sorted(signatures_a) != sorted(signatures_b):
        return False
    order = sorted(range(n), key=lambda u: (signatures_a.count(signatures_a[u]), -sum(aa[u])))
    mapping, used = {}, set()
    def visit(k):
        budget.tick()
        if k == n:
            return True
        u = order[k]
        for v in range(n):
            budget.tick()
            if v in used or signatures_a[u] != signatures_b[v]:
                continue
            if any(aa[u][x] != bb[v][y] for x, y in mapping.items()):
                continue
            mapping[u] = v
            used.add(v)
            if visit(k + 1):
                return True
            used.remove(v)
            del mapping[u]
        return False
    return visit(0)


def load_data(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise MathInputError("DATASET_SIZE")
    raw = path.read_bytes()
    rows = [json.loads(x) for x in raw.decode("utf-8").splitlines() if x.strip()]
    if not rows or len(rows) > 2000:
        raise MathInputError("DATASET_ROW_COUNT")
    seen = {}
    record_ids = set()
    audited_graphs = []
    audit_budget = Budget(seconds=30, max_steps=2_000_000, max_items=2000)
    for r in rows:
        if type(r) is not dict or set(r) != {
            "id",
            "split",
            "graph",
            "features",
            "target",
            "origin",
            "group_id",
        }:
            raise MathInputError("DATA_RECORD_FIELDS")
        if (
            r["split"] not in {"train", "validation", "holdout"}
            or type(r["group_id"]) is not str
            or not r["group_id"].strip()
            or len(r["group_id"]) > 256
        ):
            raise MathInputError("SPLIT_GROUP_REQUIRED")
        if (
            type(r["id"]) is not str
            or not r["id"].strip()
            or len(r["id"]) > 256
            or r["id"] in record_ids
        ):
            raise MathInputError("DATA_RECORD_ID_INVALID_OR_DUPLICATE")
        record_ids.add(r["id"])
        if r["origin"] not in {"DECLARED_SYNTHETIC_MATH", "APPROVED_TASK_DERIVATIVE"}:
            raise MathInputError("DATA_ORIGIN_REQUIRED")
        g = Graph.read(r["graph"])
        for previous_split, previous_graph in audited_graphs:
            if previous_split != r["split"] and topology_isomorphic(g, previous_graph, audit_budget):
                raise MathInputError("CROSS_SPLIT_TOPOLOGY_LEAKAGE")
        audited_graphs.append((r["split"], g))
        if not g.check(r["target"]):
            raise MathInputError("TARGET_NOT_A_MATCHING")
        for key in (
            "group:" + r["group_id"],
            "instance:" + digest({"graph": r["graph"], "features": r["features"]}),
        ):
            old = seen.setdefault(key, r["split"])
            if old != r["split"]:
                raise MathInputError("CROSS_SPLIT_LEAKAGE")
    # Cross-split topology is audited exactly, including vertex/edge permutations.
    return rows, hashlib.sha256(raw).hexdigest()


def implementation_identity():
    from lumenis.shared.evaluation.openai_math_papers import core

    model_root = Path(__file__).parent
    kernel_root = Path(core.__file__).parent
    material = {}
    for prefix, root in [("model", model_root), ("math", kernel_root)]:
        for p in sorted(root.glob("*.py")):
            material[prefix + "/" + p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    return {
        "code_sha256": digest(material),
        "python": sys.version,
        "arithmetic": "Decimal explicit precision 60; exact input Fraction",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--consent", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--epochs", type=int, default=1)
    ap.add_argument("--learning-rate", default="1/100")
    ap.add_argument("--seconds", type=float, default=120)
    ap.add_argument("--resume", type=Path)
    args = ap.parse_args()
    rows, data_sha = load_data(args.data)
    consent = read_json(args.consent)
    if (
        consent.get("dataset_sha256") != data_sha
        or consent.get("operation") != "paper113_parameter_training"
        or not consent.get("decision_ref")
    ):
        raise MathInputError("EXACT_TRAINING_CONSENT_REQUIRED")
    if not 1 <= args.epochs <= 100 or not 0 < args.seconds <= 3600:
        raise MathInputError("TRAINING_BUDGET")
    if args.output.is_symlink():
        raise MathInputError("OUTPUT_SYMLINK")
    args.output.mkdir(parents=True, exist_ok=True)
    train = [r for r in rows if r["split"] == "train"]
    if not train:
        raise MathInputError("NO_TRAIN_SPLIT")
    if not any(r["split"] == "holdout" for r in rows):
        raise MathInputError("FROZEN_HOLDOUT_REQUIRED")
    if not train[0]["features"]:
        raise MathInputError("NONEMPTY_TRAIN_FEATURES")
    width = len(train[0]["features"][0])
    model = GibbsMatchingPolicy([Decimal(0)] * width)
    identity = implementation_identity()
    protocol = {
        "data_sha256": data_sha,
        "learning_rate": args.learning_rate,
        "width": width,
        "implementation": identity,
        "epochs": args.epochs,
        "decision_ref": consent["decision_ref"],
    }
    cursor = 0
    total = len(train) * args.epochs
    if args.resume:
        chk = read_json(args.resume)
        material = chk["payload"]
        if (
            digest(material) != chk["payload_sha256"]
            or material["protocol"] != protocol
        ):
            raise MathInputError("RESUME_IDENTITY_MISMATCH")
        model = GibbsMatchingPolicy(
            [Decimal(v) for v in material["model"]["weights"]],
            material["model"]["step"],
        )
        cursor = material["cursor"]
        if type(cursor) is not int or not 0 <= cursor <= total or model.step != cursor:
            raise MathInputError("RESUME_CURSOR")
    start = time.monotonic()
    while cursor < total:
        remaining = args.seconds - (time.monotonic() - start)
        if remaining <= 0:
            raise MathInputError("WALL_LIMIT_LAST_CHECKPOINT_RETAINED")
        r = train[cursor % len(train)]
        receipt = model.update(
            Graph.read(r["graph"]),
            r["features"],
            r["target"],
            args.learning_rate,
            Budget(seconds=min(remaining, 120), max_items=10000),
        )
        cursor += 1
        payload = {
            "protocol": protocol,
            "cursor": cursor,
            "model": model.state(),
            "last_record_id": r["id"],
            "receipt": receipt,
        }
        save_new(
            args.output / f"checkpoint-{cursor:08d}.json",
            {"payload": payload, "payload_sha256": digest(payload)},
        )
        print(
            json.dumps(
                wire(
                    {
                        "step": cursor,
                        "nll": receipt["preupdate_nll"],
                        "checkpoint": f"checkpoint-{cursor:08d}.json",
                    }
                )
            ),
            flush=True,
        )
    print(
        json.dumps(
            {
                "training": "FINISHED_NOT_EVALUATED",
                "production_promotion": "NOT_GRANTED",
            }
        )
    )


if __name__ == "__main__":
    main()
