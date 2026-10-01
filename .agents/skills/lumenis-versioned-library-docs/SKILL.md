---
name: lumenis-versioned-library-docs
description: Must use whenever LUMENIS implementation or debugging depends on an external framework, SDK, package, API, CLI, protocol, browser API, Flutter/Dart package, Python library, or version-specific behavior.
---
# Current Library Documentation
Resolve the actual dependency and version from manifests/lockfiles first. Use Context7 for version-matched docs; fall back to authoritative current vendor/project docs. Do not invent APIs from model memory. Record compatibility assumptions that materially affect implementation. External docs inform implementation but never become Product Truth.
