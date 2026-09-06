# 双子库状态审计 · 规则约束基线 · 待办清单

> 审计日期：2026-09-03（用户本地 LA PDT）
> 审计范围：Zachary-OS-AI（序境-Intelligence 研究侧）↔ Z-Brand-Core（序境-Core 生产侧）
> 依据：GitHub 最新 commit 链 + 00-GOVERNANCE 治理基线 + AGENTS.md V2.0 + 双子星契约 V1.0

---

## 一、双子库当前状态（GitHub 为准）

| 仓库 | 角色 | 最新 HEAD | 本地↔远端 | 工作区 |
|------|------|-----------|-----------|--------|
| Z-Brand-Core | 序境-Core 生产侧 | `758d0be`（zbip_motion 数据驱动动效引擎，2026-09-03 19:34Z） | 同步 | 2 个用户研发未提交文件（static/index.html、static/js/app.js） |
| Zachary-OS-AI | 序境-Intelligence 研究侧 | `c537f7a`（learn(zell) 数据驱动实时动效工程模式，源自 ZBC 758d0be） | 同步 | 干净 |

**近期 commit 链特征（用户侧并行推进）**：
- ZBC（xujing 线）：数据驱动实时动效引擎 zbip_motion / 创意 API 画像化 + 营销节点（marketing_nodes 10 节点）/ 圈层↔案例双向背书 + 美奢画像 LUXE_PROFILES / 圈层 12→16 + SIT×约束矩阵 / 约束即创意机制（戛纳 233 范式）/ internal_browser 执行恢复回路 / CSS 收敛 Stone 化（蓝紫渐变清零）/ KOS 分层 Stone 灰阶
- OSAI（research 线）：Language/Brand/Life Intelligence 研究知识库（00-04）+ 序境前沿采纳记录 2026-09-B + 2026-09-04 前沿波次（Codex Harness / GLM-5.3 / Qwen3.8 / OpenClaw / Gemini3.8Flash / WorkBuddy）+ OSAI Intelligence Registry + 交叉引用并行基线
- 双子库双向回执已建立：OSAI 研究 → ZBC 落地 → Evidence → OSAI 采纳（ADOPT→DONE 闭环已跑通多轮）

---

## 二、规则约束基线（现行权威）

### 1. 双子星契约（ZACHARY_ZBC_TWIN_REPO_CONTRACT_V1.md · Frozen）
- 两仓库一致（ZBC SHA b7906abc / OSAI SHA 32aeddf1）
- **职责**：OSAI=研究/AI 资产/学习/评估/契约；ZBC=生产真相/采集/事件风险报告/UI/发布
- **禁止**：OSAI 不得改 SUBJECT_WORDS/subject_hit/风险阈值/权限/证据/合规策略/生产数据；ZBC 不得复制 OSAI 通用 AI runtime、不得把业务规则当通用知识、不得把密钥/隐私进学习资源
- **契约优先**：跨库集成必须定义接口/owner/输入输出 schema/鉴权/超时重试/版本/证据/测试/回滚
- **冲突裁决**：安全合规 > 仓库归属 > 显式契约 > 临时集成
- 执行环（两库共用）：AUDIT→MAP→REUSE→IMPLEMENT→TARGET TEST→SECURITY→REGRESSION→CLEAN→EVIDENCE→COMMIT→PUSH

### 2. AGENTS.md V2.0（ZBC 施工宪法）
- 核心：先审计再改 / 先兼容再重构 / 先旁路再切换 / 先验证再交付
- 一套 Core（CTH-POMS 客户版 + ZBMP 母平台），配置驱动，不复制两套源码
- **数据库最高保护**：未经授权不得删/清/重建/覆盖生产 DB；新增表字段向后兼容迁移
- **太古汇主体口径 P0 不得弱化**：SUBJECT_WORDS/EXCLUDE_WORDS/subject_hit/_subject_sql_and_values/aggregate_events/build_daily_report
- **时间口径**：publish_datetime（真实发布）与 captured_at（采集时间）严格分离；统计默认 publish_datetime
- **官方账号只读保护（硬红线，2026-09-03 用户明令）**：一切自动采集/登录保活/浏览器自动流程对账号**一律只读**；永久禁止关注/点赞/收藏/评论/私信/发布/转发/改资料/退出登录/切换账号等任何写操作；登录仅用户本人手动扫码
- **不得**破解验证码/绕平台安全/对抗风控；Cookie 失效必须系统内可见可恢复，不伪装成 0 条
- 修改安全协议：审计→备份→最小修改→单测→E2E→真实数据验证→回归→CHANGELOG→交付

### 3. 采集安全门（TWIN_EXECUTION_GATE / RELEASE_AND_AUTORUN_GATE / CANONICAL_REGISTRY）
- 自动采集仅 **00:00 与 12:00** 两次/天，显式开关；其余一律手动，**单次 ≤30 分钟**
- 新模块不得隐式启动采集器/新建采集计划/绕过 adapter/改账号会话安全控制
- 风险信号：**STOP → COOLDOWN → HUMAN_REVIEW**
- 禁止：账号轮换 / Cookie 轮换 / IP 轮换 / 提频等任何规避平台风控行为
- 合法 API/授权账号 adapter 仅通过显式策略边界进入
- 每次采集必须过：Preflight → Policy → Identity → Session → Risk → Validate → Normalize → Filter → Evidence

