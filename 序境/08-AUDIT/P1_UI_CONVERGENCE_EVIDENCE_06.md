# 序境 P1 · Cross-Filter 联动 + CSS 收敛治理（Evidence #06）

- 日期：2026-09-04 · 状态：VERIFIED
- 依据：《序境》动态可视化（Cross-filter / Cross-highlight / 语义连续性）+ Lean Engineering（CSS token 单一来源）

## 一、Cross-Filter 通用框架（新增，纯增量）
- `static/js/xujing-crossfilter.js`：事件驱动 publish/subscribe 总线 + Cross-highlight 辅助
  - `XJ_CrossFilter.publish/clear/subscribe/getState/bind/refresh`
  - data-xf-dim / data-xf-value 声明式打标；`.xf-on` 高亮 / `.xf-dimmed` 淡化（+灰度，非只依赖颜色）
  - toggle（同值再点清除）、knownDims 集合（清空后仍刷新 UI）
- `static/css/xujing-crossfilter.css`：侘寂适配（墨黑描边 + 不透明度 + 移动端 0.45 保底可读）

## 二、首个真实落地：事件关系图谱
- 事件类型统计卡（营销/传播/舆情）→ 可点击筛选源；关系类型图例（触发/衍生/继发/并行）→ 可点击筛选源
- 16 个真实事件卡片打标 data-xf-dim（用 event_type_name 中文值，与统计卡对齐）
- 清除筛选卡（data-xf-clear）

## 三、E2E 验证（真实数据：16 事件 / 传播 13 / 舆情 2 / 营销 1）
| 场景 | 结果 |
|---|---|
| 点击「传播事件」 | .xf-on=14（1 统计卡+13 事件卡）· .xf-dimmed=5 |
| 再点（toggle 清除） | .xf-on=0 · .xf-dimmed=0 · state=None |
| 点击关系图例「并行」 | .eg-rel-tag.xf-on=1 |
| 再点关系图例 | 清除=0 |
| pageerror | 无 |

## 四、CSS 收敛治理（审计层，NO-BLIND-DELETE）
- `序境/08-AUDIT/CSS_CONVERGENCE_AUDIT_01.md`：32 个 CSS 加载顺序/体积/:root 变量/body 判定
- token 单一来源声明：`zbip-tokens.css`（Stone 权威）+ `zbip-theme-override.css`（序境覆盖层）
- LEGACY 候选登记（tokens-minimal/design-v8/v9/style/ui_optimized 等），删除需人工确认
- 组件级硬编码色值收敛列为 P2

## 五、变更清单（精确提交）
- static/js/xujing-crossfilter.js（新）
- static/css/xujing-crossfilter.css（新）
- static/js/v3_modules.js（eventGraph：init 绑定 + renderStats 筛选源 + renderEvents 打标 + event_type_name 对齐）
- static/index.html（加载 CF 资源）
- 序境/08-AUDIT/CSS_CONVERGENCE_AUDIT_01.md（新）
- 序境/08-AUDIT/P1_UI_CONVERGENCE_EVIDENCE_06.md（本文件）
