# UI × INTERACTION × UNIVERSAL DATA × PODCAST
## Research / Execution Specification V2 — 2026-09-04

本文件是 UI、窗口、跳转、通用数据入口、Canonical Table、动态可视化、KOS/KOC/UGC、舆情、内容生产与播客的统一实施契约。

## 0. 绝对原则
Find → Audit → Map → Reuse → Implement → Test → Gate → Commit。
禁止凭空重做、平行 UI、平行计算、页面自行计算、假数据验收、只做视觉 Demo、播客孤立化、AI 覆盖 Production Truth。

## 1. 源码先行
```bash
pwd
find . -maxdepth 5 -type f | sort
rg -n "Shell|sidebar|workspace|route|popover|drawer|dialog|modal|table|grid|chart|visual|animation|realtime|websocket|SSE|stream|import|upload|parser|CSV|XLSX|PDF|PPT|PPTX|image|video|OCR|ETL|normalize|dedup|schema|function|export|evidence|health|KOS|KOC|UGC|podcast|episode|idea|vault|knowledge" . --glob '!node_modules/**' --glob '!venv/**' --glob '!data/**'
```
建立：功能/页面 → 文件 → symbol/component → route → 当前行为 → 数据源 → 依赖 → 测试 → 修改方案。名称不匹配时继续按 symbol/class/route/API/DB/visible text 搜索。

## 2. 窗口与层级必须由功能决定
```text
用户任务 → 对象复杂度 → 上下文需求 → 是否编辑/确认 → 信息密度 → 功能层级 → 窗口类型 → 跳转
```
Popover：轻量控制；Drawer：保留当前页面上下文查看对象；Dialog：确认/短表单/有后果操作；Full Page：独立对象信息架构；Full Workspace：复杂连续任务；AI Panel：当前上下文辅助；AI Workspace：复杂研究/创作。

## 3. 跳转
Navigation→Module Page；List Row→Context-preserving Drawer；Drawer→View Full→Full Page；Evidence→Evidence Detail；Edit→Inline/Dialog；Dangerous→Confirm Dialog；Complex Task→Full Workspace；AI Quick→Panel；AI Complex→Workspace。
关闭 Drawer 恢复 route/query/filter/sort/pagination/scroll/selection；深链、返回、刷新状态必须测试。

## 4. 视觉升级
允许脱离旧视觉重新设计，但必须研究已提供的参考资产，建立 Reference Matrix：Reference→Layout→Typography→Density→Motion→Interaction→Data Display→Reusable Principle。吸收编辑感、模块化、高信息密度、沉浸媒体、精细动效、状态变化、时间线/关系可视化等原则，不复制单一作品。

目标：Editorial Intelligence × Operational Precision × Dynamic Data × Quiet Expressive Motion。
禁止 generic AI dashboard、无意义渐变/Glow、巨大 KPI 卡、每页独立语言、第二套 Shell。

## 5. Universal Data Ingestion
外部数据包括：采集器、CSV/XLSX/XLS、PDF、PPT/PPTX、DOC/DOCX、TXT/Markdown、JSON、API、数据库、复制文本、用户输入文字、图片、截图、音频、视频、链接等。

所有输入先进入统一 ingestion pipeline。

## 6. 两条合法数据路径
### Path A：需要计算
External Input→Raw Asset→Parser/OCR/Media Extractor→Schema→Normalize→Deduplicate→Programming Function→Deterministic Calculation→Canonical Data Table→Visualization Adapter Code→Dynamic Table/Chart/UI/Report/Export。

### Path B：输入已经是标准表格且不需业务重算
External Table→Schema→Normalize/Deduplicate→Canonical Data Table→Visualization Adapter Code→Dynamic Table/Chart/UI/Report/Export。

不能为了形式重复计算；Path B 也不得绕过验证。

非表格输入：Extraction→Structured Intermediate Data→（需要计算时）Function→Canonical Table；若只有原始内容，则停在 Structured Data/Evidence 层，不得伪造计算完成。

## 7. Canonical Table
Canonical Table 是唯一标准事实数据层，不是普通展示表。核心数据集记录 dataset_id、dataset_version、schema_version、source_type、source_asset_id、source_record_ids、transformation_version、calculation_version、formula_version、created_at、calculated_at、quality_status、evidence_refs。

核心指标必须能沿 Raw Record→Function→Formula→Canonical Value 追溯。

## 8. Visualization Adapter
Canonical Table→Visualization Dataset/Adapter→Dynamic Table / Chart / Metric / Timeline / Relation Graph / Map / Heatmap / Trend / Live View / Report / Export。
前端只呈现与交互，不重新定义业务事实。数据变化驱动可视化更新；ECharts 的动态数据机制可作为这一工程思想的参考。citeturn2search7turn2search10

## 9. 实时
区分 Static / Periodic Refresh / Incremental Update / Streaming / Event-driven Update。每个实时模块声明 source_updated_at、received_at、processed_at、visualized_at、latency、freshness_status。UI 状态：LIVE / UPDATING / STALE / DEGRADED / OFFLINE / ERROR。优先增量更新，不做无意义全量重绘。

