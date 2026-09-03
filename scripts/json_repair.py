# -*- coding: utf-8 -*-
"""轻量 LLM 结构化输出修复（能力提取自 outputguard：15 修复策略核心子集，零重依赖）。

outputguard（ndcorder/outputguard, MIT）针对 LLM 损坏 JSON 提供 15 种有序修复策略 +
JSON Schema 校验 + 重试提示；288 模型实测 100% 可用（78% 直接有效 + 22% 自动修复）。
本模块提取最高频策略（纯标准库 json/re 实现），服务 ZBC 的 LLM 输出解析（智谱等）：

  策略（按序）：strip_fences -> extract_json -> fix_booleans -> fix_keys ->
               fix_quotes -> fix_commas -> fix_truncated -> fix_closers

用法：
  from scripts.json_repair import repair_json
  data, strategies = repair_json(llm_text)   # 成功返回 (解析结果, 策略列表)；失败 (None, [])
"""
import json
import re


def _try_loads(text):
    try:
        return json.loads(text), True
    except (json.JSONDecodeError, ValueError, TypeError):
        return None, False


def _strip_fences(text):
    """去 markdown code fence（```json ... ```）。"""
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    return m.group(1).strip() if m else text


def _extract_json(text):
    """抽取首个 { 到末个 } 之间的内容（剥离前后解说文字）。"""
    i = text.find("{")
    j = text.rfind("}")
    if i >= 0 and j > i:
        return text[i:j + 1]
    i = text.find("[")
    j = text.rfind("]")
    if i >= 0 and j > i:
        return text[i:j + 1]
    return text


def _fix_booleans(text):
    """True/False/None -> true/false/null（Python 字面量）。"""
    text = re.sub(r"\bTrue\b", "true", text)
    text = re.sub(r"\bFalse\b", "false", text)
    text = re.sub(r"\bNone\b", "null", text)
    return text


def _fix_keys(text):
    """裸键 -> 引号键：{a: 1} -> {"a": 1}。"""
    return re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)(\s*:)", r'\1"\2"\3', text)


def _fix_quotes(text):
    """单引号 -> 双引号（仅键与值外围；内嵌撇号保守处理）。"""
    # 键：'key' -> "key"
    text = re.sub(r"'([A-Za-z_][A-Za-z0-9_]*?)'\s*:", r'"\1":', text)
    # 值：'value' -> "value"
    text = re.sub(r":\s*'([^']*?)'(\s*[,}])", r': "\1"\2', text)
    return text


def _fix_commas(text):
    """去尾随逗号（数组/对象结尾的 ,）。"""
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return text


def _fix_truncated(text):
    """修复截断字符串：未闭合的引号补全。"""
    # 找到未闭合的字符串（值里引号无配对，后跟 EOF 或逗号/括号）
    return re.sub(r'"([^"\\]*(?:\\.[^"\\]*)*)$', lambda m: '"%s"' % m.group(1), text)


def _fix_closers(text):
    """补齐未闭合的括号/方括号。"""
    stack = []
    for ch in text:
        if ch in "{[":
            stack.append(ch)
        elif ch in "}]" and stack:
            if (ch == "}" and stack[-1] == "{") or (ch == "]" and stack[-1] == "["):
                stack.pop()
    close_map = {"{": "}", "[": "]"}
    for ch in reversed(stack):
        text += close_map.get(ch, "")
    return text


STRATEGIES = [
    ("strip_fences", _strip_fences),
    ("extract_json", _extract_json),
    ("fix_booleans", _fix_booleans),
    ("fix_keys", _fix_keys),
    ("fix_quotes", _fix_quotes),
    ("fix_commas", _fix_commas),
    ("fix_truncated", _fix_truncated),
    ("fix_closers", _fix_closers),
]


def repair_json(text):
    """按策略序修复 LLM JSON 输出，返回 (data, strategies_applied)。

    data 为解析后的 Python 对象；全部策略后仍失败返回 (None, [])。
    修复仅做格式层校正（去 fence/引号/逗号/截断），不改变业务内容。
    """
    if not text or not isinstance(text, str):
        return None, []
    cur = text.strip()
    data, ok = _try_loads(cur)
    if ok:
        return data, []
    applied = []
    for name, fn in STRATEGIES:
        nxt = fn(cur)
        if nxt == cur:
            continue
        cur = nxt
        applied.append(name)
        data, ok = _try_loads(cur)
        if ok:
            return data, applied
    return None, []


def safe_parse_json(text):
    """repair_json 的便捷封装：成功返回 data；失败返回 None（调用方降级）。"""
    data, _ = repair_json(text)
    return data
