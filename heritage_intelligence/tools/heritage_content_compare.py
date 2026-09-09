#!/usr/bin/env python3
"""Compare indexed Heritage text blobs without modifying any source mirror."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path


TEXT_EXTENSIONS = {
    ".md", ".txt", ".rst", ".adoc", ".json", ".jsonl", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".csv", ".tsv", ".sql", ".py", ".js",
    ".jsx", ".ts", ".tsx", ".html", ".css", ".scss", ".sh", ".ps1",
    ".bat", ".xml", ".graphql",
}
PROSE_EXTENSIONS = {".md", ".txt", ".rst", ".adoc"}


def batch_read(repo: Path, shas: list[str]) -> dict[str, bytes]:
    if not shas:
        return {}
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    proc = subprocess.Popen(
        ["git", "cat-file", "--batch"], cwd=repo, stdin=subprocess.PIPE,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
    )
    assert proc.stdin is not None and proc.stdout is not None
    result: dict[str, bytes] = {}
    for expected in shas:
        proc.stdin.write((expected + "\n").encode("ascii"))
        proc.stdin.flush()
        header = proc.stdout.readline().decode("ascii", "replace").strip()
        parts = header.split()
        if len(parts) < 3 or parts[1] == "missing":
            continue
        size = int(parts[2])
        data = proc.stdout.read(size)
        proc.stdout.read(1)
        result[expected] = data
    proc.stdin.close()
    proc.wait(timeout=120)
    return result


def decode_text(data: bytes) -> str | None:
    if b"\0" in data[:8192]:
        return None
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return "\n".join(line for line in lines if line).casefold()


def tokens(text: str) -> set[str]:
    latin = re.findall(r"[a-z0-9_]{2,}", text)
    cjk_runs = re.findall(r"[\u3400-\u9fff\uac00-\ud7af]+", text)
    cjk = []
    for run in cjk_runs:
        if len(run) < 3:
            cjk.append(run)
        else:
            cjk.extend(run[i:i + 3] for i in range(len(run) - 2))
    return set(latin + cjk)


def simhash(items: set[str]) -> int:
    vector = [0] * 64
    for item in items:
        digest = hashlib.blake2b(item.encode("utf-8"), digest_size=8).digest()
        value = int.from_bytes(digest, "big")
        for bit in range(64):
            vector[bit] += 1 if value & (1 << bit) else -1
    result = 0
    for bit, score in enumerate(vector):
        if score >= 0:
            result |= 1 << bit
    return result


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mirror-root", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--skip-sequence", action="store_true", help="Use Jaccard-only candidate generation for large histories")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    with args.inventory.open("r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    wanted_by_repo: dict[str, set[str]] = defaultdict(set)
    row_by_blob: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        row_by_blob[row["source_blob"]].append(row)
        ext = (row.get("extension") or Path(row.get("source_path", "")).suffix).casefold()
        size = int(row.get("size_bytes") or 0)
        if ext in TEXT_EXTENSIONS and size <= 1_000_000:
            wanted_by_repo[row["repository"]].add(row["source_blob"])

    content: dict[str, bytes] = {}
    source_repo: dict[str, str] = {}
    for repo_name, shas in wanted_by_repo.items():
        missing = [sha for sha in sorted(shas) if sha not in content]
        fetched = batch_read(args.mirror_root / f"{repo_name}.git", missing)
        for sha, data in fetched.items():
            content[sha] = data
            source_repo[sha] = repo_name

    feature_rows = []
    normalized_groups: dict[str, list[str]] = defaultdict(list)
    prose: dict[str, dict[str, object]] = {}
    decode_failures = []
    for sha, data in sorted(content.items()):
        text = decode_text(data)
        if text is None:
            decode_failures.append(sha)
            continue
        norm = normalize(text)
        norm_sha = hashlib.sha256(norm.encode("utf-8")).hexdigest()
        normalized_groups[norm_sha].append(sha)
        representatives = row_by_blob[sha]
        extensions = sorted({(r.get("extension") or Path(r.get("source_path", "")).suffix).casefold() for r in representatives})
        token_set = tokens(norm)
        feature_rows.append({
            "source_blob": sha,
            "read_from_repository": source_repo[sha],
            "content_sha256": hashlib.sha256(data).hexdigest(),
            "normalized_sha256": norm_sha,
            "size_bytes": len(data),
            "line_count": text.count("\n") + 1,
            "token_count": len(token_set),
            "extensions": ";".join(extensions),
        })
        if set(extensions) & PROSE_EXTENSIONS and len(norm) <= 500_000 and len(token_set) >= 25:
            prose[sha] = {
                "normalized": norm,
                "normalized_sha256": norm_sha,
                "tokens": token_set,
                "simhash": simhash(token_set),
                "paths": sorted({f"{r['repository']}:{r['source_path']}" for r in representatives}),
            }

    normalized_duplicate_rows = []
    for norm_sha, members in normalized_groups.items():
        if len(members) > 1:
            normalized_duplicate_rows.append({
                "normalized_sha256": norm_sha,
                "member_count": len(members),
                "source_blobs": ";".join(sorted(members)),
                "paths": ";".join(sorted({p for sha in members for p in prose.get(sha, {}).get("paths", [])})),
            })

    buckets: dict[tuple[int, int], list[str]] = defaultdict(list)
    for sha, item in prose.items():
        value = int(item["simhash"])
        for band in range(4):
            buckets[(band, (value >> (band * 16)) & 0xFFFF)].append(sha)
    candidate_pairs: set[tuple[str, str]] = set()
    for members in buckets.values():
        if len(members) > 200:
            continue
        for i, left in enumerate(members):
            for right in members[i + 1:]:
                if left != right:
                    candidate_pairs.add(tuple(sorted((left, right))))

    near_rows = []
    for left, right in sorted(candidate_pairs):
        a = prose[left]
        b = prose[right]
        if a["normalized_sha256"] == b["normalized_sha256"]:
            continue
        if (int(a["simhash"]) ^ int(b["simhash"])).bit_count() > 12:
            continue
        ta = set(a["tokens"])
        tb = set(b["tokens"])
        union = len(ta | tb)
        jaccard = len(ta & tb) / union if union else 0.0
        length_ratio = min(len(str(a["normalized"])), len(str(b["normalized"]))) / max(len(str(a["normalized"])), len(str(b["normalized"])))
        if jaccard < 0.70 or length_ratio < 0.55:
            continue
        if args.skip_sequence:
            if jaccard < 0.80:
                continue
            sequence_ratio = 0.0
        else:
            max_length = max(len(str(a["normalized"])), len(str(b["normalized"])))
            sequence_ratio = (
                SequenceMatcher(None, str(a["normalized"]), str(b["normalized"]), autojunk=False).ratio()
                if max_length <= 100_000 else 0.0
            )
            if jaccard < 0.75 and sequence_ratio < 0.82:
                continue
        near_rows.append({
            "left_blob": left,
            "right_blob": right,
            "token_jaccard": f"{jaccard:.6f}",
            "sequence_ratio": f"{sequence_ratio:.6f}",
            "length_ratio": f"{length_ratio:.6f}",
            "left_paths": ";".join(a["paths"]),
            "right_paths": ";".join(b["paths"]),
            "review_status": "SEMANTIC_CANDIDATE",
        })

    write_csv(
        args.output / "content_features.csv",
        ["source_blob", "read_from_repository", "content_sha256", "normalized_sha256", "size_bytes", "line_count", "token_count", "extensions"],
        feature_rows,
    )
    write_csv(
        args.output / "normalized_duplicate_groups.csv",
        ["normalized_sha256", "member_count", "source_blobs", "paths"],
        sorted(normalized_duplicate_rows, key=lambda r: (-int(r["member_count"]), str(r["normalized_sha256"]))),
    )
    write_csv(
        args.output / "semantic_duplicate_candidates.csv",
        ["left_blob", "right_blob", "token_jaccard", "sequence_ratio", "length_ratio", "left_paths", "right_paths", "review_status"],
        sorted(near_rows, key=lambda r: (-float(r["sequence_ratio"]), -float(r["token_jaccard"]))),
    )
    summary = {
        "candidate_unique_blobs": len(row_by_blob),
        "text_blobs_requested": len(set().union(*wanted_by_repo.values())) if wanted_by_repo else 0,
        "text_blobs_read": len(content),
        "text_blobs_decoded": len(feature_rows),
        "decode_failures": len(decode_failures),
        "normalized_duplicate_groups": len(normalized_duplicate_rows),
        "normalized_duplicate_extra_blobs": sum(int(r["member_count"]) - 1 for r in normalized_duplicate_rows),
        "semantic_duplicate_candidates": len(near_rows),
        "semantic_candidates_require_review": True,
    }
    (args.output / "content_compare_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
