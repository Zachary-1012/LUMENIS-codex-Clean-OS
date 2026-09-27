# -*- coding: utf-8 -*-
"""数据质量门 DataQualityGate（研究自 OpenDQV write-time enforcement，落地 ZBC）。

范式（OpenDQV README）：
  - Write-time validation：写入前校验，坏记录 422 拒绝（per-field errors），不存 payload
  - Contract YAML：name/version/owner/rules；规则 severity=error(阻止)/warning(标记放行)
  - 哲学：Trust is easier to build than to repair——写入时 422 比三周后的数据事故便宜

ZBC 三层数据治理分工：
  schema_registry      DB 结构反射（表/列类型）—— 结构层
  DataQualityGate      业务语义规则（必填/格式/取值/范围/日期/长度）—— 语义层（本模块）
  (报告/采集)          下游使用方

用法：
  gate = DataQualityGate(r"config/data-contracts")
  res = gate.validate("note", {...})   # -> {"valid":bool,"errors":[],"warnings":[]}
"""
import datetime
import io
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONTRACTS_DIR = os.path.join(ROOT, "config", "data-contracts")


# ---- 内置规则 ----
def _rule_not_empty(v, p):
    return v is not None and str(v).strip() != "", "字段不能为空"


def _rule_regex(v, p):
    if v is None:
        return False, "字段缺失"
    ok = bool(re.search(p["pattern"], str(v)))
    return ok, "格式不匹配: %s" % p["pattern"]


def _rule_min(v, p):
    if v is None:
        return False, "字段缺失"
    return float(v) >= p["min"], "不能小于 %s" % p["min"]


def _rule_max(v, p):
    if v is None:
        return False, "字段缺失"
    return float(v) <= p["max"], "不能大于 %s" % p["max"]


def _rule_range(v, p):
    if v is None:
        return False, "字段缺失"
    n = float(v)
    return p["min"] <= n <= p["max"], "须在 [%s,%s]" % (p["min"], p["max"])


def _rule_min_length(v, p):
    if v is None:
        return False, "字段缺失"
    return len(str(v)) >= p["min_length"], "长度不能小于 %s" % p["min_length"]


def _rule_max_length(v, p):
    if v is None:
        return False, "字段缺失"
    return len(str(v)) <= p["max_length"], "长度不能大于 %s" % p["max_length"]


def _rule_allowed_values(v, p):
    return v in p["allowed_values"], "取值须在 %s" % p["allowed_values"]


def _rule_date_format(v, p):
    if v is None:
        return False, "字段缺失"
    fmts = p.get("format")
    if isinstance(fmts, str):
        fmts = [fmts]
    if not fmts:
        fmts = ["%Y-%m-%d %H:%M:%S"]
    for f in fmts:
        try:
            datetime.datetime.strptime(str(v), f)
            return True, ""
        except ValueError:
            continue
    return False, "日期格式不符（支持 %s）" % fmts


_RULES = {
    "not_empty": _rule_not_empty,
    "regex": _rule_regex,
    "min": _rule_min,
    "max": _rule_max,
    "range": _rule_range,
    "min_length": _rule_min_length,
    "max_length": _rule_max_length,
    "allowed_values": _rule_allowed_values,
    "date_format": _rule_date_format,
}


