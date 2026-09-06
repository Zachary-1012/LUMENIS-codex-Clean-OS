# -*- coding: utf-8 -*-
"""[Legacy] ComplianceGate（P1-H｜统一合规 Gate · Legacy 保留）。

⚠️ Legacy 模块：Phase 3 后，权限控制由 permission_gate.py 统一，合规裁决仍由本模块负责（多法域 BLOCK/REVIEW/PASS）。两者互补：PermissionGate 管操作权限，ComplianceGate 管法域合规，不替代、不删除。

ComplianceGate（P1-H｜统一合规 Gate）。

把散落在 safe_collection / ai_governance 等的合规能力统一编排为「动作 → 多法域裁决」Gate，
输出 BLOCK / REVIEW / PASS，并对不确定项 BLOCK / HUMAN REVIEW（基线 §18）。

规则矩阵位于 config/compliance-rules.json（法域 × 维度），本模块只做确定性裁决：
  任一规则命中 BLOCK  -> 整体 BLOCK（禁止执行）
  仅命中 REVIEW       -> 整体 REVIEW（需人工/法务复核后放行）
  无命中              -> PASS

维度：data_protection / personal_info / ai / web_scraping / cross_border /
      data_minimization / copyright
法域：CN / HK / EU / UK / US（* = 全域适用）

可选对接：若采集动作以 scrape_* 开头且 platform_adapters.safe_collection 可用，
则并入其本地守卫结论（try/except 可选，不因组件缺失阻塞）。

用法：
  gate = ComplianceGate()
  result = gate.gate(action='scrape_public_notes', data_type='note', jurisdiction='CN')
  # {'ok': True/False, 'overall': 'PASS'/'REVIEW'/'BLOCK', 'findings': [...], ...}
"""
import json
import logging
import os

BLOCK = "BLOCK"
REVIEW = "REVIEW"
PASS = "PASS"

logger = logging.getLogger(__name__)

_DEFAULT_RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "config", "compliance-rules.json")


class ComplianceGate:
    def __init__(self, rules_path=None):
        self.rules_path = rules_path or _DEFAULT_RULES_PATH
        self.rules = self._load()

    def _load(self):
        if not os.path.exists(self.rules_path):
            return {"rules": []}
        try:
            return json.load(open(self.rules_path, encoding="utf-8"))
        except Exception:
            return {"rules": []}

    def evaluate(self, action, data_type=None, jurisdiction="CN"):
        """返回命中规则列表（含 verdict）。"""
        findings = []
        for rule in self.rules.get("rules", []):
            acts = rule.get("action")
            if isinstance(acts, str):
                acts = [acts]
            if action not in acts:
                continue
            jr = rule.get("jurisdiction", "*")
            if jr not in ("*", jurisdiction):
                continue
            if rule.get("data_type") and data_type and rule["data_type"] != data_type:
                continue
            findings.append(rule)
        return findings

    def _overall(self, findings):
        if any(f.get("verdict") == BLOCK for f in findings):
            return BLOCK
        if findings:
            return REVIEW
        return PASS

    def gate(self, action, data_type=None, jurisdiction="CN", extra=None):
        """统一裁决入口。返回结构化结果（BLOCK 则 ok=False 并给出阻断原因）。"""
        findings = self.evaluate(action, data_type, jurisdiction)
        overall = self._overall(findings)
        detail = {
            "action": action,
            "data_type": data_type,
            "jurisdiction": jurisdiction,
            "overall": overall,
            "findings": [
                {"id": f.get("id"), "dimension": f.get("dimension"),
                 "verdict": f.get("verdict"), "reason": f.get("reason"),
                 "ref": f.get("ref")}
                for f in findings
            ],
        }
        # 可选并入 safe_collection 本地守卫（采集动作）
        if action.startswith("scrape_") or action.startswith("collect_"):
            self._merge_local_guard(action, detail)
            if detail.get("local_guard") == BLOCK:
                detail["overall"] = BLOCK
                detail["ok"] = False
                return detail
        detail["ok"] = overall != BLOCK
        return detail

    def _merge_local_guard(self, action, detail):
        try:
            from platform_adapters import safe_collection  # noqa: F401
            # safe_collection 具体接口以仓库实际为准；仅当存在通用守卫函数才并入。
            fn = getattr(safe_collection, "guard", None) or getattr(safe_collection, "check", None)
            if callable(fn):
                try:
                    out = fn(action)
                    verdict = getattr(out, "verdict", None) or (out if isinstance(out, str) else None)
                    detail["local_guard"] = verdict
                except Exception:
                    detail["local_guard"] = None
            else:
                detail["local_guard"] = None
        except Exception:
            detail["local_guard"] = None

    def matrix(self):
        """返回 法域 × 维度 覆盖矩阵（文档/展示用，真实来自规则文件）。"""
        dims = self.rules.get("dimensions", [])
        jrs = self.rules.get("jurisdictions", [])
        grid = {}
        for j in jrs:
            grid[j] = {}
            for d in dims:
                n = sum(1 for r in self.rules.get("rules", [])
                        if r.get("dimension") == d and r.get("jurisdiction") in ("*", j))
                grid[j][d] = n
        return {"jurisdictions": jrs, "dimensions": dims, "grid": grid}
