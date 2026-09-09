#!/usr/bin/env python3
"""Build provenance and coverage ledgers from the verified Git inventories."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


DOMAIN_TARGET = {
    "korean": "03_language_content_intelligence/Korean_Content_Intelligence_Collection",
    "xiaohongshu": "02_platform_intelligence/xiaohongshu",
    "platform": "02_platform_intelligence",
    "data_metrics": "04_data_metrics_presentation",
    "kos_kol_koc": "05_domain_methodologies/kos_kol_koc",
    "podcast": "05_domain_methodologies/podcast",
    "domain_methodology": "05_domain_methodologies",
    "ui_ux": "07_product_ux_design",
    "ai_agent": "08_ai_agent_intelligence",
    "evidence_contract": "06_evidence_truth_contracts",
    "engineering": "09_engineering_governance",
    "decision_memory": "10_decision_memory",
    "regression_memory": "12_tests_regression_memory",
}

DOMAIN_OWNER = {
    "korean": "Shared Capability / Content & Creation",
    "xiaohongshu": "LUMENIS / Collector",
    "platform": "LUMENIS / SYSTEM",
    "data_metrics": "LUMENIS / Production Truth",
    "kos_kol_koc": "LUMENIS / BMP",
    "podcast": "LUMENIS / Shared Capability",
    "domain_methodology": "LUMENIS / CTH or BMP by Contract",
    "ui_ux": "LUMENIS / Production UX",
    "ai_agent": "OSAI Intelligence with LUMENIS Contract",
    "evidence_contract": "LUMENIS / Production Truth",
    "engineering": "LUMENIS Command / Engineering Sidecar",
    "decision_memory": "LUMENIS Governance",
    "regression_memory": "LUMENIS Engineering",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--category-root", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    history = read_csv(args.inventory_root / "historical_asset_versions.csv")
    commits = read_csv(args.inventory_root / "commit_inventory.csv")
    features = read_csv(args.inventory_root / "history_compare" / "content_features.csv")
    semantic = read_csv(args.inventory_root / "history_compare" / "semantic_duplicate_candidates.csv")
    commit_subject = {(r["repository"], r["commit"]): r["subject"] for r in commits}
    decoded_blobs = {r["source_blob"] for r in features}

    by_blob: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in history:
        by_blob[row["source_blob"]].append(row)

    provenance_rows = []
    pending_rows = []
    for blob, members in sorted(by_blob.items()):
        domains = sorted({d for row in members for d in row["domains"].split(";") if d})
        primary_domain = domains[0] if domains else "research_learning"
        repositories = sorted({row["repository"] for row in members})
        paths = sorted({f"{row['repository']}:{row['source_path']}" for row in members})
        branches = sorted({b for row in members for b in row["reachable_from_branches"].split(";") if b})
        first = min(members, key=lambda r: (r["first_seen_date"], r["first_seen_commit"]))
        last = max(members, key=lambda r: (r["last_seen_date"], r["last_seen_commit"]))
        equivalents = {row["current_equivalent"] for row in members}
        if "EXACT_BLOB" in equivalents:
            current_equivalent = "EXACT_BLOB"
            decision = "KEEP_CURRENT_REFERENCE"
        elif "SAME_PATH_DIFFERENT_BLOB" in equivalents:
            current_equivalent = "SAME_PATH_DIFFERENT_BLOB"
            decision = "PENDING_SEMANTIC_CURRENT_EQUIVALENT_REVIEW"
        else:
            current_equivalent = "NO_EXACT_CURRENT_EQUIVALENT"
            decision = "PENDING_HERITAGE_REVIEW"
        target = DOMAIN_TARGET.get(primary_domain, "01_research_learning")
        owner = DOMAIN_OWNER.get(primary_domain, "LUMENIS Heritage Governance")
        row = {
            "provenance_id": f"HIF-{blob[:12]}",
            "asset_name": Path(first["source_path"]).name,
            "category_domains": ";".join(domains),
            "source_repositories": ";".join(repositories),
            "source_branches": ";".join(branches),
            "source_paths": ";".join(paths),
            "source_blob": blob,
            "first_seen_commit": first["first_seen_commit"],
            "first_seen_date": first["first_seen_date"],
            "last_seen_commit": last["last_seen_commit"],
            "last_seen_date": last["last_seen_date"],
            "original_purpose_evidence": commit_subject.get((first["repository"], first["first_seen_commit"]), ""),
            "summary": "Source artifact indexed; semantic content retained at source Blob and pending collection-level interpretation.",
            "evidence_level": "GIT_REPO+BRANCH+COMMIT+PATH+BLOB",
            "production_verified": "NO",
            "current_relevance": current_equivalent,
            "current_equivalent": current_equivalent,
            "current_owner": owner,
            "dependencies": "PENDING_DEPENDENCY_TRACE",
            "decision": decision,
            "target_location": target,
            "status": "INDEXED",
            "supersedes": "PENDING",
            "superseded_by": "PENDING",
            "do_not_lose": "Source provenance, unique knowledge, corrections and negative findings.",
            "do_not_regress": "Do not promote into Production without Current Truth, Contract, Test, Evidence and Release Gate.",
            "notes": "Content decoded" if blob in decoded_blobs else "Binary, oversized or undecodable content; metadata only.",
        }
        provenance_rows.append(row)
        if decision.startswith("PENDING"):
            pending_rows.append(row)

    coverage_rows = []
    all_domains = sorted(DOMAIN_TARGET)
    for domain in all_domains:
        rows = [r for r in history if domain in r["domains"].split(";")]
        blobs: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in rows:
            blobs[row["source_blob"]].append(row)
        exact_blobs = {
            blob for blob, members in blobs.items()
            if any(r["current_equivalent"] == "EXACT_BLOB" for r in members)
        }
        same_path_blobs = {
            blob for blob, members in blobs.items()
            if blob not in exact_blobs and any(r["current_equivalent"] == "SAME_PATH_DIFFERENT_BLOB" for r in members)
        }
        no_exact_blobs = set(blobs) - exact_blobs - same_path_blobs
        semantic_pairs = [
            r for r in semantic if r["left_blob"] in blobs or r["right_blob"] in blobs
        ]
        coverage_rows.append({
            "domain": domain,
            "path_blob_versions_discovered": len(rows),
            "unique_blobs_indexed": len(blobs),
            "index_coverage_percent": "100.00" if rows else "0.00",
            "exact_duplicate_extra_versions": len(rows) - len(blobs),
            "current_exact_blob_matches": len(exact_blobs),
            "same_path_different_blob": len(same_path_blobs),
            "no_exact_current_equivalent": len(no_exact_blobs),
            "historical_only_versions": sum(r["present_at_scanned_tip"] == "False" for r in rows),
            "decoded_text_blobs": len(set(blobs) & decoded_blobs),
            "semantic_candidates_pending": len(semantic_pairs),
        })

    write_csv(
        args.output / "ASSET_PROVENANCE_LEDGER.csv",
        [
            "provenance_id", "asset_name", "category_domains", "source_repositories",
            "source_branches", "source_paths", "source_blob", "first_seen_commit",
            "first_seen_date", "last_seen_commit", "last_seen_date",
            "original_purpose_evidence", "summary", "evidence_level",
            "production_verified", "current_relevance", "current_equivalent",
            "current_owner", "dependencies", "decision", "target_location", "status",
            "supersedes", "superseded_by", "do_not_lose", "do_not_regress", "notes",
        ],
        provenance_rows,
    )
    write_csv(
        args.output / "PENDING_VERIFICATION_LEDGER.csv",
        [
            "provenance_id", "asset_name", "category_domains", "source_repositories",
            "source_branches", "source_paths", "source_blob", "first_seen_commit",
            "first_seen_date", "current_equivalent", "current_owner", "decision",
            "target_location", "status", "notes",
        ],
        pending_rows,
    )
    write_csv(
        args.output / "ASSET_COVERAGE_MATRIX.csv",
        [
            "domain", "path_blob_versions_discovered", "unique_blobs_indexed",
            "index_coverage_percent", "exact_duplicate_extra_versions",
            "current_exact_blob_matches", "same_path_different_blob",
            "no_exact_current_equivalent", "historical_only_versions",
            "decoded_text_blobs", "semantic_candidates_pending",
        ],
        coverage_rows,
    )
    if args.category_root:
        for directory in [
            "01_research_learning", "02_platform_intelligence",
            "03_language_content_intelligence", "04_data_metrics_presentation",
            "05_domain_methodologies", "06_evidence_truth_contracts",
            "07_product_ux_design", "08_ai_agent_intelligence",
            "09_engineering_governance", "10_decision_memory",
            "11_cases_benchmarks", "12_tests_regression_memory",
            "99_archive_reference",
        ]:
            (args.category_root / directory).mkdir(parents=True, exist_ok=True)
        for domain, target in DOMAIN_TARGET.items():
            target_dir = args.category_root / target
            target_dir.mkdir(parents=True, exist_ok=True)
            pointers = [
                {
                    "provenance_id": row["provenance_id"],
                    "source_blob": row["source_blob"],
                    "current_relevance": row["current_relevance"],
                    "decision": row["decision"],
                    "status": row["status"],
                }
                for row in provenance_rows
                if domain in str(row["category_domains"]).split(";")
            ]
            write_csv(
                target_dir / f"{domain.upper()}_SOURCE_POINTERS.csv",
                ["provenance_id", "source_blob", "current_relevance", "decision", "status"],
                pointers,
            )
    summary = {
        "knowledge_path_blob_versions_discovered": len(history),
        "unique_knowledge_blobs_indexed": len(by_blob),
        "provenance_index_coverage_percent": 100.0 if history else 0.0,
        "pending_current_equivalent_or_semantic_review": len(pending_rows),
        "coverage_domains": len(coverage_rows),
    }
    (args.output / "REGISTRY_BUILD_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
