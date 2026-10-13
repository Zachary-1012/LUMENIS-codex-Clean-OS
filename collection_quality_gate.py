# -*- coding: utf-8 -*-
"""
采集五步质量门禁（P0 红线：Source→Raw→Dedup→Subject Filter→Canonical）
========================================================================
每步：输入校验→处理→输出校验→失败记录（写入 collection_quality_log 表）。
任何一步失败不得静默丢弃，必须记录失败状态+原因+原始数据引用。

五步：
1. Source 校验：URL 非空、平台合法、账号信息存在
2. Raw 校验：原始字段非空、内容哈希可计算
3. Dedup 校验：content_hash + platform_id 组合去重，记录去重决策
4. Subject Filter 校验：subject_hit() 结果可追溯，过滤原因记录
5. Canonical 校验：CanonicalRecord 所有必填字段完整
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from lumenis.shared.database import DatabaseRepository
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# 合法平台列表
VALID_PLATFORMS = {
    "xiaohongshu", "xhs", "rednote", "douyin", "weibo", "bilibili",
    "zhihu", "instagram", "facebook", "dianping", "smzdm",
    "sogou_search", "google", "bing_search", "baidu_search",
    "sogou_wechat",
}

# 五步名称
STEP_SOURCE = "source"
STEP_RAW = "raw"
STEP_DEDUP = "dedup"
STEP_SUBJECT = "subject_filter"
STEP_CANONICAL = "canonical"

ALL_STEPS = [STEP_SOURCE, STEP_RAW, STEP_DEDUP, STEP_SUBJECT, STEP_CANONICAL]

# 质量日志表
QUALITY_LOG_TABLE = "collection_quality_log"

QUALITY_LOG_DDL = f"""
CREATE TABLE IF NOT EXISTS {QUALITY_LOG_TABLE} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT DEFAULT '',
    step TEXT NOT NULL,
    status TEXT NOT NULL,  -- pass/fail/skipped
    reason TEXT DEFAULT '',
    source_platform TEXT DEFAULT '',
    content_hash TEXT DEFAULT '',
    canonical_id TEXT DEFAULT '',
    raw_ref TEXT DEFAULT '',
    details TEXT DEFAULT '',  -- JSON 详情
    created_at TEXT DEFAULT ''
);
"""

QUALITY_LOG_INDEXES = [
    f"CREATE INDEX IF NOT EXISTS idx_quality_log_step ON {QUALITY_LOG_TABLE}(step, status)",
    f"CREATE INDEX IF NOT EXISTS idx_quality_log_hash ON {QUALITY_LOG_TABLE}(content_hash)",
    f"CREATE INDEX IF NOT EXISTS idx_quality_log_run ON {QUALITY_LOG_TABLE}(run_id)",
]


def ensure_quality_log_table(db_path: str) -> None:
    """确保质量日志表存在（幂等）。"""
    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    con = DatabaseRepository(db_path).connect(timeout=15)
    try:
        con.execute(QUALITY_LOG_DDL)
        for idx in QUALITY_LOG_INDEXES:
            con.execute(idx)
        con.commit()
    finally:
        con.close()


def _now_str() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _content_hash(content: Any) -> str:
    raw = json.dumps(content, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


@dataclass
class GateResult:
    """单步门禁结果。"""
    step: str
    passed: bool
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CollectionGateResult:
    """五步门禁总结果。"""
    passed: bool
    failed_step: Optional[str] = None
    results: List[GateResult] = field(default_factory=list)
    content_hash: str = ""
    canonical_id: str = ""
    dedup_decision: str = ""  # new/duplicate
    subject_decision: str = ""  # hit/miss

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "failed_step": self.failed_step,
            "content_hash": self.content_hash,
            "canonical_id": self.canonical_id,
            "dedup_decision": self.dedup_decision,
            "subject_decision": self.subject_decision,
            "steps": [
                {"step": r.step, "passed": r.passed, "reason": r.reason}
                for r in self.results
            ],
        }


class CollectionQualityGate:
    """采集五步质量门禁。

    用法：
        gate = CollectionQualityGate(db_path)
        result = gate.validate(raw_data, platform, url, author_info)
        if not result.passed:
            log.warning(f"采集门禁失败: {result.failed_step}")
    """

    def __init__(self, db_path: str, run_id: str = ""):
        self.db_path = db_path
        self.run_id = run_id or f"run_{int(time.time())}"
        ensure_quality_log_table(db_path)

    def _log(self, con: sqlite3.Connection, step: str, status: str,
             reason: str = "", platform: str = "", content_hash: str = "",
             canonical_id: str = "", raw_ref: str = "", details: Dict = None):
        """记录一步门禁结果到日志表。"""
        con.execute(
            f"INSERT INTO {QUALITY_LOG_TABLE} "
            f"(run_id, step, status, reason, source_platform, content_hash, "
            f"canonical_id, raw_ref, details, created_at) "
            f"VALUES (?,?,?,?,?,?,?,?,?,?)",
            (self.run_id, step, status, reason, platform, content_hash,
             canonical_id, raw_ref, json.dumps(details or {}, ensure_ascii=False),
             _now_str()),
        )

    # ---- Step 1: Source 校验 ----
    def validate_source(self, raw: Dict[str, Any], platform: str,
                        url: str, author_info: Dict[str, Any]) -> GateResult:
        """Source 校验：URL 非空、平台合法、账号信息存在。"""
        if not url or not str(url).strip():
            return GateResult(STEP_SOURCE, False, "URL 为空")
        if platform not in VALID_PLATFORMS:
            return GateResult(STEP_SOURCE, False, f"非法平台: {platform}")
        if not author_info or not (author_info.get("author_id") or author_info.get("author_name")):
            return GateResult(STEP_SOURCE, False, "账号信息缺失（author_id/author_name 均为空）")
        return GateResult(STEP_SOURCE, True, "source 校验通过")

    # ---- Step 2: Raw 校验 ----
    def validate_raw(self, raw: Dict[str, Any]) -> Tuple[GateResult, str]:
        """Raw 校验：原始字段非空、内容哈希可计算。"""
        title = str(raw.get("title") or "").strip()
        content = str(raw.get("content") or raw.get("body") or "").strip()
        if not title and not content:
            return GateResult(STEP_RAW, False, "title 和 content 均为空"), ""
        try:
            ch = _content_hash({"title": title, "content": content, "url": raw.get("url", "")})
            if not ch:
                return GateResult(STEP_RAW, False, "内容哈希计算失败"), ""
            return GateResult(STEP_RAW, True, "raw 校验通过"), ch
        except Exception as e:
            return GateResult(STEP_RAW, False, f"内容哈希计算异常: {e}"), ""

    # ---- Step 3: Dedup 校验 ----
    def validate_dedup(self, con: sqlite3.Connection, content_hash: str,
                       platform: str, canonical_id: str = "") -> Tuple[GateResult, str]:
        """Dedup 校验：content_hash + platform_id 组合去重，记录决策。"""
        if not content_hash:
            return GateResult(STEP_DEDUP, False, "content_hash 为空，无法去重"), "error"
        try:
            from canonical_data import is_duplicate
            dup = is_duplicate(con, content_hash, platform, canonical_id=canonical_id)
            decision = "duplicate" if dup else "new"
            if dup:
                return GateResult(STEP_DEDUP, True, f"判定为重复内容（content_hash+platform 匹配）",
                                  {"decision": decision}), decision
            return GateResult(STEP_DEDUP, True, "无重复", {"decision": decision}), decision
        except Exception as e:
            return GateResult(STEP_DEDUP, False, f"去重校验异常: {e}"), "error"

    # ---- Step 4: Subject Filter 校验 ----
    def validate_subject(self, raw: Dict[str, Any]) -> Tuple[GateResult, str]:
        """Subject Filter 校验：subject_hit() 结果可追溯，过滤原因记录。"""
        try:
            from subject_rules import subject_hit
            title = str(raw.get("title") or "")
            body = str(raw.get("content") or raw.get("body") or "")
            keyword = str(raw.get("source_keyword") or "")
            hit = subject_hit(title=title, body=body, content=body, source_keyword=keyword)
            decision = "hit" if hit else "miss"
            if hit:
                return GateResult(STEP_SUBJECT, True, "主体命中", {"decision": decision}), decision
            return GateResult(STEP_SUBJECT, True, "主体未命中（不阻断，标记为低相关）",
                              {"decision": decision}), decision
        except Exception as e:
            return GateResult(STEP_SUBJECT, False, f"主体过滤异常: {e}"), "error"

    # ---- Step 5: Canonical 校验 ----
    def validate_canonical(self, record: Any) -> GateResult:
        """Canonical 校验：必填字段完整。"""
        required = ["canonical_id", "content_hash", "source_platform", "title", "content"]
        missing = []
        for f in required:
            val = getattr(record, f, None)
            if val is None or (isinstance(val, str) and not val.strip()):
                if f == "content":
                    continue  # content 允许为空（有些内容只有标题）
                missing.append(f)
        if missing:
            return GateResult(STEP_CANONICAL, False, f"必填字段缺失: {', '.join(missing)}")
        return GateResult(STEP_CANONICAL, True, "canonical 校验通过")

    # ---- 总入口 ----
    def validate(self, raw: Dict[str, Any], platform: str, url: str,
                 author_info: Dict[str, Any], con: sqlite3.Connection = None,
                 canonical_record: Any = None) -> CollectionGateResult:
        """执行五步门禁。任何一步失败记录日志并返回。"""
        own_con = con is None
        if own_con:
            con = DatabaseRepository(self.db_path).connect(timeout=15)
        try:
            results = []
            content_hash = ""
            dedup_decision = ""
            subject_decision = ""
            canonical_id = getattr(canonical_record, 'canonical_id', '') if canonical_record else ""

            # Step 1: Source
            r = self.validate_source(raw, platform, url, author_info)
            results.append(r)
            self._log(con, STEP_SOURCE, "pass" if r.passed else "fail",
                      r.reason, platform, "", canonical_id, "", r.details)
            if not r.passed:
                con.commit()
                return CollectionGateResult(False, STEP_SOURCE, results, "", canonical_id)

            # Step 2: Raw
            r, content_hash = self.validate_raw(raw)
            results.append(r)
            self._log(con, STEP_RAW, "pass" if r.passed else "fail",
                      r.reason, platform, content_hash, canonical_id, "", r.details)
            if not r.passed:
                con.commit()
                return CollectionGateResult(False, STEP_RAW, results, content_hash, canonical_id)

            # Step 3: Dedup
            r, dedup_decision = self.validate_dedup(con, content_hash, platform, canonical_id)
            results.append(r)
            self._log(con, STEP_DEDUP, "pass" if r.passed else "fail",
                      r.reason, platform, content_hash, canonical_id, "",
                      {**r.details, "decision": dedup_decision})
            if not r.passed:
                con.commit()
                return CollectionGateResult(False, STEP_DEDUP, results, content_hash, canonical_id,
                                            dedup_decision=dedup_decision)

            # Step 4: Subject Filter
            r, subject_decision = self.validate_subject(raw)
            results.append(r)
            self._log(con, STEP_SUBJECT, "pass" if r.passed else "fail",
                      r.reason, platform, content_hash, canonical_id, "",
                      {**r.details, "decision": subject_decision})
            if not r.passed:
                con.commit()
                return CollectionGateResult(False, STEP_SUBJECT, results, content_hash, canonical_id,
                                            dedup_decision=dedup_decision,
                                            subject_decision=subject_decision)

            # Step 5: Canonical
            if canonical_record is not None:
                r = self.validate_canonical(canonical_record)
                results.append(r)
                self._log(con, STEP_CANONICAL, "pass" if r.passed else "fail",
                          r.reason, platform, content_hash, canonical_id, "", r.details)
                if not r.passed:
                    con.commit()
                    return CollectionGateResult(False, STEP_CANONICAL, results, content_hash,
                                                canonical_id, dedup_decision, subject_decision)
            else:
                results.append(GateResult(STEP_CANONICAL, True, "skipped（无 canonical_record）"))
                self._log(con, STEP_CANONICAL, "skipped", "无 canonical_record",
                          platform, content_hash, canonical_id)

            con.commit()
            return CollectionGateResult(True, None, results, content_hash, canonical_id,
                                        dedup_decision, subject_decision)
        finally:
            if own_con:
                con.close()


def get_quality_logs(db_path: str, step: str = "", status: str = "",
                     run_id: str = "", limit: int = 100) -> List[Dict[str, Any]]:
    """查询质量日志。"""
    ensure_quality_log_table(db_path)
    con = DatabaseRepository(db_path).connect(timeout=15)
    con.row_factory = sqlite3.Row
    try:
        sql = f"SELECT * FROM {QUALITY_LOG_TABLE}"
        conds = []
        params = []
        if step:
            conds.append("step=?")
            params.append(step)
        if status:
            conds.append("status=?")
            params.append(status)
        if run_id:
            conds.append("run_id=?")
            params.append(run_id)
        if conds:
            sql += " WHERE " + " AND ".join(conds)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)
        rows = con.execute(sql, tuple(params)).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()
