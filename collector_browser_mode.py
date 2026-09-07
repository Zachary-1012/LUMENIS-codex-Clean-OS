# -*- coding: utf-8 -*-
"""
Phase4: 采集浏览器模式配置（内部AI浏览器默认，可切外部）

默认 internal_cdp：采集走内部 AI 浏览器（CDP 真人通道 9222/9223）。
可选 external_standalone：走独立 Chromium 兜底通道（无持久登录态，易风控，仅测试用）。

持久化：data/private/collector_browser_mode.json
不写入 .env（避免与其他配置混淆），不修改 DB（遵守数据资产只读约束）。
"""
from __future__ import annotations
import json
import os
from typing import Dict

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(ROOT, "data", "private", "collector_browser_mode.json")

MODE_INTERNAL_CDP = "internal_cdp"
MODE_EXTERNAL_STANDALONE = "external_standalone"
VALID_MODES = (MODE_INTERNAL_CDP, MODE_EXTERNAL_STANDALONE)
DEFAULT_MODE = MODE_INTERNAL_CDP  # Phase4: 内部AI浏览器为默认


def _ensure_dir() -> None:
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)


def get_browser_mode() -> str:
    """读取当前采集浏览器模式。缺失/非法值均回退默认 internal_cdp。"""
    # 环境变量优先（运维可强制覆盖）
    env_mode = os.getenv("COLLECTOR_BROWSER_MODE", "").strip().lower()
    if env_mode in VALID_MODES:
        return env_mode
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            mode = str(cfg.get("mode", "")).strip().lower()
            if mode in VALID_MODES:
                return mode
    except Exception:
        pass
    return DEFAULT_MODE


def set_browser_mode(mode: str) -> Dict:
    """设置并持久化采集浏览器模式。返回 {ok, mode, source}。"""
    mode = (mode or "").strip().lower()
    if mode not in VALID_MODES:
        return {"ok": False, "error": f"非法模式: {mode}，允许: {list(VALID_MODES)}"}
    _ensure_dir()
    cfg = {"mode": mode, "updated_at": __import__("time").strftime("%Y-%m-%d %H:%M:%S")}
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        return {"ok": True, "mode": mode, "source": "file", "config_file": CONFIG_FILE}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_browser_mode_info() -> Dict:
    """获取浏览器模式完整信息（供 API/UI 消费）。"""
    mode = get_browser_mode()
    env_mode = os.getenv("COLLECTOR_BROWSER_MODE", "").strip().lower()
    source = "env" if env_mode in VALID_MODES else ("file" if os.path.exists(CONFIG_FILE) else "default")
    return {
        "ok": True,
        "mode": mode,
        "default": DEFAULT_MODE,
        "valid_modes": list(VALID_MODES),
        "source": source,
        "labels": {
            MODE_INTERNAL_CDP: "内部AI浏览器（CDP真人通道，默认）",
            MODE_EXTERNAL_STANDALONE: "外部独立浏览器（无持久登录态，易风控）",
        },
        "config_file": CONFIG_FILE,
    }


def is_internal_cdp() -> bool:
    """便捷判断：当前是否为内部CDP模式。"""
    return get_browser_mode() == MODE_INTERNAL_CDP
