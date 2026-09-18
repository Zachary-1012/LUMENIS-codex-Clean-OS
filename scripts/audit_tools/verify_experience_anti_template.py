#!/usr/bin/env python3
"""LUMENIS Experience anti-template gate.

Baseline mode prevents new template debt while V3 migration is incomplete.
Strict mode is required for core Experience implementation changes and forces
the five Golden Pages onto distinct semantic V3 compositions.

This checker is intentionally structural. Visual acceptance remains a separate
Playwright screenshot/ARIA responsibility.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXP = ROOT / "experience_v2"
BASELINE = EXP / "02_authority" / "ANTI_TEMPLATE_BASELINE.json"
SCREENS = EXP / "10_prototype" / "data" / "screens.js"
SECTIONS = EXP / "10_prototype" / "assets" / "sections.js"
CONSTITUTION = ROOT / "00-GOVERNANCE" / "LUMENIS-EXPERIENCE-CONSTITUTION.md"
LOCAL_AGENTS = EXP / "AGENTS.md"


def fail(messages: list[str], summary: dict) -> int:
    payload = {"ok": False, "errors": messages, **summary}
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 2


def load_screens() -> dict:
    text = SCREENS.read_text(encoding="utf-8")
    marker = "window.LUM_SCREENS"
    start = text.find(marker)
    if start < 0:
        raise ValueError("window.LUM_SCREENS assignment not found")
    eq = text.find("=", start)
    obj_start = text.find("{", eq)
    if obj_start < 0:
        raise ValueError("LUM_SCREENS object start not found")

    depth = 0
    in_string = False
    escape = False
    obj_end = None
    for i, ch in enumerate(text[obj_start:], start=obj_start):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                obj_end = i + 1
                break
    if obj_end is None:
        raise ValueError("LUM_SCREENS object end not found")
    return json.loads(text[obj_start:obj_end])


def signature(screen: dict) -> str:
    return ">".join(str(s.get("type", "?")) for s in screen.get("sections", []))


def metric_count(screen: dict) -> int:
    total = 0
    for section in screen.get("sections", []):
        if section.get("type") == "kpis":
            total += len(section.get("items") or [])
    return total


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--baseline", action="store_true", help="enforce ratchet without requiring completed Golden Page migration")
    mode.add_argument("--strict", action="store_true", help="require Golden Page V3 migration")
    args = parser.parse_args()

    errors: list[str] = []
    for p in (BASELINE, SCREENS, SECTIONS, CONSTITUTION, LOCAL_AGENTS):
        if not p.exists():
            errors.append(f"required file missing: {p.relative_to(ROOT)}")
    if errors:
        return fail(errors, {"mode": "strict" if args.strict else "baseline"})

    cfg = json.loads(BASELINE.read_text(encoding="utf-8"))
    screens = load_screens()
    rows = []
    for sid, screen in screens.items():
        rows.append({
            "id": sid,
            "signature": signature(screen),
            "metric_count": metric_count(screen),
            "types": [s.get("type", "?") for s in screen.get("sections", [])],
        })

    sig_counts = Counter(r["signature"] for r in rows)
    largest_sig, largest_count = sig_counts.most_common(1)[0]
    head_kpis_split = sig_counts.get("head>kpis>split", 0)
    four_kpi = sum(1 for r in rows if r["metric_count"] == 4)
    summary = {
        "mode": "strict" if args.strict else "baseline",
        "screen_count": len(rows),
        "unique_top_level_signatures": len(sig_counts),
        "largest_identical_signature": {"signature": largest_sig, "count": largest_count},
        "head_kpis_split_count": head_kpis_split,
        "four_kpi_screen_count": four_kpi,
    }

    observed = cfg["observed"]
    ceiling = cfg["baseline_ceiling"]
    if len(rows) != observed["screen_count"]:
        errors.append(f"screen count changed unexpectedly: {len(rows)} != {observed['screen_count']}")
    if largest_count > ceiling["largest_identical_signature_max"]:
        errors.append(
            f"template debt increased: largest identical signature {largest_count} > "
            f"{ceiling['largest_identical_signature_max']}"
        )
    if head_kpis_split > ceiling["head_kpis_split_max"]:
        errors.append(
            f"head>kpis>split debt increased: {head_kpis_split} > {ceiling['head_kpis_split_max']}"
        )
    if four_kpi > ceiling["four_kpi_screen_max"]:
        errors.append(f"four-KPI debt increased: {four_kpi} > {ceiling['four_kpi_screen_max']}")

    golden = observed["golden_pages"]
    missing_golden = [sid for sid in golden if sid not in screens]
    if missing_golden:
        errors.append("missing Golden Pages: " + ", ".join(missing_golden))

    if args.strict and not missing_golden:
        target = cfg["strict_target"]
        sections_text = SECTIONS.read_text(encoding="utf-8")
        legacy_phrase = "44 screens may ONLY compose registered patterns/components (no bespoke layout)"
        if legacy_phrase in sections_text:
            errors.append("legacy fixed-composer authority is still present in sections.js")

        if head_kpis_split > target["head_kpis_split_max"]:
            errors.append(
                f"strict target: head>kpis>split {head_kpis_split} > {target['head_kpis_split_max']}"
            )
        if four_kpi > target["four_kpi_screen_max"]:
            errors.append(
                f"strict target: four-KPI screens {four_kpi} > {target['four_kpi_screen_max']}"
            )

        golden_signatures = {signature(screens[sid]) for sid in golden}
        summary["golden_signatures"] = {sid: signature(screens[sid]) for sid in golden}
        summary["golden_unique_signature_count"] = len(golden_signatures)
        if len(golden_signatures) < target["golden_unique_signature_min"]:
            errors.append(
                f"Golden Pages remain structurally duplicated: {len(golden_signatures)} unique < "
                f"{target['golden_unique_signature_min']}"
            )

        forbidden = set(target["golden_forbidden_top_level_types"])
        for sid in golden:
            types = [s.get("type", "?") for s in screens[sid].get("sections", [])]
            bad = forbidden.intersection(types)
            if bad:
                errors.append(f"{sid} still uses forbidden top-level generic types: {sorted(bad)}")

        for sid, required in target["golden_required_top_level_types"].items():
            types = {s.get("type", "?") for s in screens[sid].get("sections", [])}
            missing = [t for t in required if t not in types]
            if missing:
                errors.append(f"{sid} missing V3 semantic types: {missing}")

    if errors:
        return fail(errors, summary)

    print(json.dumps({"ok": True, **summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
