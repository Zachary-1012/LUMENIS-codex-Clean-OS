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

统一管理：

- Ollama Local AI
- Zhipu
- Codex/Sol Engineering Runtime
- Future Models

原则：根据成本、速度、复杂度、隐私、资源自动选择。

## AI Runtime Target Architecture

```
User
 ↓
LUMENIS Chat Interface
 ↓
Intelligence Router
 ↓
Local AI / Cloud AI / Engineering AI
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

不是用户聊天模型唯一依赖。

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