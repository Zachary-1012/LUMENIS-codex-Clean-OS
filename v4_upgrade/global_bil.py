# -*- coding: utf-8 -*-
"""Global BIL（全球品牌智能体系）只读研究数据加载器（阶段4c，research-stage）。

边界：
- 只从 data/global_bil_*_v1.json 三个 seed 读取研究数据，带 mtime 缓存；
- **不建表、不写库、不联网**；migrations/009_*_staging.sql 仅允许在 ZBC_DB_PATH 指向的隔离库执行；
- 不参与任何生产统计/主体/风控口径，纯研究/基准/案例参考。
"""
from __future__ import annotations

import json
import os
import threading

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DATA_DIR = os.path.join(_ROOT, "data")

# 资源白名单 -> seed 文件名 / 其中列表字段
_FILES = {
    "benchmarks": ("global_bil_benchmark_seed_v1.json", "benchmarks"),
    "mechanisms": ("global_bil_benchmark_mechanisms_v1.json", "mechanisms"),
    "cases": ("global_bil_case_seed_v1.json", "cases"),
}

_lock = threading.Lock()
_cache: dict = {}


def load_resource(name: str):
    """按白名单读取一个 seed（dict）；未就绪返回 None；非法名抛 KeyError。"""
    if name not in _FILES:
        raise KeyError(name)
    fname, _ = _FILES[name]
    path = os.path.join(_DATA_DIR, fname)
    if not os.path.exists(path):
        return None
    mtime = os.path.getmtime(path)
    with _lock:
        if _cache.get(name, {}).get("mtime") != mtime:
            with open(path, "r", encoding="utf-8") as f:
                _cache[name] = {"mtime": mtime, "data": json.load(f)}
        return _cache[name]["data"]


def overview() -> dict:
    """三个 seed 的版本/状态/条数概览（不返回全量，供首页卡片用）。"""
    out = {}
    for name, (_, list_key) in _FILES.items():
        d = load_resource(name)
        if d is None:
            out[name] = {"available": False}
            continue
        lst = d.get(list_key)
        out[name] = {
            "available": True,
            "version": d.get("version", ""),
            "status": d.get("status", ""),
            "count": len(lst) if isinstance(lst, list) else None,
        }
    return out
