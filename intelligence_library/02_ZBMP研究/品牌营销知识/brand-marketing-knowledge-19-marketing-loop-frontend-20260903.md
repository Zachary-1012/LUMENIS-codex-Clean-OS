# OSAI 第十九期 · 营销节点全链路前端闭环 + edit 极简 system 尝试（智谱生成不稳定的进一步证据）

日期：2026-09-03
定位：报告体系消费营销节点前端闭环完成；创意引擎显示绑定节点；垂直行业×节气交叉扩充完成；edit 工程回合智谱侧稳定性再次证实受限（如实记录）。

---

## 一、营销节点渲染进报告中心前端 ✅
- 新增 `app.py /api/v2/marketing/overview`（Basic 保护）：返回当月全部节点（节气/节日/营销节点）+ suggest_hotspot 当期绑定 + 垂直行业交叉建议。
- `static/index.html` 报告中心新增「本月营销节点速览」卡片（mkNodesBody），DOM ready 后拉取渲染。
- 实测：9 月节点 白露/教师节/秋分/中秋/丰收节，当期绑定白露+教师节，建议调性 premium；index 200。
- 芥子→须弥闭环：营销日历（抽象能力）→ 报告中心（用户可见层）→ 排期决策。

## 二、创意引擎显示当前绑定节点 ✅
- `idea_generator.generate_ideas` 返回 meta 新增 `bound_hotspot`（当前自动绑定的营销节点；luxury 显示"（未绑定节点）"——克制叙事）。
- 前端/调用方可直接展示"创意当前踩中的文化时机"。

## 三、垂直行业 × 节气交叉扩充 ✅
- `marketing_calendar.cross_industry_season(industry, month)`：行业节点 × 当月节气交叉建议，如「爱婴节遇白露：更轻松的妈妈、高质量带娃 × 清透、秋凉」。
- CLI `--cross 母婴`；overview 端点 `?industry=` 联动。
- 触类旁通：通用节点（节气）与垂直节点（行业）叠加出专属心智，而非单一来源。

## 四、edit 工程回合：极简 system 尝试（第 8-9 次智谱调用，仍然失败，如实）
- 依据诊断成功条件（极简 system + 无 rules 注入 + 极简 user + 无 ctx）复刻：`_PATCH_SYSTEM_EDIT` 去掉 rules 注入、user 只留任务、ctx 不再附带文件内容。
- 结果：智谱生成 `src/app.js`（前端）、纠正重试 `src/components/UserProfile.tsx`（React 组件）——又一次完全偏离任务指定文件，且换到了 JS/TS 域。
- 证据链：7 次尝试覆盖 库存审计(仓库) → 编造函数(get_campaigns/get_events) → 前端(React) 三个完全无关域。结论：**当前智谱 glm-4.7 端点对"编辑指定现有 Python 文件"的遵循性极不稳定，属模型侧限制，非 OSAI 机制问题**。
- OSAI edit 机制（路径白名单/唯一校验/备份/回滚/禁止词/锚点兜底/纠正重试）在全部 8 次尝试中每次都正确拦截，ZBC 零污染——fail-safe 已验证充分。
- 建议：不再对智谱 edit 消耗额度；edit 补丁生成后续改由 OSAI 本地确定性生成（对"新增独立函数"类任务，OSAI 可基于文件内容自写最小 diff），智谱只承担研究与决策。已登记下一轮候选。

## 五、验收
- 相关测试全绿（营销日历含交叉 8 项）；全量回归 reg50 见日志（EXIT=0 判定）。
- 现网 8201 已重启，overview 端点 + 报告中心卡片在线。

## 六、下一轮候选
1. edit 补丁 OSAI 本地生成 fallback（确定性最小 diff，替代不稳定智谱）。
2. 营销节点速览卡片增加行业下拉（industry 参数联动交叉建议）+ 接入日报弹窗。
3. 垂直行业×节气交叉扩充到 CLI 排序输出与报告 marketing_nodes 合并。
4. 更多垂直行业（电竞/宠物医疗/文旅大省）+ 海外节点（海外社媒/节日）扩充。
