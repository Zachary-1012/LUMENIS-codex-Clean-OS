# 序境 · 零号序列一键执行 · 全量验证记录（Evidence #07）

- 日期：2026-09-04 · 状态：VERIFIED-PASS
- 依据：《序境·零号序列一键执行》以 GitHub 两仓库最新状态为唯一基线

## 一、双库同步（基线一致）
- ZBC：fetch+merge origin/main 完成（含并行会话 RELEASE_AND_AUTORUN_GATE / TWIN_EXECUTION_GATE），本地/远端同步
- OSAI：fetch+merge 完成（含 CANONICAL_REGISTRY / LATEST_RESEARCH_ADOPTION_GATE / TWIN_EXECUTION_GATE），本地/远端同步
- 无冲突，无 ahead/behind

## 二、全量回归（真实验证）
- 命令：pytest tests -m "not online" --ignore=tests/test_browser_e2e.py -k "not alembic"
- **reg65 EXIT=0（全量通过，含 1 skip）**
- 覆盖：KOS（ops/paid/execution）、报告母模型、三语、采集窗口、搜索增强等全部模块

## 三、生产服务健康（8201）
| 端点 | 结果 |
|---|---|
| /healthz | 200 ok |
| /api/system/health | ok |
| /api/kos/overview | ok · 375 profiles |
| /api/event-graph/stats | ok · 16 events |
| /api/browser-runtime/status | ok |

## 四、架构/命名/合规核对（无 GAP）
- 用户可见产品名 = 序境（此前 Evidence #04/#05/#06 已截图/验证）；Zachary 仅保留为认证凭证（Basic Auth Zachary:Zachary01）与研发标识，符合序境命名体系（不破坏）
- 采集安全 Gate：每日 00:00/12:00 各一次、最多 2 次、手动 ≤30min、可开关（已实现 xujing_auto_hours）
- AI 权限边界：HCG 状态机 + GATED_ACTIONS（reply_send/outreach_send/email_send/paid_media/publish/reward_issue 等）+ AI_GENERATED→HUMAN_APPROVED→EXECUTING 锁链
- 数据/Evidence 规则：kos 375 条 59 字段、事件图谱 16 事件均可下钻至来源
- 双库边界：序境-Core（生产 Truth）/ 序境-Intelligence（研究/AI），无第三核心库

## 五、本次零号序列变更
- OSAI：序境/01-PRODUCT/RESEARCH_2026-09.md（前沿研究采纳记录，commit 4dd5ea1）
- ZBC：本轮为验证/同步为主，代码零改动（Cross-filter 等已在前序提交 a6c4ceb/8ae84dd）
- 并行会话归档（apple-ui/compat/ui_dashboard → 99-ARCHIVE）为并行工作，未触碰

## 六、结论
当前确定范围全量核对通过：架构清晰、测试通过、服务健康、命名统一、采集安全、AI 受控、双库协同、Evidence 可追溯。
