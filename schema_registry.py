# -*- coding: utf-8 -*-
"""单一权威 DB Schema 源（对账 P1-5）——只读反射 + 代码声明来源映射，绝不建表/改库。

设计原则（红线）：
- 本模块以 mode=ro 只读打开 SQLite 反射表/列/索引/行数，不执行任何 DDL/DML，不修改生产库；
- 不重写 database.py 的建表逻辑，只把「实际库结构 ↔ 全仓 CREATE 声明位置」收敛成一份可追溯清单；
- 无 CREATE 声明的实际表标 LEGACY（保留不删，待人工确认）；migration 隔离表标 MIGRATION_ISOLATED。
生成 docs/DATABASE-SCHEMA-REGISTRY.md；tests/test_schema_registry.py 锁定，防止再出现无主表。
"""
from __future__ import annotations

import os
import re
import sqlite3
from typing import Dict, List, Optional, Set, Tuple

CRE_RE = re.compile(
    r"CREATE\s+TABLE(?:\s+IF\s+NOT\s+EXISTS)?\s+[`\"\[]*([a-zA-Z_][a-zA-Z0-9_]*)",
    re.I,
)
_SKIP_DIRS = (".venv", "__pycache__", "backups", ".trae", "tests", ".git", "staging", "docs")
# 备份/旧版本文件不作为权威声明来源
_SKIP_FILE_MARK = ("_backup", "_v5", "app_backup", "legacy")

# 已知「无 CREATE 声明」的实际表及其定性（只允许登记，不允许悄悄新增无主表）
LEGACY_NO_DECLARATION = {
    "industry_stats": "LEGACY 历史遗留预聚合表（8 行旧数据）；现役 /api/brand-industry/* 实际查 "
                      "brand_industry_monitor；旧版本化网页监测模块已收敛为 web_discovery.py；该表保留待数据治理确认",
}
# migration 隔离、生产库当前不建的预留表前缀/集合（设计如此，不算无主）
MIGRATION_ISOLATED_PREFIX = ("bi_",)


def reflect(db_path: str) -> Dict[str, dict]:
    """只读反射数据库结构。返回 {table: {columns, indexes, row_count}}。以 ro 打开，绝不写入。"""
    uri = "file:" + db_path.replace("\\", "/") + "?mode=ro"
    con = sqlite3.connect(uri, uri=True)
    try:
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        out: Dict[str, dict] = {}
        for t in tables:
            cols = [
                {"cid": r[0], "name": r[1], "type": r[2], "notnull": r[3],
                 "default": r[4], "pk": r[5]}
                for r in con.execute(f"PRAGMA table_info([{t}])")
            ]
            idxs = [r[1] for r in con.execute(f"PRAGMA index_list([{t}])")]
            try:
                cnt = con.execute(f"SELECT COUNT(*) FROM [{t}]").fetchone()[0]
            except sqlite3.Error:
                cnt = -1
            out[t] = {"columns": cols, "indexes": idxs, "row_count": cnt}
        return out
    finally:
        con.close()


def declared_sources(root: str) -> Dict[str, List[str]]:
    """扫描全仓 .py/.sql 中 CREATE TABLE 的声明位置，返回 {table_lower: [相对路径...]}。"""
    src: Dict[str, List[str]] = {}
    for dp, dn, fns in os.walk(root):
        dn[:] = [d for d in dn if d not in _SKIP_DIRS]
        for f in fns:
            if not f.endswith((".py", ".sql")):
                continue
            low = f.lower()
            if any(m in low for m in _SKIP_FILE_MARK):
                continue
            fp = os.path.join(dp, f)
            try:
                txt = open(fp, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            rel = os.path.relpath(fp, root)
            for m in CRE_RE.findall(txt):
                if m.lower() == "if":
                    continue
                src.setdefault(m.lower(), []).append(rel.replace("\\", "/"))
    return src


def classify(table: str, sources: Dict[str, List[str]]) -> Tuple[str, str]:
    """返回 (状态, 说明)。DECLARED 正常 / LEGACY_NO_DECL / MIGRATION_ISOLATED / MISSING_SOURCE。"""
    tl = table.lower()
    if tl in sources:
        return "DECLARED", ""
    if tl in LEGACY_NO_DECLARATION:
        return "LEGACY_NO_DECL", LEGACY_NO_DECLARATION[tl]
    if any(tl.startswith(p) for p in MIGRATION_ISOLATED_PREFIX):
        return "MIGRATION_ISOLATED", "migration 隔离表（生产库当前不建，设计如此）"
    return "MISSING_SOURCE", "!! 实际存在但全仓无 CREATE 声明且未登记，需要补声明或登记遗留"


def build_markdown(reflect_data: Dict[str, dict], sources: Dict[str, List[str]],
                   db_label: str = "data/monitor.db (mode=ro)") -> str:
    lines: List[str] = []
    lines.append("# 数据库 Schema 权威清单（DATABASE-SCHEMA-REGISTRY，P1-5 单一权威源）\n")
    lines.append("> 由 schema_registry.py 只读反射实际库 + 全仓 CREATE 声明来源生成；请勿手改，"
                 "用生成器重跑。本文件不改变任何建表逻辑与生产数据。\n")
    total = len(reflect_data)
    declared = sum(1 for t in reflect_data if classify(t, sources)[0] == "DECLARED")
    legacy = sum(1 for t in reflect_data if classify(t, sources)[0] == "LEGACY_NO_DECL")
    missing = [t for t in reflect_data if classify(t, sources)[0] == "MISSING_SOURCE"]
    lines.append(f"- 反射对象：{db_label}")
    lines.append(f"- 实际表数：**{total}**；有 CREATE 声明：{declared}；"
                 f"登记遗留：{legacy}；无主未登记：**{len(missing)}** {missing if missing else ''}")
    lines.append("- 状态含义：DECLARED=全仓可定位建表声明；LEGACY_NO_DECL=历史遗留保留不删；"
                 "MIGRATION_ISOLATED=迁移隔离预留；MISSING_SOURCE=必须处理的无主表。\n")
    lines.append("| # | 表名 | 状态 | 列数 | 行数 | 索引数 | CREATE 声明来源（节选） | 备注 |")
    lines.append("|---|------|------|------|------|--------|--------------------------|------|")
    for i, (t, meta) in enumerate(sorted(reflect_data.items()), 1):
        status, note = classify(t, sources)
        srcs = ", ".join(sorted(set(sources.get(t.lower(), [])))[:3])
        colnames = ", ".join(c["name"] for c in meta["columns"])
        lines.append(
            f"| {i} | `{t}` | {status} | {len(meta['columns'])} | {meta['row_count']} | "
            f"{len(meta['indexes'])} | {srcs or '—'} | {note or colnames[:60]} |"
        )
    # 红线列校验提示段
    lines.append("\n## 红线时间列核对（publish_datetime ≠ captured_at）")
    for t in ("notes",):
        if t in reflect_data:
            names = {c["name"] for c in reflect_data[t]["columns"]}
            for must in ("publish_datetime", "captured_at"):
                lines.append(f"- `{t}.{must}`: {'存在' if must in names else '!!缺失'}")
    return "\n".join(lines) + "\n"


def generate(root: Optional[str] = None, db_path: Optional[str] = None,
             out_path: Optional[str] = None) -> str:
    root = root or os.getcwd()
    db_path = db_path or os.path.join(root, "data", "monitor.db")
    refl = reflect(db_path)
    srcs = declared_sources(root)
    md = build_markdown(refl, srcs)
    if out_path:
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            f.write(md)
    return md
