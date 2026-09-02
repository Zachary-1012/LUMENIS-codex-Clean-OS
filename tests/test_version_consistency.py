# -*- coding: utf-8 -*-
"""P1-1 版本单一权威一致性测试：VERSION 文件 = package.json = app.APP_VERSION，无残留旧版本号。"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel, encoding="utf-8"):
    return open(os.path.join(ROOT, rel), encoding=encoding).read()


def test_single_version_authority_aligned():
    version_file = _read("VERSION", encoding="utf-8-sig").strip()
    pkg = json.loads(_read("package.json"))["version"].strip()
    m = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", _read("app.py"))
    assert m, "app.py 未找到 APP_VERSION"
    app_ver = m.group(1)
    assert version_file == pkg == app_ver == "5.9.9", (version_file, pkg, app_ver)


def test_models_py_has_no_stale_version():
    src = _read("models.py")
    assert "v5.8.0" not in src and "v5.8.9" not in src
    assert "v5.9.9" in src
