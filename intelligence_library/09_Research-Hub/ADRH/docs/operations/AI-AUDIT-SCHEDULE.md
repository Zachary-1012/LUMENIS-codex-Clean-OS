# AI 双轨审计调度基线

> Protocol ID: HUB-OPS-AI-AUDIT-SCHEDULE-V1
> Effective: 2026-08-31
> Timezone: Asia/Shanghai (UTC+08:00)
> Scope: Z-Brand-Core / SICI-Core / Development-Command-Console + Research Hub

## 1. 固定时序

豆包负责工程巡检：

| 北京时间 | UTC | Agent | 范围 | 结果 |
|---|---:|---|---|---|
| 10:00 | 02:00 | 豆包 | 三产品仓库 | Inspection Evidence + Handoff |
| 13:00 | 05:00 | 豆包 | 三产品仓库 | Inspection Evidence + Handoff |
| 15:00 | 07:00 | 豆包 | 三产品仓库 | Inspection Evidence + Handoff |
| 21:00 | 13:00 | 豆包 | 三产品仓库 | Inspection Evidence + Handoff |
| 24:00 | 16:00 | 豆包 | 三产品仓库 | Inspection Evidence + Handoff |

ChatGPT 的对应独立审计窗口为豆包完成后约 1 小时：11:00 / 14:00 / 16:00 / 22:00 / 01:00（次日）。

> GitHub Actions 是工程巡检的定时执行器；ChatGPT 审计不是 GitHub Actions 自动冒充的结果。ChatGPT 必须读取实际最新 SHA 和豆包 Evidence 后独立复核。

## 2. 每轮固定顺序

```text
豆包：Audit → Test/Inspect → Evidence → 留给 ChatGPT 的 Handoff
                         ↓
ChatGPT：重新读取四库事实 → 独立 Audit → 对比差异 → 分类 → 留给豆包的 Next Instruction
                         ↓
下一轮豆包：读取上一轮 ChatGPT Handoff，再执行
```

任何一方发现远程出现新 Commit：立即 stop-and-reread，不基于旧 SHA 继续。

## 3. 分类规则

每轮发现必须归入：

- `P0` Critical / 安全或生产阻断
- `P1` 高优先级 / 交付或核心能力风险
- `P2` 中优先级 / 工程质量、可维护性、效率
- `INFO` 观察项 / 学习材料 / 非阻断优化

同时标记生命周期：`NEW` / `REGRESSION` / `UNCHANGED` / `RESOLVED` / `DEFERRED`。

## 4. 推送隔离

- 豆包提交必须明确标记 `AI=DOUBAO`。
- ChatGPT 直接写入 GitHub 时必须明确标记 `AI=CHATGPT`。
- 不得使用对方的 Agent 名义提交。
- 不得把对方 Evidence 复制成自己的 Evidence。
- 每次工程提交必须在 commit body 或对应 handoff 中写明 `Research ID`、观察 SHA、变更范围、测试状态。

## 5. 五轮后的整合

每完成一个自然日的 5 次工程巡检：把当天结果按 `P0/P1/P2/INFO` 与 `NEW/REGRESSION/RESOLVED/DEFERRED` 汇总为一个 Daily Integration Record。

每 7 个 Daily Integration Record 再形成 Weekly Learning Summary。汇总只做分类、去重、趋势分析和研究入口，不删除原始 Evidence。

## 6. 不自动升级

定时巡检只能发现、验证、记录和提出候选项；不得自动：

- 修改生产逻辑
- 修改永久基线
- Promotion 到 reusable
- Release / Deploy
- 删除失败记录

需要开发时，重新进入 `CHATGPT-INTERVENTION-PROTOCOL.md` 的九阶段流程。
