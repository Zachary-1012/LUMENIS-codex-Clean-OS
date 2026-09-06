# -*- coding: utf-8 -*-
"""AI Provider 连通性验证。"""
import ai_channel
ai_channel.ensure_env_loaded()
import os, json, urllib.request

print("=== OLLAMA ===")
try:
    req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
    with urllib.request.urlopen(req, timeout=5) as r:
        data = json.loads(r.read())
        models = [m["name"] for m in data.get("models", [])]
        print(f"Ollama ACTIVE, models: {models}")
except Exception as e:
    print(f"Ollama UNAVAILABLE: {type(e).__name__}: {e}")

print()
print("=== ZHIPU ===")
try:
    zhipu_key = os.environ.get("ZHIPU_API_KEY", "")
    print(f"ZHIPU_API_KEY configured: {bool(zhipu_key)} (len={len(zhipu_key)})")
    print(f"ZHIPU_BASE_URL: {os.environ.get('ZHIPU_BASE_URL')}")
    print(f"ZHIPU_MODEL: {os.environ.get('ZHIPU_MODEL')}")
    print(f"ZHIPU_STRONG_MODEL: {os.environ.get('ZHIPU_STRONG_MODEL')}")
except Exception as e:
    print(f"Zhipu config error: {e}")

print()
print("=== ARK (Doubao) ===")
try:
    ark_key = os.environ.get("ARK_API_KEY", "")
    print(f"ARK_API_KEY configured: {bool(ark_key)} (len={len(ark_key)})")
    print(f"ARK_BASE_URL: {os.environ.get('ARK_BASE_URL')}")
    print(f"ARK_MODEL: {os.environ.get('ARK_MODEL')}")
except Exception as e:
    print(f"ARK config error: {e}")

# 实际调用智谱
print()
print("=== ZHIPU ACTUAL CALL ===")
try:
    import ark_llm
    # 检查 ark_llm 的接口
    funcs = [x for x in dir(ark_llm) if not x.startswith("_")]
    print(f"ark_llm exports: {funcs}")
except Exception as e:
    print(f"ark_llm import: {type(e).__name__}: {e}")

try:
    import ai_api
    funcs = [x for x in dir(ai_api) if not x.startswith("_") and callable(getattr(ai_api, x))]
    print(f"ai_api callables: {funcs[:20]}")
except Exception as e:
    print(f"ai_api import: {type(e).__name__}: {e}")
