# LUMENIS State Semantics V2.5
数据状态是生产真相的一部分：**0 ≠ NULL ≠ UNKNOWN ≠ NOT_AVAILABLE ≠ STALE ≠ ERROR**。UI 必须如实区分，禁止把缺失渲染成 0。

## 1. 状态全集（components.js STATE_ORDER，13 态）
| 状态 | 含义 | UI 表达（.lum-state） | 禁止 |
|---|---|---|---|
| loading | 加载中 | 与终态同形 skeleton | 用通用转圈替代内容骨架 |
| empty | 确为空集合 | 说明这里放什么 + 单一下一步 | 只写「无数据」 |
| unknown | 真值未知 | 中性 `UNKNOWN`（mono）+ 原因 | 猜一个值、补 0 |
| not_available | 能力/字段不可用 | `N/A` + 说明 | 显示 0 或 — 冒充数值 |
| stale | 数据过期 | 过期标记 + 最后更新时间 | 当实时数据用 |
| error | 出错 | 内联、可行动、相邻报错 | 「出错了」无动作 / window.alert |
| restricted | 无权限查看 | 锁标 + 申请权限入口 | 泄漏受限内容 |
| permission_required | 需授权动作 | 授权说明 + 动作 | 静默失败 |
| approval_required | 需审批 | 审批链/状态 | 直接执行 |
| processing | 进行中 | 阶段化进度 | 无期限转圈 |
| completed | 完成 | 完成态 + 结果/回链 | — |
| warning | 警告 | 语义色+图标+文字（三编码） | 只靠颜色 |
| risk/critical | 风险 | level dot + meter + 文案 | 只靠红色 |

## 2. 数值语义规则
- 真实 0：业务确为零（如「今日新增 0」），正常显示 0。
- NULL：字段存在但无值 → 显示 `—` 并在 tooltip/旁注说明 null。
- UNKNOWN：无法判定 → `UNKNOWN`，保留未知，进入 unknown-bindings。
- NOT_AVAILABLE：该能力/口径未提供 → `N/A`。
- 缺测/采集中：`--` 配 processing 小点，区别于 0。
- 时间双口径：`publish_datetime`（发布）与 `captured_at`（采集）分离显示，不混用。

## 3. 状态不只靠颜色
每状态同时具备：图标/形状 + 文案 +（必要时）颜色。色盲可辨；对比 ≥4.5:1。

## 4. AI 状态诚实度
- AI 输出必须带 confidence 与 limitation；低置信标 needs-review。
- fallback / mock / DESIGN_ONLY 数据必须可见地标记（原型 `data-source="prototype`），禁止 fake 200：API 返回 200 但内容是 fallback mock 时按 NOT_VERIFIED 处理。
- 文档存在、文件存在、route 存在都不等于能力可用（UNREACHED / BROKEN / FAKE_200_RISK 见契约层）。

## 5. 与契约的对应
状态枚举与 `12_contracts/STATE_REGISTRY.json` 对齐；后端缺失的状态能力进入 `BACKEND_GAP.json`，前端只做表达、不伪造数据。
