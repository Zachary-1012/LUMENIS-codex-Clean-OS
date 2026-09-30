# -*- coding: utf-8 -*-
"""Current-source dependency and third-party provenance safeguards.

The dependency register, LICENSE, and active manifests are the only evidence
used here. A missing verification remains UNVERIFIED; it is never converted
into a historical audit PASS or a commercial-use grant.
"""
import json
import os
import re

import pytest


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REGISTER = os.path.join(REPO_ROOT, "00-GOVERNANCE", "THIRD-PARTY-COMPONENT-REGISTER.md")
LICENSE = os.path.join(REPO_ROOT, "LICENSE")
REQUIREMENTS = os.path.join(REPO_ROOT, "requirements.txt")
DEV_REQUIREMENTS = os.path.join(REPO_ROOT, "requirements-dev.txt")
PACKAGE_JSON = os.path.join(REPO_ROOT, "package.json")

EXCLUDE_DIRS = {
    ".venv", "node_modules", "nodejs", "dependencies", ".git",
    ".pytest_cache", "__pycache__", "data", "logs", "backups",
    "staging", "ref_gpt_v2", "_pitch_dump", "_ref_frames",
    "_shots", "_u", "_video_frames", "99-ARCHIVE", "序境",
    "docs", "audit", "tests", "static", "templates", "migrations",
    "alembic", "deliverables", "deployment", "docker", "00-GOVERNANCE",
    "02-ARCHITECTURE", "2026-08-30", "2026-09-01",
    ".trae", ".trae-cn", ".vscode", ".skills-router", ".ollama",
    "edge-cdp-general", "edge-cdp-newaccount", "edge-cdp-profile",
    "edge-cdp-retinaut", "archive", "podcast", "contracts",
    "scripts",
}


def _read_utf8(path):
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def _canonical_package_name(name):
    """Normalize package separators according to common Python/Node naming."""
    text = str(name).strip()
    # Register rows may carry an authoritative project link and an extra
    # version marker in the display cell. Parse the package identity only;
    # keep the link/license evidence in the remaining register columns.
    # The display name may itself contain an extras suffix such as
    # ``markitdown[pptx]``; stop at the closing bracket that is followed by
    # the Markdown URL delimiter rather than the inner extras bracket.
    text = re.sub(r"^\[(.*?)\]\([^)]*\)", r"\1", text)
    match = re.match(r"^([a-zA-Z0-9_.-]+)", text)
    return re.sub(r"[-_.]+", "-", (match.group(1) if match else text).strip().lower())


def _parse_requirements(path=REQUIREMENTS):
    packages = []
    for line in _read_utf8(path).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("-"):
            continue
        match = re.match(r"^([a-zA-Z0-9_.-]+)", line)
        if match:
            packages.append(_canonical_package_name(match.group(1)))
    return packages


def _register_section(start_heading, end_heading):
    text = _read_utf8(REGISTER)
    start = text.index(start_heading)
    end = text.index(end_heading, start)
    return text[start:end]


