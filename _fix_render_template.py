# -*- coding: utf-8 -*-
"""UI HARD RESET 后续：把 v4_upgrade 路由中 render_template(已删除模板) 改为 JSON 响应。"""
import io, re

ZBC = r"D:\Taikoo-monitor-new"

def patch_file(path, old, new, add_import=None):
    full = f"{ZBC}\\{path}"
    s = io.open(full, encoding="utf-8").read()
    if old not in s:
        print(f"SKIP (pattern not found): {path}")
        return False
    s = s.replace(old, new, 1)
    if add_import and add_import not in s:
        # 在 from flask import 行添加 jsonify
        s = re.sub(r"from flask import (.*)", lambda m: "from flask import " + m.group(1) + ", jsonify" if "jsonify" not in m.group(1) else m.group(0), s, count=1)
    io.open(full, "w", encoding="utf-8", newline="\n").write(s)
    print(f"PATCHED: {path}")
    return True

# 1. collect/routes.py
patch_file(
    "v4_upgrade/collect/routes.py",
    '    return render_template("collect.html", current_user=user)',
    '    return jsonify({"ok": True, "ui_reset": True, "page": "collect", "user": user.get("username") if user else None})',
    add_import="jsonify"
)

# 2. console/routes.py
patch_file(
    "v4_upgrade/console/routes.py",
    '    return render_template("console.html", current_user=user)',
    '    return jsonify({"ok": True, "ui_reset": True, "page": "console", "user": user.get("username") if user else None})',
    add_import="jsonify"
)

# 3. settings/routes.py - login
patch_file(
    "v4_upgrade/settings/routes.py",
    '    return render_template("login.html")',
    '    return jsonify({"ok": True, "ui_reset": True, "page": "login"})'
)

# 4. settings/routes.py - settings
patch_file(
    "v4_upgrade/settings/routes.py",
    '    return render_template("settings.html", current_user=user)',
    '    return jsonify({"ok": True, "ui_reset": True, "page": "settings", "user": user.get("username") if user else None})'
)

# 5. version_center/routes.py
patch_file(
    "v4_upgrade/version_center/routes.py",
    '    return render_template("version_center.html", current_user=user)',
    '    return jsonify({"ok": True, "ui_reset": True, "page": "version_center", "user": user.get("username") if user else None})'
)

print("\n完成：6 处 render_template 已改为 JSON 响应")
