# -*- coding: utf-8 -*-
"""app.py 巨石拆分 · 闭包依赖审计器（P1-10 批2b~7 通用决策工具）。

对 app.py 每个 api_ 路由函数做静态闭包分析：
  引用名 ∈ (顶层 import ∪ 模块级 def/class/赋值 ∪ 函数内局部 ∪ 内置)  -> SAFE（可安全搬移到蓝图）
  否则 -> BLOCKED（依赖 app.py 私有全局/模块级可变状态，需人工梳理）

用法：
  python scripts/app_closure_audit.py                # 全量清单（SAFE/BLOCKED）
  python scripts/app_closure_audit.py <name>         # 单个函数判定

注意：静态判定是必要条件非充分条件——即使 SAFE 也要人工确认函数体不依赖
模块级可变状态（锁/任务表/闭包 helper，如 _collect_lock/_run_collect_task），
这类以 BLOCKED 处理。建议结合 E2E 冒烟验证。
"""
import ast
import builtins
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app.py")


def analyze():
    src = io.open(APP, encoding="utf-8", errors="replace").read()
    tree = ast.parse(src)
    builtin_names = set(dir(builtins))
    top_names = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for a in node.names:
                top_names.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                top_names.add(a.asname or a.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            top_names.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    top_names.add(t.id)
                elif isinstance(t, (ast.Tuple, ast.List)):
                    for e in t.elts:
                        if isinstance(e, ast.Name):
                            top_names.add(e.id)
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                top_names.add(node.target.id)

    routes = []
    for node in tree.body:
        if not (isinstance(node, ast.FunctionDef) and node.name.startswith("api_")):
            continue
        local = set()
        for n in ast.walk(node):
            if isinstance(n, ast.FunctionDef):
                local.add(n.name)
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                local.add(n.id)
            if isinstance(n, ast.ExceptHandler) and n.name:
                local.add(n.name)
        used = set()
        for n in ast.walk(node):
            if isinstance(n, ast.Name):
                used.add(n.id)
        deps = sorted(used - builtin_names - top_names - local)
        deps = [d for d in deps if d not in ("True", "False", "None")]
        routes.append((node.lineno, node.name, deps))
    return routes


def main():
    routes = analyze()
    if len(sys.argv) > 1:
        target = sys.argv[1]
        hit = [r for r in routes if target in r[1]]
        for ln, name, deps in hit:
            print("%d %s %s" % (ln, name, "SAFE" if not deps else "BLOCKED: " + ",".join(deps)))
        return
    closure = [r for r in routes if r[2]]
    safe = [r for r in routes if not r[2]]
    print("api_ 函数总数: %d | SAFE: %d | BLOCKED(闭包依赖): %d" % (len(routes), len(safe), len(closure)))
    print()
    print("=== SAFE 前 40 ===")
    for ln, name, _ in safe[:40]:
        print("%5d %s" % (ln, name))
    print()
    print("=== BLOCKED 前 20（依赖）===")
    for ln, name, deps in closure[:20]:
        print("%5d %-44s <- %s" % (ln, name, ",".join(deps[:6])))


if __name__ == "__main__":
    main()