## 10. Data Gate
G01 Input Integrity→G02 Extraction→G03 Schema→G04 Normalization→G05 Dedup→G06 Function/Calculation→G07 Canonical→G08 Visualization Dataset→G09 UI Consistency→G10 Export Consistency。FAIL/UNKNOWN/MISSING/MISMATCH 必须 BLOCKED/NEEDS_REVIEW。
建立 Golden Dataset；schema/parser/function/formula/query/aggregation/visualization/export 变化均需回归。

## 11. KOS/KOC/UGC
KOS：Identity→Positioning→Content Ability→Performance→Distribution→Interaction Quality→Audience Fit→Influence→Risk→Cooperation Value→History→Recommendation→Evidence。
KOC：Identity→Real Experience→Content Quality→Interaction→Word of Mouth→Spread→Brand Fit→Risk→Recommendation→Evidence。
UGC：Original Record→Author→Time→Content→Topic→Emotion→Interaction→Spread→Brand→Event→Risk→Evidence。原始内容必须保留，AI 只能增加分析层。

## 12. 舆情对象
所有 Note/Topic/Event/Risk 遵循 Identity→Source→Raw/Original→Structured Fields→Analysis→Relations→Risk→Evidence→Action。Event 额外支持 First/Latest Seen、Timeline、Peak、Volume、Velocity、Spread、Related Objects、Status、Resolution；Topic 支持时间窗口比较；Risk 支持 Trigger/Severity/Confidence/Evidence/Status。

## 13. Podcast：平台内部独立 Workspace
Podcast 与 KOS 等模块同属平台内部一级业务 Workspace，共享平台 Shell、Canonical Data、Evidence、AI、Knowledge、Export，但拥有自己的内部信息架构。绝不能做成外置工具或第二套平台。

```text
Podcast
├─ Program
├─ Idea Vault
├─ Research
├─ Episodes
├─ Production
├─ Content
├─ Audience
├─ Knowledge
└─ Review
```

## 14. Podcast UI
Program：Overview / Positioning / Audience / Seasons。
Idea Vault：Daily / Weekly / Monthly。
Research：Topic / Person / Event / Case / Evidence。
Episodes：List / Detail / Episode Workspace。
Production：Pre-production / Recording / Editing / Publishing。
Content：Clips / Xiaohongshu / Video / Poster / Social Copy。
Audience：Growth / Engagement / Feedback / Questions。
Knowledge：Episode / Research / Cross-reference。
Review：Performance / Feedback / What Worked / What Failed / Next Experiment。

## 15. Podcast 闭环
Daily Idea→Weekly Candidate→Research→Episode→Production→Publish→Audience→Review→Knowledge→New Idea。Idea 可进入 Drawer 编辑并晋级；Research Item 可打开 Evidence Drawer、加入 Research Set、生成 Insight、绑定 Episode；Episode List→Drawer→Full Workspace；Audience Question→Idea Vault；Review→Knowledge→New Idea。

## 16. Episode Workspace
复杂生产使用 Full Workspace：Header（Status/Save/Preview/Publish）＋左侧 Structure＋中间 Editor/Research/Script/Outline＋底部 Evidence/AI Assist/Notes/Version/Knowledge。不要用巨型弹窗替代工作区。

## 17. 内容模板
Template ID / Version / Input Schema / Prompt Version / Model Version / Output Schema / Human Review / Final Output / Performance。覆盖小红书、视频、海报、评论回复、播客发布文案、播客切片。AI 草稿与最终人工确认结果分离。

## 18. 动态可视化
时间→Timeline/Line/Area；排名→Bar/Dot；结构→Treemap/Stacked；关系→Network；事件→Timeline+Cluster；风险→Matrix；传播→Flow/Network；空间→Map；密度→Heatmap；实时→Streaming/Incremental；文本→Topic Cluster/Sentiment。交互按任务使用 hover/focus/filter/brush/zoom/drill-down/compare/time-window/pin/cross-highlight，不为动画而动画。

## 19. Evidence
UI Metric→Canonical Value→Calculation→Source Record→Evidence。优先 Evidence Drawer 保持上下文，必要时进入 Full Page。

## 20. AI 边界
AI：分析、分类、聚类、摘要、关系发现、草稿、研究辅助、建议。确定性层：Raw/Schema/Function/Formula/Canonical/Evidence/Final Metric。AI 未经验证不得覆盖确定性事实层。

## 21. 最终验收
源码映射完成；窗口与功能层级一致；跳转与窗口一致；参考资产已转成设计原则；所有外部输入统一 ingestion；Path A/B 均存在；Canonical 是唯一事实层；Visualization Adapter 独立；实时状态可见；Golden Dataset；10级 Gate；KOS/KOC/UGC；Note/Topic/Event/Risk；Evidence；Podcast 同 Shell/同数据/同 Evidence/同 AI；Podcast 独立 Workspace；Daily/Weekly/Monthly Vault；Research→Episode→Production→Publish→Review→Knowledge；内容模板；真实交互；无假数据；无重复计算；全部 Gate PASS 才能 DONE。

## 22. 外部学习
参考开源工程的通用方法而不复制实现：ECharts 的异步数据、动态更新、加载状态；shadcn/ui Drawer 的 Header/Content/Footer、嵌套、snap points、响应式 Dialog/Drawer 与滚动行为；数据表格按业务需求组合筛选、排序、分页、选择与可见性。citeturn2search1turn2search4turn2search5turn2search13