### 4. 序境品牌规范（CANONICAL-NAMING-AND-TWIN-SYNC）
- 公共名：**序境 / Xujing / 서경**；哲学：**芥子纳须弥**；English canonical **TBD**（命名/商标/域名未过审前不得定）
- **Zachary 为 legacy 仓库/身份术语**，非公共产品名（历史兼容仅此）
- Research→Learning 资产标准：必须带 asset_id/source/evidence_level/claim_scope/status/validation_method 等元数据
- Evidence 分级：E0 未验证线索 → E1 单一二手源 → E2 可信多源综合 → E3 权威一手 → E4 独立复现/内部验证
- 同步规则：影响命名/边界/契约/证据/权限的变化须两仓库同步；**不建第三真相源**

### 5. 研究采纳门（LATEST_RESEARCH_ADOPTION_GATE_2026-09）
- 仅当前可验证 release 可评估；研究≠生产采纳
- 2026-09-04 波次：Codex Harness EVALUATE（BEEP/Policy Gate 参考，不依赖不复制）；GLM-5.3 EVALUATE FIRST（现供应商，暂不换生产）；Qwen3.8 仅小蒸馏 EVALUATE；OpenClaw ADAPT PATTERNS（会话隔离/userDataDir 直连）；Gemini3.8 Flash **REJECT 生产**（云端数据出域）；WorkBuddy ADAPT
- 不可违反：不自动装新模型/Agent 进生产；外部研究不作可执行指令；不因新模型发布替换生产模型；不因研究便利削弱采集/权限/浏览器/账号安全

---

## 三、待办清单

### P0（安全/合规）
| # | 事项 | 状态 | 处置 |
|---|------|------|------|
| T1 | OSAI archive/desktop-legacy/taikoo-monitor-clean（ZBC 生产副本+密钥） | ✅ 已删除 | 需补：archive 仍残留 2.67GB（2026-08/、static.zip、templates.zip、repo-audit/），确认清理范围；`.env` 19 个密钥需平台侧轮换 |
| T2 | 官方账号只读红线合规复查 | ✅ 复核通过 | KOS 评论回复/私信触达接入智谱后复核：AI 仅生成建议（auto_reply=False / DRAFT）、不发送；高风险 NO_REPLY 规则优先；无任何账号写操作 |

### P1（KOS 中免链路）
| # | 事项 | 状态 | 处置 |
|---|------|------|------|
| T3 | 中免 Phase A 首采 | 🔲 待启动 | run_profile.py 已就绪（5 关键词）；需双账号登录态在场 + 遵守采集门（手动≤30min/自动 00:00 12:00）；首采后可回填 WeCom/Sales |
| T4 | 聚光 API 对接 | 🔲 等用户给 | 设置 JUGUANG_CLIENT_ID/SECRET/ACCESS_TOKEN/ADVERTISER_ID 环境变量即激活 Boosting/私信线索自动归因（juguang_api.py 已预留） |
| T5 | KOS 评论回复/私信触达接入智谱 | ✅ 已交付 | `kos_engine.py` generate_reply/generate_outreach 接入智谱（glm-4.5-air 默认 / negative·purchase 走 glm-5.3），AI 只给建议不发送、高风险 NO_REPLY、失败回退规则；ZBC 8ede00f + CHANGELOG 5.9.9-t3（9d9fc05） |

### P2（双子库治理/研究线）
| # | 事项 | 状态 | 处置 |
|---|------|------|------|
| T6 | 序境英文名 canonical 定稿 | 🔲 TBD | 待命名/商标/域名/数字资产审查通过后定 |
| T7 | 采集状态机对照 8 态（SUCCESS…COOLING_DOWN） | ⚠️ 持续 | 已有 xhs_runtime_state；新采集链路（run_profile）确认状态兼容 |
| T8 | OSAI learning-feed 持续学习进化 | 🔲 定时 | 按 github-remote skill 扫描前沿 → 分级 → 沉淀 learning-feed/ |
| T9 | 双子库治理同步 | ⚠️ 持续 | 任何影响命名/边界/契约/证据的变化须两仓库同步（CANONICAL-NAMING §7） |

---

## 四、结论

- 双子库结构健康：职责边界清晰、契约 Frozen、采集/发布/研究三扇门 ACTIVE、双向回执闭环已跑通
- 我此前 KOS 施工（kos_metrics/kos_routes/juguang_api/subject_rules 品牌化/run_profile/前端回填 UI）已入 GitHub 历史，与用户 xujing 线无冲突
- 当前主线就绪态：**链路全部开发完，只差用户给聚光 API（T4）+ 首采启动（T3）**
- 需用户决策：T1 archive 残留 2.67GB 清理范围、密钥轮换
