# -*- coding: utf-8 -*-
"""
ZBC Phase 17 - Source Provenance / License Audit Tests

1. 无 INFRINGEMENT_RISK 模块进入生产路径
2. 所有第三方依赖有 License 记录
3. 源码中无未归因的第三方代码
"""
import json
import os
import re
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AUDIT_JSON = os.path.join(REPO_ROOT, "audit", "source_provenance.json")
AUDIT_REPORT = os.path.join(REPO_ROOT, "audit", "SOURCE-PROVENANCE-AUDIT.md")
REQUIREMENTS = os.path.join(REPO_ROOT, "requirements.txt")

EXCLUDE_DIRS = {
    ".venv", "node_modules", "nodejs", "dependencies", ".git",
    ".pytest_cache", "__pycache__", "data", "logs", "backups",
    "staging", "ref_gpt_v2", "_pitch_dump", "_ref_frames",
    "_shots", "_u", "_video_frames", "99-ARCHIVE", "序境",
    "docs", "audit", "tests", "static", "templates", "migrations",
    "alembic", "deliverables", "deployment", "docker", "00-GOVERNANCE",
    "02-ARCHITECTURE", "08-AUDIT", "2026-08-30", "2026-09-01",
    ".trae", ".trae-cn", ".vscode", ".skills-router", ".ollama",
    "edge-cdp-general", "edge-cdp-newaccount", "edge-cdp-profile",
    "edge-cdp-retinaut", "archive", "podcast", "contracts",
    "scripts",
}


def _load_audit_json():
    assert os.path.exists(AUDIT_JSON), f"审计 JSON 不存在: {AUDIT_JSON}"
    with open(AUDIT_JSON, "r", encoding="utf-8") as f:
        return json.load(f)


