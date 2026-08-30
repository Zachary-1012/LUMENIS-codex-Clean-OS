# Development Command Console

Development Command Console v0.1：将自然语言开发需求转换为可执行、可验收、可追溯的工程任务。

## 当前状态

- Local-only MVP
- 不调用外部 AI
- 不修改生产代码
- 不自动提交 GitHub 业务代码
- 不自动部署
- 数据仅保存于浏览器 localStorage

## 核心流程

自然语言需求 → 工程任务合同 → AI 执行指令 → 人工/后续自动验收

## 完成等级

- L0 Concept
- L1 Planned
- L2 Implemented
- L3 Tested
- L4 E2E Verified
- L5 Production

没有证据不得升级完成等级。

## GitHub 集成路线

V0.2：读取仓库、分支、Commit、变更文件。

V0.3：接入测试回执和 Diff 审计。

V0.4：接入开发 AI / Agent。

V0.5：形成任务 → GitHub → 测试 → 审计闭环。

## 安全边界

本 MVP 独立于 Z-Brand Core 生产业务链，先验证产品闭环，再逐步接入 GitHub API 和自动化能力。