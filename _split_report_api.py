# -*- coding: utf-8 -*-
"""app.py 批3拆分：提取 report/digest/brand-report 路由到 report_api.py 蓝图。
精确提取函数体（基于缩进边界），生成蓝图文件，并从 app.py 中移除。
备份已存：app.py.bak-report-split-*"""
import io, re, os
from core.repository_registry import get_repo_root, get_db_path, get_osai_root

base = get_repo_root()
app_path = os.path.join(base, "app.py")
out_path = os.path.join(base, "report_api.py")

src = io.open(app_path, encoding="utf-8").read()
lines = src.split("\n")

# 要提取的函数名（def 后的函数名）
TARGET_FUNCS = {
    "report_center_preview",
    "brand_report_generate",
    "brand_report_export",
    "api_report_daily",
    "api_reports_list",
    "api_report_download",
    "api_report_file",
    "api_report",
    "api_generate_report",
    "api_report_v2",
    "api_report_v2_stats",
    "api_report_verify_v571",
    "api_digest_today",
    "api_digest_generate",
    "api_report_export",
    "api_special_report_export",
    # 内部 helper（无路由装饰器，但被 report 路由调用）
    "_canonical_report_metrics",
}

#  also extract api_reports_export_v532 / api_reports_export_all_v532 if they are report-related
# (they may not have @app.route decorators — check)

def find_func_blocks(lines, target_funcs):
    """找到每个目标函数的起始行（含装饰器）和结束行（不含）。
    起始：@app.route 或 def 行（取最上层装饰器开始）。
    结束：下一个顶层（缩进0）def 或 @app.route，或文件末尾。"""
    blocks = {}  # func_name -> (start_line, end_line) 0-indexed
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        # 匹配顶层 def
        m = re.match(r'^def\s+(\w+)\s*\(', line)
        if m:
            fname = m.group(1)
            if fname in target_funcs:
                # 向前找装饰器（@app.route 等，缩进0）
                start = i
                j = i - 1
                while j >= 0 and lines[j].startswith("@"):
                    start = j
                    j -= 1
                # 向后找结束：下一个缩进0的 def 或 @ 装饰器
                end = i + 1
                while end < n:
                    el = lines[end]
                    if el and not el.startswith(" ") and not el.startswith("\t") and (el.startswith("def ") or el.startswith("@") or el.startswith("# ======") or el.startswith("# ---")):
                        # 跳过空行后的注释分隔
                        if el.startswith("#"):
                            # 检查是否是分隔线（# ==== 或 # ----）
                            if re.match(r'^#\s*[=-]{3,}', el):
                                break
                            end += 1
                            continue
                        break
                    end += 1
                blocks[fname] = (start, end)
                i = end
                continue
        i += 1
    return blocks

blocks = find_func_blocks(lines, TARGET_FUNCS)
print(f"找到 {len(blocks)} 个函数块：")
for fname, (s, e) in sorted(blocks.items(), key=lambda x: x[1][0]):
    print(f"  {fname}: L{s+1}-L{e} ({e-s} 行)")

# 检查是否有遗漏
missing = TARGET_FUNCS - set(blocks.keys())
if missing:
    print(f"[WARN] 未找到: {missing}")

# 按行号排序提取
sorted_blocks = sorted(blocks.items(), key=lambda x: x[1][0])

# 生成 report_api.py 蓝图内容
blueprint_header = '''# -*- coding: utf-8 -*-
"""report_api.py — 报告/摘要/品牌报告 API 蓝图（批3拆分自 app.py）。
原则：只搬不移逻辑，函数体零改动；依赖 app.py 内 helper 时用函数内延迟导入。
注册点：app.register_blueprint(report_api.report_bp)"""
from flask import Blueprint, request, jsonify
import os, json, time, traceback
from datetime import datetime, timedelta

import database as db
import report_engine
import canonical_metrics
import daily_report

report_bp = Blueprint('report', __name__)

# ===== 报告 API（从 app.py 拆分，函数体零改动）=====

'''

# 提取函数体并转换装饰器
extracted_code = []
for fname, (s, e) in sorted_blocks:
    block_lines = lines[s:e]
    # 转换 @app.route -> @report_bp.route
    converted = []
    for bl in block_lines:
        converted.append(bl.replace("@app.route", "@report_bp.route"))
    extracted_code.append("\n".join(converted))

blueprint_content = blueprint_header + "\n\n".join(extracted_code) + "\n"
io.open(out_path, "w", encoding="utf-8", newline="\n").write(blueprint_content)
print(f"\n已生成 {out_path}（{len(blueprint_content)} 字节）")

# 从 app.py 中移除这些函数块（从后往前删，避免行号偏移）
remove_ranges = sorted([(s, e) for _, (s, e) in sorted_blocks], reverse=True)
new_lines = lines[:]
for s, e in remove_ranges:
    del new_lines[s:e]

# 移除后清理多余空行（连续3+空行压缩为2）
cleaned = []
empty_count = 0
for l in new_lines:
    if l.strip() == "":
        empty_count += 1
        if empty_count <= 2:
            cleaned.append(l)
    else:
        empty_count = 0
        cleaned.append(l)

io.open(app_path, "w", encoding="utf-8", newline="\n").write("\n".join(cleaned))
print(f"已从 app.py 移除 {len(remove_ranges)} 个函数块，剩余 {len(cleaned)} 行")
