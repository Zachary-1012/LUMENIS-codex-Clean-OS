# S1 冲刺 Evidence：智谱 AI 智能功能补强 · 2026-09-02

> 依据：用户指令"补 OpenAI 的智能功能，不是 api key，现在只有一个 api key，就是云智"→ 澄清后确认为**智谱(ZHIPU)**，云智(ARK)删除。
> 状态：**COMPLETE**（E2E 验证 + 286 回归通过 + 已推送）

---

## 一、变更内容

### 1. AI Provider 切换
| 项 | 变更 |
|---|---|
| 云智(ARK) | 已停用：`.env` 中 ARK_API_KEY/ARK_MODEL/ARK_BASE_URL 注释保留；ark_llm.py 硬编码 key 已移除（安全修复 3521383） |
| 智谱(ZHIPU) | 激活：`AI_PROVIDER=zhipu`，key 在 .env（gitignore 保护） |
| 网关 | intelligence.py `_provider_config()` auto 分支 → 显式 zhipu，model=glm-4.5-air |

### 2. intelligence.py 新增智谱驱动 AI 能力（4 函数）
- `analyze_sentiment(text)` — 情感/摘要/关键词一站式（JSON 结构化）
- `generate_summary(text, max_length)` — 文本摘要
- `extract_keywords(text, num_keywords)` — 关键词提取
- `generate_report(title, data, report_type)` — 舆情报告生成
- 复用 _chat 网关 + redact_for_cloud 脱敏 + _json_from_text 解析；失败回退规则/空值，绝不崩溃

### 3. app.py /api/ark/* 路由改用智谱（5 端点）
- `/api/ark/status` `chat` `sentiment` `summary` `keywords` 全部走 intelligence（zhipu）
- 保留响应结构与前端兼容；provider 字段标记真实来源

---

## 二、E2E 验证结果（真实系统 8321 端口）

| 接口 | 输入 | 结果 | provider |
|---|---|---|---|
| /api/ark/status | - | enabled:true, model:glm-4.5-air | zhipu |
| /api/ark/sentiment | 广州太古汇新店开业服务很好 | sentiment:1, label:positive, 10关键词 | zhipu |
| /api/ark/summary | 15周年活动文本 | 简洁摘要 | zhipu |
| /api/ark/keywords | 活动关键词 | 4关键词正确 | zhipu |
| /api/ark/chat | 确认接入 | "AI已成功接入智谱系统" | zhipu |

## 三、回归与安全
- ZBC 全量回归：**286 passed**（无破坏）
- 关键测试集：agent_security + ai + schema_registry = 39 passed
- 密钥安全：智谱 key 仅存 .env（gitignore），代码无硬编码；云端调用经 redact_for_cloud 脱敏

## 四、提交记录
- ZBC HEAD `88cd96f`（app.py 智谱路由）+ `234d2f8`（报告）已含全部改造，与 origin 同步
- intelligence.py 新函数在 HEAD `d109aca`/`234d2f8`

## 五、下一步（Sprint 2 候选）
- 智谱驱动的 review_note/summarize_event 已存在（intelligence 既有），可增强日报/周报 AI 摘要
- 结合 GitHub 标杆：SkillSpector 静态扫描 → security_scanner 增强（P1）
- 结合 OSAI P0：browser_runtime 长驻测试框架（P0 backlog）
