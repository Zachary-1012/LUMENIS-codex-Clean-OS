# -*- coding: utf-8 -*-
"""免费双通道在线冒烟（需 .env 已配 ZHIPU / DASHSCOPE key 且网络可达）：
主=智谱 GLM，备=千问 qwen-flash；并验证 auto 在主通道缺失时自动 failover。
接入/更换 key 后运行：.venv\\Scripts\\python tests\\test_llm_online.py
"""
import io, os, sys, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for line in io.open(".env", encoding="utf-8"):
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        k, v = line.split("=", 1); os.environ.setdefault(k.strip(), v.strip())
os.environ["AI_TIMEOUT_SECONDS"] = "40"
import intelligence

NOTE = {"title": "太古汇停车排队久",
        "content": "商场品牌很全、环境高级，但地下停车场排队太久，引导标识不清，体验打折"}
RULE = {"verified": True, "summary": "提及广州太古汇停车", "topics": ["停车"], "verify_reason": ""}

def run_provider(p):
    os.environ["AI_PROVIDER"] = p; intelligence._CACHE["ts"] = 0
    st = intelligence.ai_status()
    if not st["enabled"]:
        print(f"[{p}] 未配置，跳过"); return None
    res = intelligence.review_note(NOTE, RULE)
    print(f"[{p}] model={st['model']} -> 情感={res.get('sentiment')} 置信={res.get('confidence')} 来源={res['provider']} 摘要={res.get('summary')}")
    assert res["provider"] == p, f"{p} 未走通，回退到 {res['provider']}"
    return res

print("===== 主通道：智谱 GLM =====")
z = run_provider("zhipu")
print("===== 备通道：千问 qwen-flash =====")
q = run_provider("qwen")

print("===== auto 故障转移：去掉智谱 key，应自动落到千问 =====")
os.environ["ZHIPU_API_KEY"] = ""; os.environ["AI_PROVIDER"] = "auto"; intelligence._CACHE["ts"] = 0
st = intelligence.ai_status(); print("auto ->", st["provider"], st.get("model"))
assert st["provider"] == "qwen", "主通道缺失时未自动 failover 到千问"

print("===== 设置页 AI 测试同源函数 =====")
os.environ["AI_PROVIDER"] = "zhipu"; intelligence._CACHE["ts"] = 0
# 上面清空了内存中的 zhipu key，仅用于本进程，不影响 .env；这里直接用 qwen 验证连接函数
os.environ["AI_PROVIDER"] = "qwen"; intelligence._CACHE["ts"] = 0
print(json.dumps(intelligence.test_connection("用一句中文说明你能做舆情分析"), ensure_ascii=False))

if z and q:
    print("\n免费双通道（智谱主 / 千问备）在线冒烟全部通过")
