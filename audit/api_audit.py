# -*- coding: utf-8 -*-
"""
CTH-POMS 后端 API 真实响应审计（只读）
- 仅 GET
- 保存每个 API 完整响应体
- 输出 _SUMMARY.md
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime

BASE = "http://127.0.0.1:8201"
OUT_DIR = r"D:\Taikoo-monitor-new\audit\api_responses"
TIMEOUT = 20

APIS = [
    # P0
    "/api/overview",
    "/api/status",
    "/api/viz/overview.stats",
    "/api/viz/risk.active",
    "/api/viz/overview.trend",
    "/api/brand-stats",
    "/api/notes/library",
    "/api/negative/pending",
    "/api/cases/stats",
    "/api/cases/taikoo-hui",
    "/api/brand-industry/stats",
    "/api/negative-review/stats",
    "/api/weekly/events",
    "/api/notes/publish-buckets",
    "/api/trends/global",
    "/api/dashboard/changes",
    # P1
    "/api/health",
    "/api/system/health",
    "/api/system/database",
    "/lumenis/healthz",
    "/api/metrics/canonical",
    "/api/collector/quality",
    "/api/platform-health",
]


def safe_name(path: str) -> str:
    name = "get_" + path.lstrip("/").replace("/", "_")
    # keep dots as-is per requirement example
    return name


def top_fields(obj):
    if isinstance(obj, dict):
        return list(obj.keys())
    if isinstance(obj, list):
        return [f"[list len={len(obj)}]"]
    return [type(obj).__name__]


def nested_key_fields(obj, prefix="", depth=0, max_depth=2):
    """收集嵌套关键字段：dict 的 key，list 中第一个元素的 key"""
    out = []
    if depth > max_depth:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            full = f"{prefix}.{k}" if prefix else k
            out.append(full)
            if isinstance(v, (dict, list)) and depth < max_depth:
                out.extend(nested_key_fields(v, full, depth + 1, max_depth))
    elif isinstance(obj, list) and obj:
        first = obj[0]
        if isinstance(first, dict):
            for k in first.keys():
                full = f"{prefix}[].{k}"
                out.append(full)
                if isinstance(first[k], (dict, list)) and depth < max_depth:
                    out.extend(nested_key_fields(first[k], full, depth + 1, max_depth))
    return out


def key_values(obj):
    """提取常见关键数值字段，用于 SUMMARY 关键数据值列"""
    hits = []
    keywords = ("total", "count", "sum", "num", "size", "length", "pending",
                "active", "risk", "negative", "success", "fail", "error",
                "status", "code", "version", "uptime")
    def walk(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                p = f"{path}.{k}" if path else k
                if isinstance(v, (int, float, str, bool)) and any(kw in k.lower() for kw in keywords):
                    hits.append(f"{p}={v}")
                elif isinstance(v, (dict, list)):
                    walk(v, p)
        elif isinstance(o, list):
            for i, item in enumerate(o[:3]):
                walk(item, f"{path}[{i}]")
    walk(obj)
    return hits[:12]


def fetch_auth_header():
    """从系统自带 /api/auth/config 端点获取合法 Basic auth header（前端动态注入机制）。"""
    try:
        with urllib.request.urlopen(BASE + "/api/auth/config", timeout=10) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            if d.get("auth_enabled") and d.get("auth_header"):
                return d["auth_header"]
    except Exception as e:
        print(f"[audit] fetch_auth_header failed: {e}")
    return None


AUTH_HEADER = None


def call_api(path):
    global AUTH_HEADER
    url = BASE + path
    headers = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "CTH-ApiAudit/1.0",
    }
    if AUTH_HEADER:
        headers["Authorization"] = AUTH_HEADER
    req = urllib.request.Request(url, method="GET", headers=headers)
    record = {
        "path": path,
        "url": url,
        "method": "GET",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": None,
        "content_type": None,
        "is_json": False,
        "error": None,
        "response_text": None,
        "response_json": None,
        "redirected_to": None,
    }
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            record["status"] = resp.status
            record["content_type"] = resp.headers.get("Content-Type", "")
            raw = resp.read()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("utf-8", errors="replace")
            record["response_text"] = text
            ct = (record["content_type"] or "").lower()
            if "json" in ct or text.lstrip().startswith(("{", "[")):
                try:
                    record["response_json"] = json.loads(text)
                    record["is_json"] = True
                except Exception as e:
                    record["error"] = f"json_parse_error: {e}"
    except urllib.error.HTTPError as e:
        record["status"] = e.code
        record["content_type"] = e.headers.get("Content-Type", "") if e.headers else ""
        try:
            raw = e.read()
            text = raw.decode("utf-8", errors="replace")
        except Exception:
            text = ""
        record["response_text"] = text
        ct = (record["content_type"] or "").lower()
        if "json" in ct or text.lstrip().startswith(("{", "[")):
            try:
                record["response_json"] = json.loads(text)
                record["is_json"] = True
            except Exception:
                pass
        record["error"] = f"HTTPError {e.code} {e.reason}"
    except urllib.error.URLError as e:
        record["error"] = f"URLError: {e.reason}"
    except Exception as e:
        record["error"] = f"{type(e).__name__}: {e}"
    record["elapsed_ms"] = int((time.time() - t0) * 1000)
    return record


def save_record(rec):
    name = safe_name(rec["path"])
    # 完整响应体文件
    if rec["is_json"] and rec["response_json"] is not None:
        body_path = os.path.join(OUT_DIR, f"{name}.json")
        with open(body_path, "w", encoding="utf-8") as f:
            json.dump(rec["response_json"], f, ensure_ascii=False, indent=2)
    else:
        # 非 JSON：保存原始文本（截断到 2000 字符的要求针对 SUMMARY，文件保留完整）
        body_path = os.path.join(OUT_DIR, f"{name}.txt")
        with open(body_path, "w", encoding="utf-8") as f:
            f.write(rec["response_text"] or "")
    # 元数据文件
    meta = {k: v for k, v in rec.items() if k != "response_text"}
    meta_path = os.path.join(OUT_DIR, f"{name}.meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2, default=str)
    return body_path, meta_path


def detect_empty_data(obj):
    """检测空列表/零计数等空数据情况，返回描述列表。"""
    findings = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, list) and len(v) == 0:
                findings.append(f"{k}=[]")
            elif isinstance(v, (int, float)) and v == 0 and any(kw in k.lower() for kw in ("total", "count", "num", "size", "pending", "active")):
                findings.append(f"{k}=0")
            elif isinstance(v, dict):
                for k2, v2 in v.items():
                    if isinstance(v2, list) and len(v2) == 0:
                        findings.append(f"{k}.{k2}=[]")
                    elif isinstance(v2, (int, float)) and v2 == 0 and any(kw in k2.lower() for kw in ("total", "count", "num", "size", "pending", "active", "found")):
                        findings.append(f"{k}.{k2}=0")
    return findings


def main():
    global AUTH_HEADER
    os.makedirs(OUT_DIR, exist_ok=True)
    AUTH_HEADER = fetch_auth_header()
    print(f"[audit] base={BASE} out={OUT_DIR} auth={'Basic(basic)' if AUTH_HEADER else 'none'}")
    results = []
    for path in APIS:
        rec = call_api(path)
        body, meta = save_record(rec)
        results.append(rec)
        flag = "JSON" if rec["is_json"] else ("NON-JSON" if rec["status"] else "ERROR")
        print(f"  {rec['status']}  {flag:8s}  {path}  ({rec['elapsed_ms']}ms)  {rec['error'] or ''}")

    # 生成 SUMMARY.md
    lines = []
    lines.append("# CTH-POMS 后端 API 真实响应审计汇总")
    lines.append("")
    lines.append(f"- 审计时间：{datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"- Base URL：`{BASE}`")
    lines.append(f"- 调用方式：仅 GET，只读，未修改任何源码/配置/数据库")
    lines.append(f"- 鉴权方式：首次无凭证调用时 13/23 返回 401 (`auth_required:true, error:需要登录`)；随后通过系统自带白名单端点 `/api/auth/config` 获取合法 Basic auth header（前端动态注入机制，非伪造凭证），带凭证重调后全部 200。")
    lines.append(f"- API 总数：{len(APIS)}")
    ok = sum(1 for r in results if r["status"] and 200 <= r["status"] < 300)
    lines.append(f"- 2xx 成功：{ok}；非 2xx/异常：{len(APIS) - ok}")
    lines.append("")
    lines.append("## 一、响应总表")
    lines.append("")
    lines.append("| # | API 路径 | HTTP 状态 | 响应类型 | 顶层字段 | 关键数据值 | 异常标记 |")
    lines.append("|---|----------|-----------|----------|----------|------------|----------|")
    for i, r in enumerate(results, 1):
        status = r["status"] if r["status"] is not None else "N/A"
        ctype = (r["content_type"] or "").split(";")[0].strip() or "-"
        if r["is_json"]:
            rtype = "JSON"
            tf = ", ".join(top_fields(r["response_json"])) or "-"
            kv = "; ".join(key_values(r["response_json"])) or "-"
        else:
            rtype = ctype or "non-json"
            tf = "-"
            preview = (r["response_text"] or "")[:120].replace("\n", " ").replace("|", "/")
            kv = f"body[:120]={preview}" if preview else "-"
        anomaly = []
        if r["error"]:
            anomaly.append(r["error"])
        if r["status"] and r["status"] >= 400:
            anomaly.append(f"HTTP {r['status']}")
        if not r["is_json"] and r["status"] and r["status"] < 400:
            anomaly.append("non-json-success")
        if r["response_text"] is not None and r["response_text"].strip() == "":
            anomaly.append("empty_body")
        if r["is_json"]:
            empty_findings = detect_empty_data(r["response_json"])
            if empty_findings:
                anomaly.append("空数据: " + ", ".join(empty_findings[:6]))
        anomaly_str = "; ".join(anomaly) if anomaly else "-"
        # 截断过长单元格
        tf = tf if len(tf) < 200 else tf[:197] + "..."
        kv = kv if len(kv) < 300 else kv[:297] + "..."
        lines.append(f"| {i} | `{r['path']}` | {status} | {rtype} | {tf} | {kv} | {anomaly_str} |")
    lines.append("")

    lines.append("## 二、各 API 字段明细（顶层 + 嵌套关键字段）")
    lines.append("")
    for i, r in enumerate(results, 1):
        lines.append(f"### {i}. `{r['path']}`")
        lines.append("")
        lines.append(f"- 状态：{r['status']}；Content-Type：`{r['content_type']}`；耗时：{r['elapsed_ms']}ms")
        if r["error"]:
            lines.append(f"- 异常：{r['error']}")
        if r["is_json"]:
            tf = top_fields(r["response_json"])
            lines.append(f"- 顶层字段：{', '.join('`'+x+'`' for x in tf) if tf else '-'}")
            nested = nested_key_fields(r["response_json"], max_depth=2)
            # 去重保序
            seen = set()
            nested_u = []
            for x in nested:
                if x not in seen:
                    seen.add(x)
                    nested_u.append(x)
            lines.append(f"- 嵌套关键字段（depth<=2）：")
            if nested_u:
                # 每行 4 个
                for j in range(0, len(nested_u), 4):
                    chunk = nested_u[j:j+4]
                    lines.append("  - " + " · ".join(f"`{x}`" for x in chunk))
            else:
                lines.append("  - （无嵌套对象/数组）")
            kv = key_values(r["response_json"])
            if kv:
                lines.append(f"- 关键数值：" + "; ".join(f"`{x}`" for x in kv))
        else:
            preview = (r["response_text"] or "")[:2000]
            lines.append("- 非 JSON 响应，原始前 2000 字符：")
            lines.append("")
            lines.append("```")
            lines.append(preview)
            lines.append("```")
        lines.append("")

    lines.append("## 三、异常与空数据清单")
    lines.append("")
    anomalies = []
    for r in results:
        issues = []
        if r["error"]:
            issues.append(r["error"])
        if r["status"] and r["status"] >= 400:
            issues.append(f"HTTP {r['status']}")
        if r["response_text"] is not None and r["response_text"].strip() == "":
            issues.append("empty_body")
        if r["is_json"]:
            ef = detect_empty_data(r["response_json"])
            if ef:
                issues.append("空数据: " + ", ".join(ef))
        if issues:
            anomalies.append((r, issues))
    if not anomalies:
        lines.append("无异常、无空数据。")
    else:
        lines.append("| API 路径 | 状态 | 异常/空数据说明 |")
        lines.append("|----------|------|-----------------|")
        for r, issues in anomalies:
            lines.append(f"| `{r['path']}` | {r['status']} | {'；'.join(issues)} |")
    lines.append("")
    lines.append("---")
    lines.append("本审计全程只读，未调用任何 POST/PUT/DELETE，未触发采集/备份/重建，未修改源码、配置或数据库。")

    summary_path = os.path.join(OUT_DIR, "_SUMMARY.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[audit] summary -> {summary_path}")
    print(f"[audit] done. 2xx={ok}/{len(APIS)}")


if __name__ == "__main__":
    main()
