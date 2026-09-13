"""Select clean-checkout pytest files for LUMENIS CI.

The selector is intentionally simple and deterministic: enumerate repository test
files, then subtract paths listed in ci_environment_tests.txt. It prints one
repository-relative path per line for the workflow to pass explicitly to pytest.

Environment/live exclusion is not PASS; those suites remain release evidence as
documented in CI_TEST_TIERS.md.
"""
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
ENV_MANIFEST = TESTS / "ci_environment_tests.txt"


def _manifest_paths(path: Path) -> set[str]:
    entries: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        item = stripped.split("|", 1)[0].strip().replace("\\", "/").rstrip("/")
        if item:
            entries.add(item)
    return entries


def _is_excluded(relative_path: str, exclusions: set[str]) -> bool:
    normalized = relative_path.replace("\\", "/")
    for excluded in exclusions:
        if normalized == excluded or normalized.startswith(excluded + "/"):
            return True
    return False


def select() -> list[str]:
    exclusions = _manifest_paths(ENV_MANIFEST)
    selected: list[str] = []
    for candidate in sorted(TESTS.rglob("test_*.py")):
        rel = candidate.relative_to(ROOT).as_posix()
        if not _is_excluded(rel, exclusions):
            selected.append(rel)
    if not selected:
        raise SystemExit("No hermetic tests selected; refusing a false-green CI run")
    return selected


if __name__ == "__main__":
    print("\n".join(select()))
