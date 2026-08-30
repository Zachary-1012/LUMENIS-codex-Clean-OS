#!/usr/bin/env python3
"""Lightweight local license/source provenance audit.

This is a guardrail, not a legal determination. It scans tracked text files for
common third-party project markers and known restricted-license phrases. It does
not copy, execute or import third-party code.

Usage:
    python scripts/license_audit.py
"""

from __future__ import annotations

import subprocess
from pathlib import Path

MARKERS = {
    "MediaCrawler": "Potential MediaCrawler marker",
    "NON-COMMERCIAL LEARNING LICENSE": "Potential non-commercial license marker",
    "relakkes@gmail.com": "Potential MediaCrawler copyright marker",
}

ALLOWLIST = {
    "THIRD_PARTY_LICENSE_AUDIT.md",
    "scripts/license_audit.py",
}


def tracked_files() -> list[Path]:
    out = subprocess.check_output(["git", "ls-files"], text=True)
    return [Path(line.strip()) for line in out.splitlines() if line.strip()]


def main() -> int:
    hits: list[tuple[str, str, int, str]] = []
    for path in tracked_files():
        if path.name in ALLOWLIST or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for marker, reason in MARKERS.items():
            for line_no, line in enumerate(text.splitlines(), 1):
                if marker.lower() in line.lower():
                    hits.append((str(path), reason, line_no, line.strip()[:160]))

    print("Z-Brand-Core third-party provenance guard")
    if not hits:
        print("PASS: no configured restricted-project markers found.")
        return 0

    print("REVIEW REQUIRED:")
    for path, reason, line_no, line in hits:
        print(f"- {path}:{line_no}: {reason}: {line}")
    print("Do not assume a hit is infringement; review the file and provenance manually.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
