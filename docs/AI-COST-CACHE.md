# AI 成本可观测：Prompt Cache 优化层 · 2026-09-03

> 研究来源：**llm-api-pricing / llm-cost-calculator**（OpenRouter 价格表分析）+ **Rapid-MLX**（本地引擎 prompt cache）。
> 关键洞察：**cached input 定价远低于非缓存**——agent 实测 token mix 中约 95.6% 为缓存输入、
> 缓存读价比列表价低 ~6.5x。固定 system 前缀最大化缓存命中是 AI 降本最有效的单一手段。

## 一、为什么

ZBC 以智谱为主力（配额约 44.3M token）、豆包最低。若智谱支持 prompt caching，
重复的固定 system 前缀（分析模板/报告指令/角色设定）命中缓存可显著降低消耗，配额利用率翻倍。

## 二、落地：ai_budget 可观测层

| 能力 | 说明 |
|---|---|
| record 扩展 | 可选 --in <in_tokens> --out <out_tokens> --cache <1/0>（向后兼容，缺省不影响旧调用） |
| summary.cache | known/hit/hit_rate/in_tokens/out_tokens/cacheable_input_share |
| cacheable_input_share | 输入 token 占总 token 比例（缓存优化潜力上限） |

## 三、用法

python scripts/ai_budget.py record zhipu glm-4.7 summarize 1 1.2 1000 --in 800 --out 200 --cache 1
python scripts/ai_budget.py summary        # 含 cache 统计

## 四、优化指引（2026-09-03 已落地）

✅ **已确认智谱上下文缓存为隐式自动**（docs.bigmodel.cn/cn/guide/capabilities/cache：自动识别重复前缀，
缓存命中 token 按优惠价计费、缓存存储限时免费；响应返回 usage.prompt_tokens_details.cached_tokens）。

✅ **固定前缀收敛已落地**：config/prompts/lumenis-prompts.yaml（4 角色版本化前缀）+ scripts/prompt_registry.py（强制加载、禁内联），
	ests/test_prompt_registry.py 强制逐字符稳定（改前缀必须 bump version）。缓存命中前提达成。

1. 调用方改用 prompt_registry.load_system_prompt(role) 加载前缀（禁止内联复制）。
2. 观测 ai_budget summary.cache：hit_rate 从 None/低 → 稳定高，即缓存生效。
3. 注意：缓存优惠计费仅适用标准 API，资源包/GLM Coding Plan 套餐不适用（文档明示）；机制本身仍加速响应。

## 五、验证

- 单测 2/2（带 cache 字段统计 + 向后兼容）
- 全量回归 EXIT=0
- Evidence：staging/ai-budget.jsonl、git commit、OSAI learning-feed
