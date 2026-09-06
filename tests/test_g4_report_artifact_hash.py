# -*- coding: utf-8 -*-
"""G4 单测：报告 artifact_hash 真实计算落库

验证：
1. 生成报告时 hash 非空
2. hash 可复现（相同内容 → 相同 hash）
3. 历史报告 hash 为空不报错
4. hash 不一致能被检测
"""
import json

import pytest

import report_artifact as ra


class TestG4HashComputation:
    """G4: hash 计算"""

    def test_build_metadata_hash_non_empty(self):
        """生成报告元数据时 artifact_hash 应非空。"""
        report = {"report_type": "daily", "report_date": "2026-09-06", "total_notes": 100}
        meta = ra.build_artifact_metadata("daily", "2026-09-06", "2026-09-06", report_data=report)
        assert meta["artifact_hash"] != ""
        assert len(meta["artifact_hash"]) == 64  # SHA-256 hex

    def test_hash_reproducible(self):
        """相同内容应生成相同 hash（可复现）。"""
        report = {"report_type": "daily", "report_date": "2026-09-06", "total_notes": 100}
        meta1 = ra.build_artifact_metadata("daily", "2026-09-06", "2026-09-06", report_data=report)
        meta2 = ra.build_artifact_metadata("daily", "2026-09-06", "2026-09-06", report_data=report)
        assert meta1["artifact_hash"] == meta2["artifact_hash"]

    def test_hash_changes_with_content(self):
        """内容变化时 hash 应变化。"""
        r1 = {"report_type": "daily", "total_notes": 100}
        r2 = {"report_type": "daily", "total_notes": 200}
        m1 = ra.build_artifact_metadata("daily", "2026-09-06", "2026-09-06", report_data=r1)
        m2 = ra.build_artifact_metadata("daily", "2026-09-06", "2026-09-06", report_data=r2)
        assert m1["artifact_hash"] != m2["artifact_hash"]

    def test_hash_excludes_meta_keys(self):
        """hash 计算应排除 artifact_hash/generated_at/data_version 等 meta 键。"""
        report = {"report_type": "daily", "total_notes": 100}
        meta = ra.build_artifact_metadata("daily", "2026-09-06", "2026-09-06", report_data=report)
        # 把 meta 加入 report 后重新验证，hash 应一致
        full_report = dict(report)
        full_report.update(meta)
        vr = ra.verify_report_hash(full_report)
        assert vr["status"] == "verified"
        assert vr["valid"] is True


class TestG4HashVerification:
    """G4: hash 一致性验证"""

    def test_verified_hash(self):
        """未修改的报告 hash 应验证通过。"""
        report = {"report_type": "daily", "report_date": "2026-09-06", "total_notes": 100}
        meta = ra.build_artifact_metadata("daily", "2026-09-06", "2026-09-06", report_data=report)
        full = dict(report)
        full.update(meta)
        vr = ra.verify_report_hash(full)
        assert vr["valid"] is True
        assert vr["status"] == "verified"

    def test_mismatch_detected(self):
        """修改内容后 hash 应检测为不一致。"""
        report = {"report_type": "daily", "total_notes": 100}
        meta = ra.build_artifact_metadata("daily", "2026-09-06", "2026-09-06", report_data=report)
        full = dict(report)
        full.update(meta)
        full["total_notes"] = 999  # 修改内容
        vr = ra.verify_report_hash(full)
        assert vr["valid"] is False
        assert vr["status"] == "mismatch"

    def test_historical_empty_hash_no_error(self):
        """历史报告 hash 为空时不报错，标记 historical_empty。"""
        report = {"report_type": "daily", "total_notes": 100, "artifact_hash": ""}
        vr = ra.verify_report_hash(report)
        assert vr["valid"] is True  # 空 hash 不视为失败
        assert vr["status"] == "historical_empty"

    def test_none_hash_no_error(self):
        """artifact_hash 为 None 时不报错。"""
        report = {"report_type": "daily", "total_notes": 100, "artifact_hash": None}
        vr = ra.verify_report_hash(report)
        assert vr["status"] == "historical_empty"

    def test_none_report_handled(self):
        """None 报告不抛出异常。"""
        vr = ra.verify_report_hash(None)
        assert vr["status"] == "error"
        assert vr["valid"] is False

    def test_expected_hash_matches_actual(self):
        """验证返回的 expected_hash 与 actual_hash 在通过时相等。"""
        report = {"report_type": "daily", "total_notes": 100}
        meta = ra.build_artifact_metadata("daily", "2026-09-06", "2026-09-06", report_data=report)
        full = dict(report)
        full.update(meta)
        vr = ra.verify_report_hash(full)
        assert vr["expected_hash"] == vr["actual_hash"]


class TestG4ComputeHash:
    """G4: compute_hash 基础功能"""

    def test_sha256_length(self):
        """SHA-256 hash 应为 64 位十六进制字符串。"""
        h = ra.compute_hash(b"test data")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_deterministic(self):
        """相同输入应生成相同 hash。"""
        assert ra.compute_hash(b"abc") == ra.compute_hash(b"abc")

    def test_different_inputs_different_hash(self):
        """不同输入应生成不同 hash。"""
        assert ra.compute_hash(b"abc") != ra.compute_hash(b"abd")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
