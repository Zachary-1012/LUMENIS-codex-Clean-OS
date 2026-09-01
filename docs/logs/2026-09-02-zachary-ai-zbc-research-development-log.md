# Zachary AI × Z-Brand-Core 研发日志

日期：2026-09-02

## 双向反哺

ZBC 是独立品牌/舆情业务系统，并向 Zachary AI 提供真实世界 Evidence；Zachary AI 的成熟 Research、Reasoning、Agent、Memory、Evaluation、Multimodal、Runtime 能力反哺 ZBC。

ZBC 当前进入功能收口、稳定性、准确性、合规与上线阶段。AI 研发不得破坏核心业务逻辑。

## 本轮 Zachary AI 已落地产出

- Core Runtime：State / Task / Capability / Evidence / Evaluation / Memory / Recovery / Promotion
- Runtime API：统一异步执行入口、Provider/Tool 调用、事件 Hooks、失败状态回写
- Tool Registry：权限门控、执行审计
- ZBC Evidence Adapter：只读、保留数据溯源字段
- Core contract tests + Runtime integration tests + CI

## ZBC 重点

继续推进小红书采集完整性、字段准确性、评论关联、图片/OCR/VLM、Event 聚合、Evidence、多平台采集、稳定性与合规。

目标是完整、准确、可引用、可验证；不以绕过平台安全控制或规避封控为目标。采用授权、公开数据边界、限速、缓存、失败恢复、可追溯采集及平台规则遵循提高可靠性。

核心主体逻辑继续保护：SUBJECT_WORDS、SUBJECT_EXCLUDE_WORDS、subject_hit()、aggregate_events()、build_daily_report 主体过滤；AI 不得越权覆盖主体判断。

## Zacreate

Requirement → Intent → Audience → Objective → Research → Evidence → Insight → Strategy → Creative → Channel/Asset → Execution → Evaluation → Iteration。

作为 Zachary AI 的 Creative Intelligence 能力域，服务品牌、产品、展览、活动、内容、社交媒体和整合营销传播。

## 真实性

能力必须经过源码、Runtime、测试、Evidence、失败恢复与可迁移性验证；未验证能力不标记为生产完成。
