# -*- coding: utf-8 -*-
"""AI Gateway：生产 AI 调用统一入口（固定前缀收敛 + budget 统一记录）。

把「智谱隐式缓存命中」与「AI 成本可观测」落到真实调用：
  1. 固定 system 前缀：从 config/prompts/zbc-prompts.yaml 加载（逐字符稳定→缓存命中前提），
     禁止调用方内联复制（防前缀漂移）。
  2. 统一 budget 记录：每次调用写 ai-budget.jsonl（含 in/out token 估算 + 可选 cache 标记），
     供 Observatory 消费，观测 cache.hit_rate。
  3. 动态内容一律放 user 消息，绝不拼进 system 前缀。

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
    """统一 AI 调用：固定 system 前缀 + 智谱/本地 + budget 记录。

    返回 (content, provider, meta)：
      meta = {role, elapsed_s, in_tokens, out_tokens, cache_hit}
    失败时 content 为 None（由调用方降级，绝不阻断主流程）。
    """
    from scripts.prompt_registry import load_system_prompt
    from lumenis.system.ai_gateway.core import _chat

    system = load_system_prompt(role)  # 固定前缀（KeyError 会暴露角色拼写漂移）
    t0 = time.time()
    try:
        content, provider = _chat(system, user_content, temperature=temperature,
                                  max_tokens=max_tokens or 1200, model=model)
    except Exception:
        content, provider = None, "unknown"
    elapsed = time.time() - t0
    in_tok = _estimate_tokens(system) + _estimate_tokens(user_content)
    out_tok = _estimate_tokens(content or "")
    try:
        from scripts.ai_budget import record
        record(provider, model or provider, "gateway:" + role, bool(content),
               elapsed, in_tok + out_tok, note="",
               in_tokens=in_tok, out_tokens=out_tok, cache_hit=None)
    except Exception:
        pass  # budget 记录失败不影响调用结果
    return content, provider, {
        "role": role, "elapsed_s": round(elapsed, 2),
        "in_tokens": in_tok, "out_tokens": out_tok, "cache_hit": None,
    }


def chat_json(role, user_content, temperature=0.1, max_tokens=1200, model=None, max_retries=1):
    """结构化输出统一入口（对齐 outputguard guarded_generate 理念：校验->修复->重试）。

    调 _chat（固定 system 前缀）→ repair_json 解析（8 策略修复）→ 失败生成重试提示再试。

    返回 (data, provider, meta)：
      data      修复/解析后的 Python 对象（成功）或 None（失败，调用方降级）
      meta      {role, attempts, strategies, elapsed_s}
    """
    from lumenis.system.ai_gateway.core import _chat
    from scripts.prompt_registry import load_system_prompt
    from scripts.json_repair import repair_json

    system = load_system_prompt(role)
    prompt = user_content
    attempts = 0
    strategies = []
    t0 = time.time()
    provider = "unknown"
    for _ in range(max_retries + 1):
        attempts += 1
        try:
            content, provider = _chat(system, prompt, temperature=temperature,
                                      max_tokens=max_tokens, model=model)
        except Exception:
            content = None
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
        record(provider, model or provider, "gateway:" + role + ":json", data is not None,
               elapsed, in_tok + out_tok, note="", in_tokens=in_tok, out_tokens=out_tok,
               cache_hit=None)
    except Exception:
        pass
    return data, provider, {"role": role, "attempts": attempts,
                            "strategies": strategies, "elapsed_s": round(elapsed, 2)}
