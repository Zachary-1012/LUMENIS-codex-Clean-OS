#!/usr/bin/env python3
"""LUMENIS App-only Experience anti-template gate.

The canonical user Experience is app/. Historical browser/Jinja/static surfaces
are migration sources only and must never become a second presentation truth.

This gate is intentionally network-independent. Flutter analyze/test remains in
the App Gate when the GitHub execution layer can reach Flutter/pub infrastructure.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"
LIB = APP / "lib"
CONSTITUTION = ROOT / "00-GOVERNANCE" / "LUMENIS-EXPERIENCE-CONSTITUTION.md"
ARCHITECTURE = ROOT / "00-GOVERNANCE" / "LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md"

REQUIRED = (
    APP / "pubspec.yaml",
    LIB / "main.dart",
    LIB / "core" / "lumenis_core_client.dart",
    LIB / "product" / "product_domain.dart",
    LIB / "product" / "lumenis_app.dart",
    LIB / "features" / "launch" / "launch_surface.dart",
    CONSTITUTION,
    ARCHITECTURE,
)

FORBIDDEN_APP_REFERENCES = (
    "experience_v2/",
    "templates/",
    "static/",
    "ref_gpt_v2/",
    "zbc-design-system",
    "apple-ui-reference",
    "Apple UI reference",
    "GPT UI reference",
    "Bento dashboard",
    "Generic SaaS dashboard",
    "Admin template",
    "glassmorphism",
    "dart:html",
    "package:flutter_web_plugins",
)

FORBIDDEN_CANONICAL_TARGETS = (
    APP / "web",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--baseline", action="store_true")
    mode.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    for path in REQUIRED:
        if not path.is_file():
            errors.append(f"required App-only authority file missing: {path.relative_to(ROOT)}")

    for path in FORBIDDEN_CANONICAL_TARGETS:
        if path.exists():
            errors.append(f"web target must not become canonical Experience: {path.relative_to(ROOT)}")

    dart_files = sorted(LIB.rglob("*.dart")) if LIB.is_dir() else []
    if not dart_files:
        errors.append("canonical Flutter app has no Dart implementation under app/lib")

    for path in dart_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in FORBIDDEN_APP_REFERENCES:
            if marker.lower() in text.lower():
                errors.append(
                    f"canonical App references legacy/web presentation authority: "
                    f"{path.relative_to(ROOT)} -> {marker}"
                )

    pubspec = APP / "pubspec.yaml"
    if pubspec.is_file():
        pub = pubspec.read_text(encoding="utf-8", errors="replace")
        if "sdk: flutter" not in pub:
            errors.append("app/pubspec.yaml is not bound to Flutter SDK")

    main_dart = LIB / "main.dart"
    if main_dart.is_file():
        text = main_dart.read_text(encoding="utf-8", errors="replace")
        if "runApp(const LumenisApp())" not in text:
            errors.append("app/lib/main.dart does not boot the canonical LumenisApp")

    launch = LIB / "features" / "launch" / "launch_surface.dart"
    if launch.is_file():
        text = launch.read_text(encoding="utf-8", errors="replace")
        for contract in ("runtimeIdentity()", "subjects()", "ProductDomain.values"):
            if contract not in text:
                errors.append(f"LaunchSurface lost canonical Core/Product binding: {contract}")

    summary = {
        "ok": not errors,
        "mode": "strict" if args.strict else "baseline",
        "canonical_experience": "app/",
        "dart_file_count": len(dart_files),
        "legacy_web_authority": False,
    }

    if errors:
        print(json.dumps({**summary, "errors": sorted(set(errors))}, ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
