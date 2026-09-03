# -*- coding: utf-8 -*-
"""Prompt Registry（智谱 Prompt-Cache 优化层·固定前缀收敛）。

从 config/prompts/zbc-prompts.yaml 加载版本化固定 system 前缀。
AI 调用方必须用本模块加载（禁止内联复制），保证前缀逐字符稳定，
最大化智谱隐式上下文缓存命中（缓存命中 token 按优惠价计费）。

用法：
  from scripts.prompt_registry import load_system_prompt, list_roles
  sys_prompt = load_system_prompt("analyst")   # 固定前缀文本
"""
import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "config", "prompts", "zbc-prompts.yaml")

_cache = None


def _load():
    global _cache
    if _cache is None:
        with open(PATH, encoding="utf-8") as f:
            _cache = yaml.safe_load(f) or {}
    return _cache


def list_roles():
    """返回所有可用角色名 + 版本号。"""
    return [(name, p.get("version")) for name, p in (_load().get("prompts") or {}).items()]


def load_system_prompt(role):
    """按角色加载固定 system 前缀；角色不存在抛 KeyError（防拼写漂移破坏缓存命中）。"""
    prompts = (_load().get("prompts") or {})
    p = prompts.get(role)
    if not p:
        raise KeyError("未知 prompt 角色: %s（可用: %s）" % (role, list(prompts)))
    return (p.get("text") or "").strip()
