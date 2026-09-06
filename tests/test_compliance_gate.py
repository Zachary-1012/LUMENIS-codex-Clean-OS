# -*- coding: utf-8 -*-
"""P1-H ComplianceGate 测试：多法域矩阵裁决（BLOCK/REVIEW/PASS）+ safe_collection 可选并入。"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from compliance_gate import BLOCK, PASS, REVIEW, ComplianceGate  # noqa: E402


@pytest.fixture
def gate():
    return ComplianceGate()


def test_block_secret(gate):
    r = gate.gate(action="store_secret", jurisdiction="CN")
    assert r["overall"] == BLOCK
    assert r["ok"] is False


def test_block_bypass_captcha(gate):
    assert gate.gate(action="bypass_captcha")["overall"] == BLOCK


def test_review_public_scrape_cn(gate):
    r = gate.gate(action="scrape_public_notes", data_type="note", jurisdiction="CN")
    assert r["overall"] == REVIEW


def test_review_eu_has_extra(gate):
    r = gate.gate(action="scrape_public_notes", jurisdiction="EU")
    assert r["overall"] == REVIEW
    ids = [f["id"] for f in r["findings"]]
    assert "SC-04" in ids  # EU 附加 GDPR 规则


def test_pass_unknown_action(gate):
    assert gate.gate(action="ping_health")["overall"] == PASS


def test_review_pii(gate):
    assert gate.gate(action="collect_pii", jurisdiction="CN")["overall"] == REVIEW


def test_matrix_coverage(gate):
    m = gate.matrix()
    assert "CN" in m["jurisdictions"] and "EU" in m["jurisdictions"]
    assert m["grid"]["CN"]["web_scraping"] >= 1


def test_scrape_action_merges_local_guard(gate):
    # safe_collection 可导入则并入，不可导入也不阻塞
    r = gate.gate(action="scrape_public_notes", jurisdiction="CN")
    assert "local_guard" in r
