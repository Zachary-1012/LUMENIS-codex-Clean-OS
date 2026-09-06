# OSAI 第十八期 · 营销节点全链路消费 + edit 工程回合机制就绪（智谱生成质量阻塞如实记录）

日期：2026-09-03
定位：四项推进落地三项 + 一项机制就绪、真实跑通受智谱侧阻塞（如实登记，不虚报）。

---

## 一、营销日历接入创意引擎 hotspot 自动增强 ✅
- `idea_generator.generate_ideas`：signals 未显式指定 hotspot 时，自动调用 `marketing_calendar.suggest_hotspot(今天, category)` 绑定当月营销节点。
- 验证：未传 hotspot 时输出自动绑定「白露」（9 月当前节气），timeliness 变为"绑定热点「白露」，踩准文化时机"。芥子→须弥时效自动增强闭环打通。

## 二、报告体系消费营销节点 ✅
- `report_engine.generate_report`：所有报告类型（日报/周报/月报/年报/专报）返回新增 `marketing_nodes` 字段（当月节点名/情感主题/建议调性）。
- 验证：9-20 日报带出 白露/教师节 + 中秋主题 + premium 建议。

## 三、垂直行业节点扩充 ✅
- `marketing_calendar._V_NODES` + `industry_nodes(industry, month)`：7 大垂直行业 16 个专属节点（母婴/美妆/酒饮/文旅/教育/宠物/咖啡茶饮），各带情感主题与品类；CLI `--industry` 可查。
- 测试：`test_vertical_industry_nodes` 覆盖行业/按月/别名匹配。

## 四、工程回合 edit 模式：机制 100% 就绪，真实跑通被智谱生成质量阻塞（如实）
### 已就绪并真实触发验证的机制（每层都在多次运行中正确工作）：
1. `generate_patch(mode="edit")` + 独立 `_PATCH_SYSTEM_EDIT`（只讲 edit 格式、钉死"修改任务指定现有文件、禁止新建文件、禁止仓库/库存/拣货/货位/供应链/审计日志类"）。
2. `run_engineering_round(mode="edit")` 完整闭环：路径白名单(scripts/tests) → old_snippet 唯一校验 → 应用前备份 .bak → py_compile 验证 → 失败回滚 .bak → 全量回归 → 回归失败回滚 → push。
3. **禁止词拦截**：内容/描述命中 inventory/warehouse/库存/仓库/拣货/货位/stock/supply/logistics 直接拒绝并纠正重试。
4. **锚点插入兜底**：智谱给出独立函数 content 且文件含 `def main():` 时，OSAI 定位插入 main() 前。
5. **纠正重试**：edit 首次失败 → 追加一次强调"禁止新文件/禁止仓库类"的纠正生成。
6. **失败安全**：5 次尝试全部正确拒绝无效补丁，ZBC 工作区零污染、未改任何文件、未伪造数据。
### 阻塞点（模型侧，非机制）：
- 智谱 glm-4.7 对"修改现有文件/新增函数"类任务反复跑偏与幻觉：
  - 第 1-2 次：生成 inventory_manager/warehouse_manager（库存/仓库新文件）；
  - 第 3 次：inventory update_stock（被禁止词拦截）；
  - 第 4 次：给不存在的 get_campaigns 加 placeholder campaign data（编造函数+伪数据）；
  - 第 5 次：给不存在的 get_events 加 sample event（编造函数+伪数据）。
- 诊断对照：用最简 system+最简 user 直接 llm.chat，智谱能正确输出 old_snippet="def main():" 的 edit JSON；但经 generate_patch（注入规则/上下文）后不稳定。怀疑与长 system 注入/上下文相关，需后续专项调优。
- 结论：机制可安全落地（fail-safe 已验证）；"智谱真实生成 edit 补丁→闭环"待智谱侧改善（换模型/精简注入/或换任务类型）后重试，已登记下一轮候选。

## 五、验收
- ZBC 新增测试全绿（营销日历含垂直 8 项 + 引擎类全部 + 报告不含回归）；全量回归 reg48 见日志（EXIT=0 判定）。
- OSAI osai_engine 测试 8 项全绿；edit 防御 5 次真实触发零污染。
- 双库推送 commit 见 git log。

## 六、下一轮候选
1. edit 工程回合真实跑通：换更简任务/精简 rules 注入/尝试 temperature 降低后重试，或登记为模型能力待提升项。
2. 营销日历接报告前端展示（marketing_nodes 渲染到日报弹窗）。
3. 更多垂直行业节点（文旅大省/电竞/宠物医疗等）+ 行业×节气交叉。
4. 创意引擎 hotspot 自动增强补 UI 展示（显示"当前绑定节点"）。
