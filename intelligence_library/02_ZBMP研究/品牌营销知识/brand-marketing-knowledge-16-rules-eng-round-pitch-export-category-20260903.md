# OSAI 第十六期 · 踩坑规则执行化 + 真实补丁工程回合 + 方案拆解Word导出 + 品类句库

日期：2026-09-03
定位：四项候选一次全部落地：①踩坑规则固化 agent system ②闭环升级到"智谱生成真实补丁→回归→推 ZBC" ③工作台接 pitch-analyze+导出 Word ④品类句库扩充。

---

## 一、踩坑规则执行化（rules.py 注入 agent system）
- 新增 `osai_engine/rules.py`：15 条高频踩坑 SOP（PowerShell 转义/git push 红字/模块缓存需重启/seed 可复现/pytest 轮询/glm-4.7 思考模型/JSON 归一化/数据不伪造/功能零减配/个人资料不线上等）。
- 注入 `agent._SYSTEM`（决策）与 `_PATCH_SYSTEM`（补丁生成），OSAI 执行时"生来就懂"这些规则。
- 测试 `test_rules_injected_into_system` 验证注入生效。

## 二、闭环升级：真实补丁工程回合（run_engineering_round）
- `agent.generate_patch()`：独立 `_PATCH_SYSTEM` 让智谱生成【新增自包含模块】（path/content/test_hint/desc JSON）。
- `orchestrator.run_engineering_round()`：完整流程 = 研究(可选联网)→智谱生成补丁→写入 ZBC scripts/→运行验证→全量回归→push ZBC→Evidence。
- 安全边界：仅允许 scripts/ 下新增文件、拒绝覆盖已有文件、验证失败清理文件、回归失败回滚、只推回归通过的工程。
- 过程中抓出并修复 2 个真实 bug：①回归轮询误用文件内容判 EXIT=（永不满足→超时误判）→ 改 `proc.poll()` 判退出码；②验证失败文件残留 ZBC 工作区 → 失败即清理。
- 需求-产出一致性弱校验：任务关键词命中 docstring 即一致；OSAI 允许自主评估"做什么更有价值"（本次自主生成仓库同步监控模块并成功交付）。
- **真实跑通**：智谱生成 `scripts/warehouse_sync_monitor.py`（Git 同步状态监控）→验证 exit=0→全量回归 exit=0→push ZBC `7082da2`→Evidence。
- 三大件更新：①自主联网研究 ✅ ②自主决策编排 ✅（已到"生成真实代码→回归→推生产"级）③踩坑规则执行化 ✅（本项）。

## 三、方案拆解 + Word 导出（工作台接 pitch-analyze）
- 后端 `scripts/pitch_export.py`：python-docx 把 analyze_pitch 结果导出为可交付 Word（需求要素表/对标基准/创意方向/方案脉络）。
- 后端新端点 `POST /api/creative/pitch-export`：text 或 multipart file → 返回 .docx 下载。
- 前端工作台新增第 4 Tab「方案拆解」：粘贴文本或上传文件（txt/md/json/csv）→ 拆解渲染；「导出 Word」按钮本地导出（个人资料仅本地，不上传）。
- 修复：PITCH_TOC 为 list[dict] 的导出兼容。
- 实测：文本方案→导出 39KB docx；现网端点返回 PK 头二进制 ✅。

## 四、品类句库扩充（研究驱动）
- 智谱 web_search 研究美妆疗愈/母婴/户外/酒类情感文案（克制比浓烈更治愈，拒绝宏大词）。
- 新增 4 个通用情感手法（_HOOK_EMO + _HOOK_EMO_LUX 高奢版 + MECH_TO_HOOK + _EMO_ROLE_COMPAT）：
  - `emo_sensory` 感官通感（触觉/气味/听觉具象）
  - `emo_self` 悦己和解（不必成为谁，更真实一点）
  - `emo_nature` 自然对白（自然元素×身体感知，自由留白）
  - `emo_grow` 共同生长（日常仪式、一起慢慢来）
- service 角色仍不配高语境/品类手法（写实收敛）。
- 测试：候选池 260 次采样覆盖 4 新手法 + 集成抽样出现品类手法；引擎 26 项测试全绿。

## 五、验收（真实证据）
- ZBC 全量回归 reg46：EXIT=0（详见日志）。
- 现网 8201：品类手法候选就绪、pitch-export 返回 docx、工作台 200。
- OSAI osai_engine 8 项自测全绿（含 rules 注入）。
- 工程回合 Evidence：智谱生成→验证→回归→push ZBC 7082da2。

## 六、下一轮候选
1. 一致性强校验+自动重试：需求偏离时自动纠正到完全匹配（当前 warn 级）。
2. 工程回合支持"修改现有文件的最小 diff"（当前仅新增文件，安全边界优先）。
3. 工作台增强：pitch-analyze 拆解结果一键导出 + 更多文件格式（pptx/docx 文本抽取）。
4. 更多品类/圈层符号扩充 + 创意引擎接入小程序端。