def _dependency_records(start_heading, end_heading):
    """Read component/license-status rows from the current markdown register."""
    records = {}
    for line in _register_section(start_heading, end_heading).splitlines():
        if not line.startswith("|") or line.startswith("| ---"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 5 or cells[0] == "Component":
            continue
        records[_canonical_package_name(cells[0])] = {
            "name": cells[0],
            "class": cells[1],
            "license_status": cells[4],
        }
    return records


def _all_manifest_records():
    return {
        "python": _dependency_records(
            "## 2. Python direct dependencies observed in `requirements.txt`",
            "## 3. Python development/test dependencies",
        ),
        "development": _dependency_records(
            "## 3. Python development/test dependencies",
            "## 4. Node direct dependencies",
        ),
        "node": _dependency_records(
            "## 4. Node direct dependencies",
            "## 5. Flutter direct dependencies observed in `app/pubspec.yaml`",
        ),
    }


def _list_production_python_files():
    py_files = []
    for root, dirs, files in os.walk(REPO_ROOT):
        rel = os.path.relpath(root, REPO_ROOT)
        parts = rel.split(os.sep) if rel != "." else []
        if any(part in EXCLUDE_DIRS for part in parts):
            continue
        for filename in files:
            if filename.endswith(".py"):
                py_files.append(os.path.join(root, filename))
    return py_files


def _git_history_provenance_status():
    """Current allowed evidence contains no verified Git-history audit record."""
    current_sources = "\n".join(
        _read_utf8(path) for path in (REGISTER, LICENSE, REQUIREMENTS)
    )
    has_verified_history_record = bool(re.search(
        r"(?is)(?:git\s+history|third.party\s+(?:fork|merge|cherry.pick))"
        r".{0,120}\b(?:verified|pass|clear)\b",
        current_sources,
    ))
    return "VERIFIED" if has_verified_history_record else "UNVERIFIED"


def _license_status(record):
    if not record:
        return "UNVERIFIED"
    status = record.get("license_status", "").strip()
    if status == "VERIFY_BEFORE_RELEASE":
        return "UNVERIFIED"
    return status or "UNVERIFIED"


class TestCurrentGovernanceSources:
    def test_current_register_license_and_manifests_exist(self):
        assert os.path.isfile(REGISTER)
        assert os.path.isfile(LICENSE)
        assert os.path.isfile(REQUIREMENTS)
        assert os.path.isfile(DEV_REQUIREMENTS)

    def test_register_explicitly_blocks_unverified_licenses(self):
        register = _read_utf8(REGISTER)
        assert "VERIFY_BEFORE_RELEASE" in register
        assert "Unknown licensing or unregistered shipped third-party code is a release blocker" in register
        assert "do not guess" in register


class TestManifestDependencyCoverage:
    def test_all_python_runtime_dependencies_are_registered(self):
        manifest = set(_parse_requirements())
        records = _all_manifest_records()["python"]
        missing = sorted(manifest - set(records))
        extra = sorted(set(records) - manifest)
        assert not missing, f"当前 requirements.txt 中的依赖未登记，许可状态必须保持 UNVERIFIED: {missing}"
        assert not extra, f"治理表登记了当前 manifest 中不存在的直接依赖: {extra}"

    def test_python_license_status_is_explicitly_unverified(self):
        records = _all_manifest_records()["python"]
        statuses = {name: _license_status(records.get(name)) for name in _parse_requirements()}
        assert set(statuses) == set(_parse_requirements())
        assert statuses
        # Only the two packages with a pinned upstream license record are
        # verified here. Every other package remains behind the release gate;
        # a license word in prose is not evidence of approval.
        verified = {
            "duckdb": (
                "MIT ([v1.5.5 license](https://github.com/duckdb/duckdb/blob/v1.5.5/LICENSE))"
            ),
            "markitdown": (
                "MIT ([v0.1.8 license](https://github.com/microsoft/markitdown/blob/v0.1.8/LICENSE)); "
                "python-pptx and transitive dependencies require separate notice/license reconciliation"
            ),
        }
        for name, status in statuses.items():
            assert status == verified.get(name, "UNVERIFIED"), (
                f"{name} 的许可证状态必须与当前权威登记一致，不能凭文本猜测"
            )

    def test_dev_dependencies_are_not_misclassified_as_production(self):
        dev_requirements = set(_parse_requirements(DEV_REQUIREMENTS)) - set(_parse_requirements())
        records = _all_manifest_records()["development"]
        assert dev_requirements <= set(records), f"未登记的开发/测试依赖: {sorted(dev_requirements - set(records))}"
        for name in dev_requirements:
            assert records[name]["class"] == "TEST ONLY"
            assert _license_status(records[name]) == "UNVERIFIED"

    def test_node_dependencies_are_registered_without_license_inference(self):
        package = json.loads(_read_utf8(PACKAGE_JSON))
        dependencies = {
            _canonical_package_name(name)
            for name in (package.get("dependencies") or {})
        }
        records = _all_manifest_records()["node"]
        assert dependencies == set(records)
        for name in dependencies:
            assert _license_status(records[name]) == "UNVERIFIED"


class TestCurrentProvenanceEvidence:
    SOURCE_MARKERS = [
        r"copied\s+from", r"adapted\s+from", r"derived\s+from",
        r"forked\s+from", r"ported\s+from", r"based\s+on\s+https?://",
        r"source:\s*https?://", r"来源[:：]\s*https?://",
    ]
    ATTRIBUTION_MARKERS = [
        r"license", r"许可", r"copyright", r"版权", r"MIT",
        r"Apache", r"BSD", r"attribution", r"归因",
    ]

    def test_historical_git_and_source_audit_status_is_unverified(self):
        """No current register/LICENSE/manifest entry proves a historical audit."""
        assert _git_history_provenance_status() == "UNVERIFIED"

    def test_current_register_requires_pre_release_reconciliation(self):
        register = _read_utf8(REGISTER)
        assert "Re-scan `requirements*.txt`" in register
        assert "vendored source" in register
        assert "Verify licenses from authoritative package/project sources" in register

    def test_production_files_scannable(self):
        assert len(_list_production_python_files()) > 50

    def test_source_markers_have_attribution(self):
        violations = []
        for py_file in _list_production_python_files():
            try:
                content = _read_utf8(py_file)
            except (OSError, UnicodeError):
                continue
            if any(re.search(pattern, content, re.IGNORECASE) for pattern in self.SOURCE_MARKERS):
                if not any(re.search(pattern, content, re.IGNORECASE) for pattern in self.ATTRIBUTION_MARKERS):
                    violations.append(os.path.relpath(py_file, REPO_ROOT))
        assert not violations, f"当前源码中的第三方来源标记缺少同文件归因: {violations}"

    def test_pitch_dump_not_really_imported(self):
        """_pitch_dump 不得被生产代码真正 import/open（排除列表中的引用不算）。"""
        violations = []
        for py_file in _list_production_python_files():
            try:
                content = _read_utf8(py_file)
            except (OSError, UnicodeError):
                continue
            if "_pitch_dump" in content:
                rel = os.path.relpath(py_file, REPO_ROOT)
                lines = [line.strip() for line in content.splitlines() if "_pitch_dump" in line]
                is_exclude_only = all(
                    any(keyword in line.lower() for keyword in [
                        "exclude", "skip", "ignore", "排除", "跳过",
                        "blacklist", "filter_out", "not_in",
                    ]) or line.startswith("#") or line.startswith("'") or line.startswith('"')
                    for line in lines
                )
                if not is_exclude_only:
                    violations.append(rel)
        assert not violations, f"生产代码真正引用了 _pitch_dump: {violations}"

    def test_license_keeps_third_party_terms_separate(self):
        license_text = _read_utf8(LICENSE)
        assert "LUMENIS Materials" in license_text
        assert "does not replace, restrict, expand, relicense or claim ownership of" in license_text
        assert re.search(
            r"subject to their respective copyright,\s*license, attribution, notice and usage terms",
            license_text,
        )
        assert "unresolved for release purposes rather than inferred" in license_text

    def test_no_media_crawler_noncommercial_source_marker(self):
        """Reject the known non-commercial source marker in production Python files."""
        violations = []
        for root, dirs, files in os.walk(REPO_ROOT):
            rel = os.path.relpath(root, REPO_ROOT)
            parts = rel.split(os.sep) if rel != "." else []
            if any(part in EXCLUDE_DIRS for part in parts):
                continue
            for filename in files:
                if not filename.endswith(".py") or "license_audit" in filename:
                    continue
                file_path = os.path.join(root, filename)
                try:
                    if "NON-COMMERCIAL LEARNING LICENSE" in _read_utf8(file_path):
                        violations.append(os.path.relpath(file_path, REPO_ROOT))
                except (OSError, UnicodeError):
                    continue
        assert not violations, f"生产 Python 代码包含已知非商业源码标记: {violations}"


class TestGitAndGitignore:
    def test_gitignore_excludes_key_runtime_artifacts(self):
        content = _read_utf8(os.path.join(REPO_ROOT, ".gitignore"))
        for pattern in ["node_modules/", ".venv/", "dependencies/", "*.exe", "*.db"]:
            assert pattern in content, f".gitignore 缺少 {pattern}"

    def test_git_history_is_not_claimed_as_pass(self):
        assert _git_history_provenance_status() == "UNVERIFIED"


class TestDependencyEvidenceConsistency:
    def test_register_count_matches_runtime_manifest(self):
        records = _all_manifest_records()["python"]
        assert len(records) == len(_parse_requirements())

    def test_all_registered_license_states_have_release_gate(self):
        verified = {
            "duckdb": "MIT ([v1.5.5 license](https://github.com/duckdb/duckdb/blob/v1.5.5/LICENSE))",
            "markitdown": (
                "MIT ([v0.1.8 license](https://github.com/microsoft/markitdown/blob/v0.1.8/LICENSE)); "
                "python-pptx and transitive dependencies require separate notice/license reconciliation"
            ),
        }
        for source, records in _all_manifest_records().items():
            for dependency, record in records.items():
                status = record["license_status"]
                expected = verified.get(dependency, "VERIFY_BEFORE_RELEASE")
                assert status == expected, f"{source}:{dependency} 缺少可追溯许可证据或 release gate"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
