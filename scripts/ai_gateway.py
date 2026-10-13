# -*- coding: utf-8 -*-
"""Prompt helper routed through the SYSTEM AI Gateway with usage accounting.

Prompts remain centrally loaded. This helper never chooses a provider or calls
the Gateway's private compatibility transport; unavailable results remain
unavailable, with no provider or model fallback.

用法：
  from scripts.ai_gateway import chat
  content, provider, meta = chat("summarizer", "请摘要：...")
"""
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def _estimate_tokens(text):
    """粗略估算 token：中文字符约 1 token/字，ASCII 约 1 token/3 字符。"""
    if not text:
        return 0
    cjk = sum(1 for ch in text if '\u4e00' <= ch <= '\u9fff')
    other = len(text) - cjk
    return cjk + other // 3


def chat(role, user_content, temperature=0.3, max_tokens=None, model=None):
    """Call the public SYSTEM Gateway API and record the observed route.

    返回 (content, provider, meta)：
      meta = {role, elapsed_s, in_tokens, out_tokens, cache_hit}
    失败时 content 为 None；本 helper 不切换 provider 或伪造结果。
    """
    from scripts.prompt_registry import load_system_prompt
    from lumenis.system.ai_gateway.core import chat as gateway_chat

    system = load_system_prompt(role)  # 固定前缀（KeyError 会暴露角色拼写漂移）
    t0 = time.time()
    try:
        content, route, gateway_meta = gateway_chat(
            system, user_content, temperature=temperature,
            max_tokens=max_tokens or 1200, model=model, use_cache=False,
        )
    except Exception:
        content, route, gateway_meta = None, "provider_disabled", {}
    elapsed = time.time() - t0
    in_tok = _estimate_tokens(system) + _estimate_tokens(user_content)
    out_tok = _estimate_tokens(content or "")
    try:
        from scripts.ai_budget import record
        record(route, model or (gateway_meta.get("model") if isinstance(gateway_meta, dict) else None) or route,
               "gateway:" + role, bool(content),
               elapsed, in_tok + out_tok, note="",
               in_tokens=in_tok, out_tokens=out_tok, cache_hit=None)
    except Exception:
        pass  # budget 记录失败不影响调用结果
    return content, route, {
        "role": role, "elapsed_s": round(elapsed, 2),
        "in_tokens": in_tok, "out_tokens": out_tok, "cache_hit": None,
    }


def chat_json(role, user_content, temperature=0.1, max_tokens=1200, model=None, max_retries=1):
    """结构化输出统一入口（对齐 outputguard guarded_generate 理念：校验->修复->重试）。

    调公开 Gateway chat（固定 system 前缀）→ repair_json 解析（8 策略修复）→ 失败生成重试提示再试。

    返回 (data, provider, meta)：
      data      修复/解析后的 Python 对象（成功）或 None（失败，调用方降级）
      meta      {role, attempts, strategies, elapsed_s}
    """
    from lumenis.system.ai_gateway.core import chat as gateway_chat
    from scripts.prompt_registry import load_system_prompt
    from scripts.json_repair import repair_json

    system = load_system_prompt(role)
    prompt = user_content
    attempts = 0
    strategies = []
    t0 = time.time()
    route = "provider_disabled"
    # A failed provider call or an empty response must still produce a valid
    # failure result and budget record when max_retries is zero.
    data = None
    content = None
    for _ in range(max_retries + 1):
        attempts += 1
        try:
            content, route, gateway_meta = gateway_chat(
                system, prompt, temperature=temperature, max_tokens=max_tokens,
                model=model, use_cache=False,
            )
        except Exception:
            content, route, gateway_meta = None, "provider_disabled", {}
        if not content:
            continue
        data, applied = repair_json(content)
        if data is not None:
            strategies.extend(applied)
            break
        # 修复失败 -> 重试提示（告诉模型上次数值 JSON 损坏，要求只输出合法 JSON）
        if _ < max_retries:
            prompt = ("上一次输出不是合法 JSON，请只返回一个合法的 JSON 对象（不要代码块、不要解释文字）。"
                      "\n原始要求：" + user_content)
    elapsed = time.time() - t0
    try:
        from scripts.ai_budget import record
        in_tok = _estimate_tokens(system) + _estimate_tokens(user_content)
        out_tok = _estimate_tokens(content or "")
        model_id = model or (gateway_meta.get("model") if isinstance(gateway_meta, dict) else None) or route
        record(route, model_id, "gateway:" + role + ":json", data is not None,
               elapsed, in_tok + out_tok, note="", in_tokens=in_tok, out_tokens=out_tok,
               cache_hit=None)
    except Exception:
        pass
    return data, route, {"role": role, "attempts": attempts,
                            "strategies": strategies, "elapsed_s": round(elapsed, 2)}
