# 轻量 LLM 结构化输出修复 · 2026-09-03

> 研究来源：**outputguard**（ndcorder/outputguard, MIT, 2026-05）——15 修复策略 + JSON Schema 校验 +
> 重试提示 + guarded_generate；288 个 OpenRouter 模型实测 100% 可用（78% 直接有效 + 22% 自动修复，
> 最高频修复为 strip_fences / extract_json / fix_truncated）。
> 能力提取：核心修复策略子集（纯标准库，零重依赖），服务 ZBC 的 LLM 输出解析（智谱等）。

## 一、为什么

LLM 结构化输出常损坏（markdown fence、单引号、尾随逗号、裸键、截断、Python 字面量）。
ZBC 的 intelligence 大量 json.loads 解析，损坏会导致分析失败/无效 AI 调用。
outputguard 实测：**22% 的 LLM 输出需要自动修复**——修复层直接提升可用率。

## 二、落地

### scripts/json_repair.py（8 策略按序）
| 策略 | 作用 |
|---|---|
| strip_fences | 去 `json code fence（LLM JSON 第一问题） |
| extract_json | 抽取首个 { } / [ ]（剥离解说文字） |
| fix_booleans | True/False/None -> true/false/null |
| fix_keys | 裸键 {a:1} -> {"a":1} |
| fix_quotes | 单引号 -> 双引号 |
| fix_commas | 去尾随逗号 |
| fix_truncated | 未闭合字符串补引号 |
| fix_closers | 补齐未闭合括号 |

### ai_gateway.chat_json（对齐 guarded_generate 理念）
固定 system 前缀 → 调 _chat → repair_json 修复 → 失败生成重试提示再试（max_retries）→ budget 记录。

## 三、验证
- json_repair 单测 6/6（干净/去fence/剥离解说/引号+布尔+逗号/截断/空输入）
- chat_json 单测 2/2（修复损坏输出 1 次成功 / 失败重试 2 次成功）
- 零重依赖（纯标准库）
