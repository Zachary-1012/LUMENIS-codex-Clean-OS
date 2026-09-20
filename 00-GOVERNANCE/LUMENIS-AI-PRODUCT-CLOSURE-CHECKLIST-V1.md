# LUMENIS AI Product Closure Checklist V1

## Purpose

用于 LUMENIS 从 AI Runtime 接入到 GPT-level Product Experience 收口阶段的验收清单。

原则：Local-first, Cloud-optional, Evidence-backed, Replaceable.

## 1. Chat Memory

- 项目上下文记忆
- 用户可控记忆
- 历史任务状态
- 记忆更新与删除

## 2. Context Manager

- 长对话压缩
- 多文档上下文
- Token预算管理
- 重要信息优先级

## 3. Tool Calling Framework

支持：

- 文件
- 数据库
- Git
- 浏览器
- 本地程序
- 外部API

要求：权限、日志、Evidence、可回放。

## 4. Prompt / Skill Registry

- Skill注册
- Prompt版本管理
- 能力模块
- 任务模板

## 5. Evaluation System

- 正确率
- 幻觉率
- 稳定性
- Benchmark
- 回归测试
- 模型对比

## 6. Model Routing

SYSTEM AI Gateway 统一管理产品运行模型：

- Ollama Local AI
- Zhipu
- Future Models

原则：根据成本、速度、复杂度、隐私、资源自动选择。

Canonical owner：`lumenis/system/ai_gateway/`。`local_ai_client.py` 和现有 `/api/local-ai/*` 是需保留行为后收敛的兼容调用路径，不得形成第二或第三个 AI Gateway。

## AI Runtime Target Architecture

```
User
 ↓
LUMENIS Chat Interface
 ↓
Intelligence Router
 ↓
Local AI / Approved Cloud AI / Deterministic Rules
 ↓
Agent + Tools
 ↓
Evidence
 ↓
Response
```

## Local AI Independence Gate

必须验证：

- Zhipu关闭
- 云AI关闭
- 本地模型仍可运行
- 真实业务分析完成
- Evidence生成
- 结果返回产品层

## Engineering AI Boundary

Codex / OpenCode：

用于：

- 研发
- 审计
- 测试
- 自动化

OpenCode 的当前仓库配置位于 `.opencode/opencode.json`。Codex/OpenCode 不进入上述产品 Model Routing，不是 Flutter 功能、Product Core 必需依赖、用户聊天模型或 Production Truth owner。工程工具可以调用现有测试和受限本地检查，但不能绕过产品 Permission/Evidence 边界。

## Source-audited current disposition

- Ollama：canonical Gateway、provider probe、真实 backend callers 和 App provider-state binding 已存在；daemon、模型、真实推理、fallback 和 Evidence 必须在 Round 2 现场验证后才能标记 `ACTIVE / VERIFIED`。
- OpenCode：工程配置已存在；当前产品源码没有 OpenCode runtime caller。其正确状态是 `ENGINEERING CONFIG PRESENT`，不是丢失的产品功能。
- AI-01：当前 App 只显示 provider/能力状态，真实意图提交与 Evidence Trace 尚未闭环；不得把状态页写成完成的 AI workflow。

## Research Optimization Layer

包含：

- Auto Research
- Performance Race
- Execution Efficiency

定位：持续优化系统，不直接成为Production Truth。

## Production Closure Gate

进入 GPT-Level Experience Ready 前必须通过：

- Chat Memory PASS
- Context PASS
- Tools PASS
- Skills PASS
- Evaluation PASS
- Routing PASS
- Local AI PASS
- Fallback PASS
- Evidence PASS
- Security PASS

## Status

当前：Governance Requirement

最终状态：

- SHADOW_READY
- READY_FOR_AUDIT
- PRODUCTION_CANDIDATE
- PRODUCTION_APPROVED

禁止未验证声明完成。
