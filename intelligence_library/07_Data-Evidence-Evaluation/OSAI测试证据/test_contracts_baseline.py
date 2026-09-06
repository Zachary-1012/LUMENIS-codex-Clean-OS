# -*- coding: utf-8 -*-
"""OSAI 最小测试基线：契约与 Baseline 报告完整性（P0-5）"""
import os
import re
import pytest

OSAI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel):
    p = os.path.join(OSAI, rel)
    assert os.path.exists(p), f"missing: {rel}"
    with open(p, encoding="utf-8") as fh:
        return fh.read()


class TestContracts:
    """契约完整性：每份 Contract 必须含 Producer/Consumer/Status/Acceptance。"""

    def test_contract_files_exist(self):
        d = os.path.join(OSAI, "contracts")
        files = [f for f in os.listdir(d) if f.endswith(".md")]
        assert len(files) >= 1, "contracts 目录必须有至少一份契约"
        assert any("BROWSER" in f for f in files), "缺少 Browser Runtime Contract"

    def test_browser_contract_content(self):
        c = _read(os.path.join("contracts", "CTR-BROWSER-RUNTIME-P0-01.md"))
        for key in ("Producer", "Consumer", "Status", "Acceptance"):
            assert key in c, f"契约缺少 {key}"
        for layer in ("Browser Contract", "Browser Router", "Browser Adapter", "Browser Provider"):
            assert layer in c, f"契约缺少分层 {layer}"

    def test_event_cluster_contract_content(self):
        c = _read(os.path.join("contracts", "CTR-EVENT-CLUSTER-P1-01.md"))
        assert "Producer" in c and "Consumer" in c and "Acceptance" in c

    def test_no_secrets_in_contracts(self):
        contracts_dir = os.path.join(OSAI, "contracts")
        secret_pats = (r"AKIA[0-9A-Z]{16}", r"sk-[A-Za-z0-9]{20}",
                       r"-----BEGIN.*PRIVATE KEY-----")
        scanned = 0
        for root, _dirs, files in os.walk(contracts_dir):
            for fn in files:
                if not fn.endswith((".md", ".json")):
                    continue
                rel = os.path.relpath(os.path.join(root, fn), OSAI)
                c = _read(rel)
                scanned += 1
                for pat in secret_pats:
                    assert not re.search(pat, c), f"契约 {rel} 疑似含密钥"
        assert scanned >= 1, "contracts 目录至少要扫描到一份契约文件"


class TestBaselineReport:
    """AI 编程施工报告 V1 完整性。"""

    def test_report_exists(self):
        _read(os.path.join("baseline", "AI-PROGRAMMING-CONSTRUCTION-REPORT-V1-20260902.md"))

    def test_report_has_all_sections(self):
        r = _read(os.path.join("baseline", "AI-PROGRAMMING-CONSTRUCTION-REPORT-V1-20260902.md"))
        sections = ["Baseline Snapshot", "Capability Matrix", "P0 差距矩阵",
                    "Release Gate Result", "代码修改清单"]
        for s in sections:
            assert s in r, f"报告缺少章节: {s}"

    def test_report_marks_not_complete_honestly(self):
        r = _read(os.path.join("baseline", "AI-PROGRAMMING-CONSTRUCTION-REPORT-V1-20260902.md"))
        assert "NOT COMPLETE" in r, "Release Gate 必须如实标记 NOT COMPLETE（审计阶段）"


class TestLearningFeed:
    def test_case_study_exists(self):
        _read(os.path.join("learning-feed", "INDUSTRY-CASE-STUDY-MULTIAGENT-OS-20260902.md"))