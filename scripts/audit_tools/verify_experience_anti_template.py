#!/usr/bin/env python3
"""LUMENIS multi-surface Experience anti-template gate.

The sole Experience authority governs Public Website and the Flutter Web,
Desktop and Mobile surfaces. Historical browser/Jinja/static implementations
must never return as a second presentation truth.

This gate is intentionally network-independent. Flutter analyze/test remains in
the App Gate when the GitHub execution layer can reach Flutter/pub infrastructure.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .experience_gate_mode import frontend_state
except ImportError:
    from experience_gate_mode import frontend_state

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"
LIB = APP / "lib"
CONSTITUTION = ROOT / "00-GOVERNANCE" / "LUMENIS-EXPERIENCE-CONSTITUTION.md"
ARCHITECTURE = ROOT / "00-GOVERNANCE" / "LUMENIS-PRODUCT-ARCHITECTURE-CURRENT.md"
SURFACE_DECISION = ROOT / "00-GOVERNANCE" / "LUMENIS-MULTI-SURFACE-DECISION-CURRENT.md"

REQUIRED = (
    APP / "pubspec.yaml",
    LIB / "main.dart",
    LIB / "core" / "lumenis_core_client.dart",
    LIB / "product" / "product_domain.dart",
    LIB / "product" / "lumenis_app.dart",
    LIB / "features" / "launch" / "launch_surface.dart",
    LIB / "features" / "cth" / "cth02" / "cth02_repository.dart",
    CONSTITUTION,
    ARCHITECTURE,
    SURFACE_DECISION,
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
)


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--baseline", action="store_true")
    mode.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    errors: list[str] = []
    try:
        retired = frontend_state(ROOT) == 'REMOVED_PENDING_REBUILD'
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
        retired = False
    removed_entries = {'app/lib/main.dart', 'app/lib/product/lumenis_app.dart', 'app/lib/features/launch/launch_surface.dart'}
    for path in REQUIRED:
        if retired and path.relative_to(ROOT).as_posix() in removed_entries:
            continue
        if not path.is_file():
            errors.append(f"required multi-surface authority file missing: {path.relative_to(ROOT)}")

    dart_files = sorted(LIB.rglob("*.dart")) if LIB.is_dir() else []
    if not dart_files:
        errors.append("canonical Flutter app has no Dart implementation under app/lib")

    for path in dart_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in FORBIDDEN_APP_REFERENCES:
            if marker.lower() in text.lower():
                errors.append(
                    f"canonical Flutter Experience references legacy presentation authority: "
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
        for contract in ("runtimeIdentity()", "LumenisWorkspaceShell("):
            if contract not in text:
                errors.append(f"LaunchSurface lost canonical Core/Product binding: {contract}")

    product_domain = LIB / "product" / "product_domain.dart"
    if product_domain.is_file():
        text = product_domain.read_text(encoding="utf-8", errors="replace")
        for contract in ("enum ProductDomain", "cth", "bmp", "shared", "system"):
            if contract not in text:
                errors.append(f"canonical ProductDomain contract missing: {contract}")

    cth02_repository = LIB / "features" / "cth" / "cth02" / "cth02_repository.dart"
    if cth02_repository.is_file():
        text = cth02_repository.read_text(encoding="utf-8", errors="replace")
        if "settingsSubjects()" not in text:
            errors.append("CTH-02 lost its protected Subject-directory Core binding")

    summary = {
        "ok": not errors,
        "mode": "strict" if args.strict else "baseline",
        "canonical_experience": "public-website + app/web-desktop-mobile",
        "experience_authority": "00-GOVERNANCE/LUMENIS-EXPERIENCE-CONSTITUTION.md",
        "dart_file_count": len(dart_files),
        "legacy_web_authority": False,
        "source_retirement": retired,
        "product_accepted": False,
    }

    if errors:
        print(json.dumps({**summary, "errors": sorted(set(errors))}, ensure_ascii=False, indent=2))
        return 2

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
