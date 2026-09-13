"""Select clean-checkout pytest files for LUMENIS CI.

The selector enumerates repository test files and subtracts two explicit sources:
1. environment/live suites from ``ci_environment_tests.txt``;
2. script-style files already declared in ``conftest.py::collect_ignore``.

It prints one repository-relative path per line for the workflow to pass explicitly
to pytest. Environment/live exclusion is not PASS; those suites remain release
evidence as documented in CI_TEST_TIERS.md.
"""
from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
ENV_MANIFEST = TESTS / "ci_environment_tests.txt"
CONFTEST = TESTS / "conftest.py"


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


def _pytest_collect_ignores(path: Path) -> set[str]:
    """Read ``collect_ignore`` statically without importing conftest side effects."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(t, ast.Name) and t.id == "collect_ignore" for t in targets):
            continue
        value = ast.literal_eval(node.value)
        if not isinstance(value, (list, tuple, set)):
            raise SystemExit("tests/conftest.py collect_ignore must be a literal sequence")
        return {f"tests/{str(item).replace(chr(92), '/').lstrip('/')}" for item in value}
    return set()


def _is_excluded(relative_path: str, exclusions: set[str]) -> bool:
    normalized = relative_path.replace("\\", "/")
    for excluded in exclusions:
        if normalized == excluded or normalized.startswith(excluded + "/"):
            return True
    return False


def select() -> list[str]:
    exclusions = _manifest_paths(ENV_MANIFEST) | _pytest_collect_ignores(CONFTEST)
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
