# -*- coding: utf-8 -*-
"""批4 ai_api 拆分 v2：正确提取函数体（装饰器+def+缩进函数体）。"""
import io

APP = r"D:\Taikoo-monitor-new\app.py"
AIOUT = r"D:\Taikoo-monitor-new\ai_api.py"

s = io.open(APP, encoding="utf-8").read()
lines = s.split("\n")

AI_ROUTE_MARKERS = [
    "/api/ai/status", "/api/ai/test", "/api/ark/status", "/api/ark/chat",
    "/api/ark/sentiment", "/api/ark/summary", "/api/ark/keywords",
    "/api/ai-learning/status", "/api/ai-learning/optimization",
    "/api/web-sentiment/search", "/api/web-sentiment/history",
    "/api/ai/chat", "/api/ai/providers", "/api/ai/analyze-v570",
    "/api/ai-filter/stats", "/api/ai-filter/run", "/api/ai-filter/cleanup",
    "/api/ai/channel-health", "/api/ai/analyze",
]

def is_top_level(line):
    """判断是否是顶层行（无缩进的非空行）。"""
    return line.strip() != "" and not line.startswith(" ") and not line.startswith("\t")

def find_route_blocks(lines, markers):
    blocks = []
    i = 0
    while i < len(lines):
        line = lines[i]
        matched = None
        for marker in markers:
            if f"@app.route('{marker}'" in line or f'@app.route("{marker}"' in line:
                matched = marker
                break
        if matched:
            start = i
            # 结束：下一个顶层 @app.route 或顶层 def（跳过当前函数的 def）
            end = len(lines)
            seen_def = False
            for j in range(i+1, len(lines)):
                if is_top_level(lines[j]):
                    if lines[j].startswith("def "):
                        if not seen_def:
                            seen_def = True  # 当前函数的 def，跳过
                            continue
                        else:
                            end = j  # 下一个顶层 def，结束
                            break
                    elif lines[j].startswith("@app.route"):
                        end = j  # 下一个装饰器，结束
                        break
                    elif lines[j].startswith("#") or lines[j].startswith('"""'):
                        # 注释或文档字符串，继续（可能是分隔注释）
                        continue
                    else:
                        # 其他顶层行（如 import、变量赋值），结束
                        end = j
                        break
            blocks.append((matched, start, end))
            i = end
        else:
            i += 1
    return blocks

blocks = find_route_blocks(lines, AI_ROUTE_MARKERS)
print(f"找到 {len(blocks)} 个 AI 路由块")
for marker, start, end in blocks:
    print(f"  {marker}: L{start+1}-L{end} ({end-start} 行)")

# 提取函数代码
functions_code = []
for marker, start, end in blocks:
    func_lines = lines[start:end]
    while func_lines and func_lines[-1].strip() == "":
        func_lines.pop()
    functions_code.append((marker, "\n".join(func_lines)))

# 生成 ai_api.py
header = '''# -*- coding: utf-8 -*-
"""AI API Blueprint（批4拆分自 app.py）
包含：ai/status, ai/test, ark/*, ai-learning/*, web-sentiment/*, ai/chat, ai/providers,
ai/analyze-v570, ai-filter/*, ai/channel-health, ai/analyze
原则：只搬不移逻辑，函数体零改动，路由与行为保持一致。
"""
from __future__ import annotations
import json
import threading
from flask import Blueprint, jsonify, request

bp = Blueprint("ai_api", __name__)

# 依赖模块（与 app.py 保持一致）
import intelligence
import ai_governance
import ai_analyzer
import ai_learning_engine
import ai_filter
import ai_channel
import function_registry
from report_api import _canonical_report_metrics


'''

body = ""
for marker, code in functions_code:
    code = code.replace("@app.route(", "@bp.route(")
    body += code + "\n\n"

footer = '''
def register_ai_api(app):
    """注册 AI API 蓝图。"""
    app.register_blueprint(bp)
    return bp
'''

io.open(AIOUT, "w", encoding="utf-8", newline="\n").write(header + body + footer)
print(f"\nai_api.py 已生成")

# 从 app.py 删除这些块（从后往前）
delete_ranges = sorted([(start, end) for _, start, end in blocks], reverse=True)
new_lines = lines[:]
for start, end in delete_ranges:
    del new_lines[start:end]

new_s = "\n".join(new_lines)

# 添加 import
if "import ai_api" not in new_s:
    if "import collection_api" in new_s:
        new_s = new_s.replace("import collection_api", "import collection_api\nimport ai_api", 1)
    elif "import data_query_api" in new_s:
        new_s = new_s.replace("import data_query_api", "import data_query_api\nimport ai_api", 1)

# 添加注册
if "ai_api.register_ai_api(app)" not in new_s:
    if "collection_api.register_collection_api(app)" in new_s:
        new_s = new_s.replace(
            "collection_api.register_collection_api(app)",
            "collection_api.register_collection_api(app)\nai_api.register_ai_api(app)",
            1
        )
    elif "data_query_api.register_data_query_api(app)" in new_s:
        new_s = new_s.replace(
            "data_query_api.register_data_query_api(app)",
            "data_query_api.register_data_query_api(app)\nai_api.register_ai_api(app)",
            1
        )

io.open(APP, "w", encoding="utf-8", newline="\n").write(new_s)
print(f"app.py 已更新：删除 {len(blocks)} 个 AI 路由，添加 import+注册")
print(f"app.py 原行数: {len(lines)}, 新行数: {len(new_lines)}")
