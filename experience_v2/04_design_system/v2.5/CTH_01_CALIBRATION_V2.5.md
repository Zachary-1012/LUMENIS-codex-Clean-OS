# CTH-01 Calibration V2.5 — 商业运营总览（第二校准母版）
Realm = Operational。Subject-first：以当前 Selected Subject 为上下文的运营指挥视图。

## 1. 叙事链（用空间/层级体现，不画成流程图）
Selected Subject → Situation → Facts → Relationships → Evidence → Finding/Risk → Decision → Action → Outcome。

## 2. 页面结构（真实渲染）
- L1：eyebrow「序境·商业运营」+ 衬线大标题「商业运营总览」+ 口径说明（以当前 Subject 为上下文，全部可追溯）。
- 头部动作：生成运营简报（primary）/ 切换时间范围 / 导出（ghost/文字）。
- L2 Facts：4 个浮动 KPI 字段（今日到店客流/会员销售占比/在线负面声量/在办事件），大 tabular 数、delta、spark、实时点，发丝分隔，无白卡盒。
- L3：主区图表（近30天客流 vs 销售指数，多系列黑/语义色，实体面 containment 合理）+ 编辑式洞察（衬线 pull-quote，行内强调 18–21/B3，依据 EV 引用）。
- L3：最新事件（Point-on-Axis 时间线，高/中风险标签三编码）+ 风险开放字段（高风险72/中风险46，level dot+meter，去左侧色条）。
- 右栏 Context：工作上下文 + 证据列表（EV-7701/7704/7710）。

## 3. Operational 方言参数
data-realm=operational：`--lum-editorial-gap` 收紧（18–34）、`--lum-axis-strength .34`（秩序更强）、`--lum-trace-strength 1`（Trace 优先）。导航 active 为短墨条（序轴指示），运营密度高于 BMP。

## 4. 数据诚实
- 所有数值标注来自 Canonical（EV: canonical_metrics）；多系列趋势区分但不用紫蓝。
- 风险等级：颜色+图标+文字；缺数据走 STATE 语义，不补 0。
- 事件/风险可下钻（Return 归点：面包屑+context 常驻）。

## 5. 响应式
≥1024 主侧双栏+右 context；768 context 抽屉、KPI 2 列；≤430 单列、图表 aspect-ratio、事件时间线竖排、风险字段堆叠；触控达标。

## 6. 校准通过证据
1440 light 截图零 console 错误；KPI 字段化、洞察衬线+证据、风险去色条成立；dark 版反相一致（见基线目录）。作为 CTH-02..10 的母版：同密度、同 Trace 优先、同字段语言，差异只在业务组件。