class DataQualityGate:
    """契约驱动的写入前数据校验门（轻量，零外部依赖）。"""

    def __init__(self, contracts_dir=None):
        self.dir = contracts_dir or DEFAULT_CONTRACTS_DIR
        self._contracts = {}
        self._load()

    def _load(self):
        if not os.path.isdir(self.dir):
            return
        for fn in sorted(os.listdir(self.dir)):
            if not fn.endswith(".yaml") and not fn.endswith(".yml"):
                continue
            try:
                with io.open(os.path.join(self.dir, fn), encoding="utf-8") as f:
                    import yaml
                    doc = yaml.safe_load(f) or {}
                c = doc.get("contract") or doc
                name = c.get("name") or os.path.splitext(fn)[0]
                self._contracts[name] = c
            except Exception:
                continue  # 单个契约损坏不影响整体

    def list_contracts(self):
        return sorted(self._contracts.keys())

    def validate(self, contract_name, record):
        """校验一条记录。缺失与格式错误分列，均不得算完整有效。"""
        c = self._contracts.get(contract_name)
        if c is None:
            return {"valid": False, "errors": [{"rule": "_contract", "message": "未知契约: %s" % contract_name}],
                    "missing": [], "warnings": [], "contract": contract_name, "version": None}
        errors, missing, warnings = [], [], []
        for rule in c.get("rules") or []:
            rname = rule.get("name", rule.get("type", "?"))
            rtype = rule.get("type")
            field = rule.get("field")
            check = _RULES.get(rtype)
            if check is None:
                continue  # 未知规则跳过（对齐 OpenDQV：lint 时警告）
            # condition：仅当条件字段等于某值时应用
            cond = rule.get("condition")
            if cond and record.get(cond.get("field")) != cond.get("equals"):
                continue
            v = record.get(field)
            if rule.get("missing_state") == "missing" and (v is None or str(v).strip() == ""):
                missing.append({"rule": rname, "field": field,
                                "message": "字段缺失", "severity": "missing"})
                continue
            ok, msg = check(v, rule)
            sev = rule.get("severity", "error")
            item = {"rule": rname, "field": field, "message": msg, "severity": sev}
            if ok:
                continue
            (errors if sev == "error" else warnings).append(item)
        return {"valid": not errors and not missing, "errors": errors,
                "missing": missing, "warnings": warnings,
                "contract": contract_name, "version": c.get("version")}

    def validate_batch(self, contract_name, records):
        """批量校验。unique 规则在此生效（批内去重）。"""
        c = self._contracts.get(contract_name) or {}
        unique_fields = [r["field"] for r in c.get("rules") or [] if r.get("type") == "unique"]
        seen = {}
        results = []
        for rec in records:
            res = self.validate(contract_name, rec)
            for uf in unique_fields:
                if uf in rec:
                    key = str(rec[uf])
                    if key in seen:
                        res["errors"].append({"rule": "unique", "field": uf,
                                              "message": "批内重复: %s" % key, "severity": "error"})
                        res["valid"] = False
                    else:
                        seen[key] = True
            results.append(res)
        return results

    def enrich_quality_record(self, contract_name, record):
        """生产接线：把质量校验结果转为 DB data_quality_* 标记字段（软门，不拒绝写入）。

        返回 dict（可直接并入写入记录，数据零丢失）：
          data_quality_status: ok / warning / missing / error
          data_quality_score:  100 / 90 / 80 / max(0, 100-10*nerror)
          data_quality_errors: 失败明细摘要（限 5 条）
        """
        res = self.validate(contract_name, record)
        nerr = len(res["errors"])
        nmissing = len(res["missing"])
        nwarn = len(res["warnings"])
        if nerr:
            status, score = "error", max(0, 100 - 10 * nerr)
        elif nmissing:
            status, score = "missing", 80
        elif nwarn == 0:
            status, score = "ok", 100
        else:
            status, score = "warning", 90
        issues = res["errors"] + res["missing"]
        brief = ["%s.%s:%s" % (e["rule"], e["field"], e["message"]) for e in issues[:5]]
        return {"data_quality_status": status, "data_quality_score": score,
                "data_quality_errors": "|".join(brief)}


# ============================================================
# ZBC Phase 10 桥接：接入统一 Evaluation 系统（data 维度）
# ============================================================
def batch_quality_to_evaluation(validation_results, db_path=None):
    """将 DataQualityGate 批量校验结果接入统一 Evaluation 系统。

    把 validate_batch() 的结果聚合为 data.completeness 指标，
    通过 lumenis.shared.evaluation.record_evaluation() 持久化。

    Args:
        validation_results: validate_batch() 返回的结果列表
        db_path: 数据库路径（默认项目 monitor.db）

    Returns:
        EvaluationRecord 列表
    """
    try:
        from lumenis.shared.evaluation import record_evaluation
    except Exception:
        return []

    total = len(validation_results)
    if total == 0:
        return [record_evaluation(
            dimension="data", metric_name="gate_completeness",
            metric_value=None, pass_threshold=0.90, warn_threshold=0.70,
            higher_is_better=True, source="data_quality_gate",
            evidence_ref="batch empty", metadata={"total": 0},
            db_path=db_path,
        )]

    valid_count = sum(1 for r in validation_results if r.get("valid", False))
    completeness = round(valid_count / total, 4)
    error_count = sum(len(r.get("errors", [])) for r in validation_results)
    missing_count = sum(len(r.get("missing", [])) for r in validation_results)
    warn_count = sum(len(r.get("warnings", [])) for r in validation_results)

    return [record_evaluation(
        dimension="data", metric_name="gate_completeness",
        metric_value=completeness, pass_threshold=0.90, warn_threshold=0.70,
        higher_is_better=True, source="data_quality_gate",
        evidence_ref=f"validate_batch | valid={valid_count}/{total}",
        metadata={"total": total, "valid": valid_count,
                  "errors": error_count, "missing": missing_count,
                  "warnings": warn_count},
        db_path=db_path,
    )]
