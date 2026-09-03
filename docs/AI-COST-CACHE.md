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

## 四、优化指引（评估后执行）

1. 确认智谱 glm-4.7 是否支持 prompt cache（bigmodel API 文档）。
2. 若支持：把 AI 调用 system prompt 收敛为**固定前缀模板 + 动态追加**，前缀保持逐字符稳定（缓存命中前提）。
3. 观测 cache.hit_rate：从 None/低 → 稳定高，即缓存生效。
4. 未支持前：保持"固定前缀"编码纪律，为未来命中做准备，零成本。

## 五、验证

- 单测 2/2（带 cache 字段统计 + 向后兼容）
- 全量回归 EXIT=0
- Evidence：staging/ai-budget.jsonl、git commit、OSAI learning-feed