def _parse_requirements():
    packages = []
    with open(REQUIREMENTS, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            match = re.match(r"^([a-zA-Z0-9_.-]+)", line)
            if match:
                packages.append(match.group(1).lower())
    return packages


def _list_production_python_files():
    py_files = []
    for root, dirs, files in os.walk(REPO_ROOT):
        rel = os.path.relpath(root, REPO_ROOT)
        parts = rel.split(os.sep) if rel != "." else []
        if any(p in EXCLUDE_DIRS for p in parts):
            continue
        for f in files:
            if f.endswith(".py"):
                py_files.append(os.path.join(root, f))
    return py_files


# ============================================================
# Test 1: 审计产物存在性
# ============================================================

class TestAuditArtifactsExist:
    def test_audit_json_exists(self):
        assert os.path.exists(AUDIT_JSON)

    def test_audit_json_valid(self):
        data = _load_audit_json()
        assert "audit_metadata" in data
        assert "classification_summary" in data
        assert "python_dependencies" in data
        assert "infringement_risk" in data

    def test_audit_report_exists(self):
        assert os.path.exists(AUDIT_REPORT)

    def test_third_party_audit_exists(self):
        assert os.path.exists(os.path.join(REPO_ROOT, "THIRD_PARTY_LICENSE_AUDIT.md"))


# ============================================================
# Test 2: 所有第三方依赖有 License 记录
# ============================================================

class TestAllDependenciesHaveLicense:
    def test_requirements_parsed(self):
        pkgs = _parse_requirements()
        assert len(pkgs) >= 25

    def test_each_requirement_has_license_record(self):
        audit = _load_audit_json()
        recorded = {dep["name"].lower() for dep in audit.get("python_dependencies", [])}
        missing = [p for p in _parse_requirements() if p not in recorded]
        assert not missing, f"缺少 License 记录: {missing}"

    def test_no_gpl_or_agpl(self):
        stats = _load_audit_json().get("python_license_stats", {})
        assert stats.get("GPL_or_AGPL", 0) == 0
        assert stats.get("non_commercial_restricted", 0) == 0

    def test_all_commercial_use_allowed(self):
        for dep in _load_audit_json().get("python_dependencies", []):
            assert dep.get("commercial_use") is True, f"{dep['name']} 不允许商业使用"

    def test_nodejs_dependency_has_license(self):
        deps = _load_audit_json().get("nodejs_dependencies", [])
        assert len(deps) >= 1
        for dep in deps:
            assert dep.get("license")
            assert dep.get("commercial_use") is True


# ============================================================
# Test 3: 无 INFRINGEMENT_RISK 模块进入生产路径
# ============================================================

class TestNoInfringementRiskInProduction:
    def test_infringement_risk_recorded(self):
        assert len(_load_audit_json().get("infringement_risk", [])) > 0

    def test_infringement_risk_not_in_production(self):
        for risk in _load_audit_json().get("infringement_risk", []):
            assert risk.get("in_production_path") is False, f"{risk.get('file')} 在生产路径"

    def test_pitch_dump_not_really_imported(self):
        """_pitch_dump 不得被生产代码真正 import/open（排除列表中的引用不算）。"""
        violations = []
        for py_file in _list_production_python_files():
            try:
                with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if "_pitch_dump" in content:
                    rel = os.path.relpath(py_file, REPO_ROOT)
                    # 判断是否仅在排除/跳过/注释语境中出现
                    lines = [l.strip() for l in content.splitlines() if "_pitch_dump" in l]
                    is_exclude_only = all(
                        any(kw in l.lower() for kw in [
                            "exclude", "skip", "ignore", "排除", "跳过",
                            "blacklist", "filter_out", "not_in",
                        ]) or l.startswith("#") or l.startswith("'") or l.startswith('"')
                        for l in lines
                    )
                    if not is_exclude_only:
                        violations.append(rel)
            except Exception:
                continue
        assert not violations, f"生产代码真正引用了 _pitch_dump: {violations}"

    def test_infringement_files_are_text_only(self):
        for risk in _load_audit_json().get("infringement_risk", []):
            assert risk.get("file", "").endswith(".txt"), f"不是纯文本: {risk.get('file')}"

    def test_production_safety_flags(self):
        safety = _load_audit_json().get("production_path_safety", {})
        assert safety.get("infringement_risk_in_production_path") is False
        assert safety.get("derived_with_license_in_production_path") is False
        assert safety.get("third_party_source_modified") is False


# ============================================================
# Test 4: 源码中无未归因的第三方代码
# ============================================================

class TestNoUnattributedThirdPartyCode:
    SOURCE_MARKERS = [
        r"copied\s+from", r"adapted\s+from", r"derived\s+from",
        r"forked\s+from", r"ported\s+from", r"based\s+on\s+https?://",
        r"source:\s*https?://", r"来源[:：]\s*https?://",
    ]
    ATTRIBUTION_MARKERS = [
        r"license", r"许可", r"copyright", r"版权", r"MIT",
        r"Apache", r"BSD", r"attribution", r"归因",
    ]

    def test_production_files_scannable(self):
        assert len(_list_production_python_files()) > 50

    def test_source_markers_have_attribution(self):
        violations = []
        for py_file in _list_production_python_files():
            try:
                with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if any(re.search(p, content, re.IGNORECASE) for p in self.SOURCE_MARKERS):
                    if not any(re.search(p, content, re.IGNORECASE) for p in self.ATTRIBUTION_MARKERS):
                        violations.append(os.path.relpath(py_file, REPO_ROOT))
            except Exception:
                continue
        assert not violations, f"缺少归因: {violations}"

    def test_derived_files_have_attribution(self):
        for item in _load_audit_json().get("derived_with_license", []):
            assert item.get("attribution_present") is True
            assert item.get("source_repo")
            assert item.get("license")

    def test_derived_not_in_production(self):
        for item in _load_audit_json().get("derived_with_license", []):
            assert item.get("in_production_path") is False

    def test_no_media_crawler_source(self):
        """MediaCrawler 非商业源码不得出现在仓库中（license_audit.py 中的检测标记不算）。"""
        violations = []
        for root, dirs, files in os.walk(REPO_ROOT):
            rel = os.path.relpath(root, REPO_ROOT)
            parts = rel.split(os.sep) if rel != "." else []
            if any(p in EXCLUDE_DIRS for p in parts):
                continue
            for f in files:
                if not f.endswith(".py"):
                    continue
                fpath = os.path.join(root, f)
                # scripts/license_audit.py 是检测工具，含标记字符串是正常的
                if "license_audit" in f:
                    continue
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                        if "NON-COMMERCIAL LEARNING LICENSE" in fh.read():
                            violations.append(os.path.relpath(fpath, REPO_ROOT))
                except Exception:
                    continue
        assert not violations, f"存在 MediaCrawler 非商业源码: {violations}"


# ============================================================
# Test 5: Git / .gitignore 合规
# ============================================================

class TestGitAndGitignore:
    def test_gitignore_excludes_key_dirs(self):
        with open(os.path.join(REPO_ROOT, ".gitignore"), "r", encoding="utf-8") as f:
            content = f.read()
        for pattern in ["node_modules/", ".venv/", "dependencies/", "*.exe", "*.db"]:
            assert pattern in content, f".gitignore 缺少 {pattern}"

    def test_no_third_party_fork_in_history(self):
        git = _load_audit_json().get("git_history_audit", {})
        assert git.get("third_party_fork_found") is False
        assert git.get("third_party_merge_found") is False
        assert git.get("third_party_cherry_pick_found") is False


# ============================================================
# Test 6: 审计数据一致性
# ============================================================

class TestAuditDataConsistency:
    def test_python_dep_count_matches_requirements(self):
        audit = _load_audit_json()
        assert len(audit.get("python_dependencies", [])) == len(_parse_requirements())

    def test_infringement_count_matches_summary(self):
        audit = _load_audit_json()
        summary = audit["classification_summary"]["INFRINGEMENT_RISK"]["file_count"]
        assert summary == len(audit["infringement_risk"])

    def test_derived_count_matches_summary(self):
        audit = _load_audit_json()
        summary = audit["classification_summary"]["DERIVED_WITH_LICENSE"]["file_count"]
        assert summary == len(audit["derived_with_license"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
