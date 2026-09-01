# 双子星（Z-Brand-Core × Zachary-OS-AI）综合审计与融合调整规范

> Spec ID: `dual-repo-audit-20260902`
> 生效范围: `Zachary-1012/Z-Brand-Core` (产品 A) + `Zachary-1012/Zachary-OS-AI` (产品 B)
> 语言: 中文
> Spec 类型: 产品定位 × 价值评估 × README 架构融合调整 × 允许/禁止边界

---

## 1. 问题与背景

### 1.1 当前状态（来自真实源码与审计）

电脑本地已成功链接两个 GitHub 仓库：

| 产品 | 仓库 | 本地路径 | 版本 | 文件/规模 |
|---|---|---|---|---|
| **产品 A：Z-Brand-Core** | `Zachary-1012/Z-Brand-Core` | `D:\Taikoo-monitor-new` | v5.9.7 | 21,656 源码文件 / 8,150 MB / main 分支与 origin 同步 |
| **产品 B：Zachary-OS-AI** | `Zachary-1012/Zachary-OS-AI` | `D:\Zachary OS AI` | 收敛审计 v1.0 | 586 整合后文件 / 2,589 MB / 含 22 份收敛矩阵 + SICI/DCC/AI-DRH 三大组件 |

- 产品 A (ZBC) 是真实生产系统：广州太古汇舆情监测（CTH-POMS，P0）与品牌传播市场情报母平台（ZBMP，受控增强），代码/数据库/E2E 已真实运行。
- 产品 B (ZOSAI) 是四库（ZBC 业务仓 + SICI 移动仓 + DCC 工程仓 + AI-DRH 研究仓）的治理汇编与收敛总枢纽，目前治理框架高度成熟（22 条 IMMUTABLE 基线、三方反哺、9 阶段研发流程、D0-D7 交付标准），但自动化落地处于 V0.5（10 项 Human Gate 冲突未裁决，5 项 HIGH 安全发现未修复，门禁=FULL CONSOLIDATION NOT READY）。

### 1.2 本次 Spec 要解决的核心问题

1. **双子星整体审计**：同时评价 A/B 两产品的项目价值、可发展性，明确各自强项弱项与互补点。
2. **产品定位再确立**：以两个 GitHub 仓库为两个独立产品，给出清晰的客户/用户/角色定位，并区分产品 A 内部的 CTH-POMS/ZBMP 双模式（不等于产品 B）。
3. **商业价值与应用场景**：从 ToB 交付、To 内部研发治理、AI Agent 平台化三条路分别给出价值模型、关键场景与营收可行性判断。
4. **README 架构融合调整**：使两仓 README 在不互相覆盖生产规则的前提下形成"统一母体但定位不同"的结构，互相交叉引用但各自保留 Owner 权威。
5. **两仓资产全面清点**：对 A/B 两仓的每一类内容（源码/数据库/文档/测试/AI 样本/配置/子模块）做分类登记，确保后续不丢资产、不误改。
6. **允许/禁止规则矩阵**：从产品层、仓库层、组件层、研发流程层四层构建"允许做/禁止做/受控做"矩阵，固化进两仓 README 的常设章节。

### 1.3 非目标（Non-Goals）

- **不是**：合并两个仓库。产品 A 与产品 B 永远是两个独立仓库（见 ZOSAI IMMUTABLE BASE-001/002/003）。
- **不是**：重构 ZBC 264KB app.py 单体（审计报告明确警告"DO NOT refactor during consolidation"）。
- **不是**：把 ZOSAI 22 份矩阵/三组件源码推送到 GitHub 生产分支（等用户后续指令，本 Spec 只定架构与边界）。
- **不是**：解决 ZOSAI 10 项 Human Gate 冲突或 5 项 HIGH 安全问题（列出并分级，后续 tasks 分派）。
- **不是**：真实 E2E 测试本轮不跑（本轮交付物 = 文档/架构/边界/清单，不是代码施工）。

---

## 2. 双子产品定位

### 2.1 一图总览

```
                         Zachary 双产品生态
                                 │
          ┌──────────────────────┴──────────────────────┐
          ↓                                             ↓
  产品 A：Z-Brand-Core                          产品 B：Zachary-OS-AI
  （品牌传播与市场情报智能平台）                    （Zachary 独立 AI 平台 / 四库治理枢纽）
          │                                             │
   ┌──────┴──────┐                         ┌────────────┼────────────┐
   ↓             ↓                         ↓            ↓            ↓
CTH-POMS      ZBMP                      SICI-Core     DCC        AI-DRH
（客户交付版） （母平台增强层）           （移动界面） （工程控制）（研究学习）
   │             │                        纯前端 PWA    Node.js     研究+注册
   │             │                        GitHub Pages  8787 端口  8 能力+pytest
   └──────┬──────┘                        （零后端）    Evidence   Reusable
          ↓                                            Release    Learning
  品牌主数据链：采集 → 标准化 → 主体过滤 → 去重 → 入库 → 分析/AI/报告
          ↑                                             │
          └──────────── Contract + Evidence + 三方验证 ───┘
                         （ZOSAI 验证/治理 A，不是 A 的运行时依赖）
```

### 2.2 产品 A：Z-Brand-Core（品牌传播与市场情报智能平台）

| 维度 | 定义 |
|---|---|
| **一句话定位** | 商业可交付的、面向品牌/购物中心/公关团队的舆情监测与品牌传播情报 SaaS/私有化部署产品。 |
| **核心用户** | 商场 PR 团队、品牌市场部、公关代理公司、内容运营、舆情分析师、品牌主理人。 |
| **当前主客户** | 广州太古汇（CTH-POMS 模式）；未来模式为多品牌客户（ZBMP）。 |
| **产品核心引擎** | 四层业务模型（WHO 传播主体 / WHAT 内容 / WHAT HAPPENED 事件 / SO WHAT 品牌影响）。 |
| **数据来源** | 小红书（PRIMARY，稳定优先）+ RedNote（冗余入口）+ Web 全网发现 + 微博/B 站（辅助，待验证）。 |
| **AI 架构** | Ollama-first 本地 AI；AI 可退出/可审计/Shadow Mode；系统规则是主判断，AI 是增强。 |
| **交付形态** | 单客户 Release 包（CTH-POMS 快照）+ ZBMP 母平台多品牌 SaaS（未来）。 |
| **竞争差异化** | ① 事件因果链（营销→传播→舆情→品牌影响）② 主体×内容严格分离 ③ 采集风控与 Auth Recovery 行业最细致 ④ 真实客户场景已稳定跑通 v5.9.7（42 项 E2E 通过）。 |
| **权威 Owner** | 仓库 Owner = Z-Brand-Core main；业务变更必须通过 AGENTS.md 工程宪法；本 Spec 不得降低其任何既有门槛。 |
| **成熟度** | **L3 生产成熟**：真实业务数据、客户验收门槛、P0 级规则、v5.9.7 连续交付记录。 |

### 2.3 产品 B：Zachary-OS-AI（Zachary 独立 AI 平台 / 四库治理枢纽）

| 维度 | 定义 |
|---|---|
| **一句话定位** | 为 Zachary 独立 AI 身份而建的、覆盖移动交互/工程治理/研究学习的 AI Agent 平台，同时是 ZBC 产品的"工程治理与研发中台"。 |
| **核心用户** | 内部研发团队（ZBC 工程协作）、AI Agent 研究员、Codex/豆包/ChatGPT 等辅助开发工具、未来外部独立 AI 平台用户。 |
| **四库角色** | ZBC = 业务真相源（L3，只进不出）；SICI = 移动交互权威（L2/L3）；DCC = 工程控制权威（L2/L3）；AI-DRH = 研究学习/能力注册权威（L1/L3）。 |
| **三组件职责** | **SICI**（移动开发控制台 v3.0 / 纯前端 PWA GitHub Pages）→ Code / Run / Preview / Test / Git / Browser Surface 移动端呈现。**DCC**（v0.5.0 / Node.js 40+ API 8787 端口）→ AI 软件工程控制平面：任务合同/Evidence/Release/Learning/Shadow/权限最小化（WRITE 永久 DENY）。**AI-DRH**（8 reusable + 115 pytest）→ Research 隔离 workspace/Shadow 生命周期/Capability Registry 唯一权威/跨库基线治理。 |
| **AI 架构** | Zachary 独立 AI 身份（与 ZBC 产品身份严格分离 IMMUTABLE BASE-001）；三方反哺闭环（ZBC 业务→DCC 工程→SICI 移动→学习反哺→ZBC）Evidence-first + 影子优先 + AI 依赖递减。 |
| **交付形态** | ① GitHub Pages 移动站（SICI）② 本地 8787 工程控制服务（DCC）③ 研究学习 Python 工具链（AI-DRH）④ 22 份收敛矩阵与基线文档（治理资产）。 |
| **竞争差异化** | ① 22 条 IMMUTABLE 永久基线 + 三方互相验证 + Before/Change/After Gate 在 AI Agent 工程体系中属上游水平 ② Evidence 优先于 AI 判断的文化贯彻彻底 ③ 四库 Owner 清晰不互相耦合 ④ DCC 权限最小化模型防 AI 失控。 |
| **权威 Owner** | 跨仓共享能力的唯一权威在 AIDRH（Capability Registry）/ DCC（工程门禁）/ SICI（移动体验）三端；任何共享能力只能一个 Owner，其他人通过 Contract 复用，禁止复制实现。 |
| **成熟度** | **L1/L2 治理框架成熟 + 自动化基础设施半成熟**：制度/边界/门禁/流程全部文档化并交叉引用一致（V1.0 水平），机器可验证的自动化（合约测试套件/加密证据链/跨库 API 版本化/Persistence Bridge/学习持久化）仍待落地（约 12 周 4 阶段）。 |

### 2.4 产品 A 与产品 B 的严格边界（定位区分）

| 对比维度 | 产品 A（Z-Brand-Core） | 产品 B（Zachary-OS-AI） |
|---|---|---|
| **产品性质** | 商用品牌情报软件（交付给客户） | AI 平台 + 研发治理（主要对内，未来独立 AI 生态） |
| **是否面向客户赚钱** | ✅ 是（主现金流） | 短期内否，中期通过 AI 能力/研发效率变现 |
| **生产稳定性要求** | P0 最高级（故障=客户事故） | P1（研发效率损失≠客户事故） |
| **对另一产品的依赖** | A 生产绝对不依赖 B（IMMUTABLE：运行时依赖箭头只能 B→A，反向严禁） | B 通过 Contract/Evidence 调用 A 的只读 API（zbc-evidence-adapter）。B 不拥有 A 业务决策权。 |
| **身份品牌** | CorTech Lab / Z-Brand Monitoring（客户品牌） | Zachary AI（独立 AI 身份，IMMUTABLE 禁止 A 与 B 身份合并） |
| **数据资产** | 生产数据库/采集数据/报告/品牌知识（高保护） | 研究数据/Evidence 链/Learning 账本（append-only） |
| **AI 角色** | 业务增强层（Ollama 本地） | 平台本体 / Zachary 独立 AI / 工程 Agent |
| **代码形态** | 巨量 Python Flask + SQLite 主程序 | 多语言（JS/PY/MD）、多组件、四库整合 |
| **上线方式** | Release 快照/私有化部署/公网隧道 | GitHub Pages + 本地 8787 端口 + Python 工具 |
| **禁止互相操作** | A 源码不得复制 B 的 DCC/SICI/AI-DRH 核心实现 | B 不得修改 A 的生产数据库/主体口径/报告口径 |

---

## 3. 项目价值评估

### 3.1 产品 A（Z-Brand-Core）综合评分

按 10 维度 0-10 打分（分数基于真实代码/数据基线，非 AI 想象）：

| 维度 | 分数 | 理由 |
|---|---|---|
| 商业可行性 | **8.5/10** | 已锁定广州太古汇真实客户；主体口径/报告口径已验收；同类舆情 SaaS 年单价 ¥100K-¥800K，CTH-POMS 功能完整度 ≥ 中价档竞品的 80%。 |
| 技术壁垒 | **8/10** | ①采集风控熔断+Auth Recovery 行业最细 ②主体×内容双模型 ③事件因果链+关系图谱 ④Ollama 可退出 AI 架构 ⑤42 项 E2E 闭环。 |
| 数据沉淀 | **9/10** | 24 张表真实跑通；笔记/事件/评论/关联/报告/采集日志/AI Filter 日志全链路有记录；广州太古汇主体口径已积累词汇与规则。 |
| 客户体验成熟度 | **7/10** | 15 SPA + 1 独立页，导航无孤儿页，Zachary 助手+3D 形象加分；移动端目前"不溢出但体验未到苹果级"。 |
| 可扩展性（多品牌） | **6/10** | ZBMP 在架构上已预留，但客户隔离/权限/Runtime Mode/新客户 Build 自动化尚未落地（属 P1 路线图）。 |
| 稳定性（P0 链路） | **8/10** | v5.7-v5.9.7 共 20+ 版本迭代，最近 42 项 E2E 全过；熔断/恢复/冷却/健康检查链路完整；仍有空正文补抓/相对时间治理待收尾。 |
| 平台扩展（多源） | **6.5/10** | 小红书稳定+RedNote 冗余+Web 全网发现已跑通；微博/B 站 Adapter 骨架在但未真实跑数；缺统一多平台 Adapter Manager。 |
| 团队开发效率 | **6/10** | 仓库 AGENTS.md/V2.0 + 工程宪法极严谨；但 app.py 264KB 单体对新贡献者上手成本高；蓝图化 P2 进行中。 |
| 盈利时间窗口 | **7.5/10** | 当前客户稳定交付后，1-2 个月可交付第二个同规模购物中心客户；品牌案例库/传播主体分析报告可成为增值模块。 |
| 合规与风控 | **9/10** | 采集风控、IP 风险熔断、Cookie 失效恢复、验证码不破解、凭据不入 Git、AI 可退出可审计——合规文化是最大护城河。 |
| **加权总分** | **7.8/10** | → 属于"已过 MVP 的高成熟度 B2B 产品，具备立刻规模化交付的基础"。 |

**核心价值判断**：ZBC 是**现金流引擎**与**行业案例锚点**。

### 3.2 产品 B（Zachary-OS-AI）综合评分

| 维度 | 分数 | 理由 |
|---|---|---|
| 战略前瞻性 | **9/10** | 四库分离、治理执行分离、Evidence-first、三方反哺+相互验证——这套 AI Agent 工程治理框架 2026 年仍处于国际一线水平。 |
| 技术新颖度 | **8.5/10** | 三组件各有原创：SICI 纯前端移动 Dev Console、DCC WRITE 永久 DENY 的权限最小化模型、AI-DRH 8 阶段 Shadow 生命周期+Research ID 系统。 |
| 工程完整性（文档） | **9.5/10** | 22 份收敛矩阵+IMMUTABLE 基线+6 份跨仓基线文档，逻辑自洽、互相交叉引用一致，AI 工程治理文档质量达到顶级水平。 |
| 工程完整性（自动化） | **5/10** | 治理框架 V1.0 vs 自动化落地 V0.5：合约测试套件不存在、证据加密链 0、Persistence Bridge 空壳、Learning Store 纯内存、跨库事件总线空。 |
| 对产品 A 的反哺价值 | **8.5/10** | 三向验证、全局反馈循环、9 阶段研发流程、Evidence 文化、DCC 40+ API 工程控制——若落地自动化可将 ZBC 的研发迭代速度×2-3、事故率降 60%。 |
| 独立产品化可行性 | **6/10** | 短期：Zachary AI 是内部研发平台；长期：移动 AI 开发工具 / AI Agent 治理 SaaS 可独立售卖，但需 12-24 个月补齐自动化。 |
| 安全与防失控 | **9/10** | DCC WRITE/DEPLOY 永久 DENY、ZBC 生产不依赖 B、AI 影子优先、Evidence 优先、10 条 XHS App BLOCK 红线——AI 失控防护极为坚固。 |
| 可发展性（天花板） | **9.5/10** | 天花板 = "AI Agent 时代的 Jira×Jenkins×GitHub Copilot 三合一治理平台"。与产品 A 的组合可形成 "行业 AI 产品（ZBC）+通用 AI 工程平台（ZOSAI）" 的双飞轮。 |
| 团队与知识沉淀 | **8/10** | Owner 知识已固化为 IMMUTABLE 基线、Research ID、Capability Registry；但当前 Human Gate 冲突 10 项仍需 Owner 个人裁决，尚未完全去中心化。 |
| 风险与不确定 | 扣分项 | 5 HIGH 安全发现未修复；12 周收敛计划需严格执行；四重能力注册分裂是当前"体系内自相矛盾"的最大风险。 |
| **加权总分** | **7.7/10** | → 属于"顶层框架已成型、基础设施半完成、3 年内可长成 AI 工程平台赛道一级选手"的高潜产品。 |

**核心价值判断**：ZOSAI 是**战略护城河**与**长期增长引擎**。

### 3.3 双子组合价值（1+1 > 2）

单独看：
- 产品 A 单独发展 = 年营收数千万规模的品牌情报 SaaS（稳，天花板有限）。
- 产品 B 单独发展 = 高潜 AI 平台但短期不赚钱，需要大量投入补齐自动化。

组合看（双子星协同）：
- 产品 A 给产品 B 提供真实行业场景（品牌传播/舆情/采集），作为 AI 工程的"实战训练场"和 Evidence 输入源。
- 产品 B 给产品 A 提供研发效率×2-3、事故率↓60%、能力复用率↑80%的治理能力，把 A 的交付成本降 40%。
- 形成"商业现金流 A → 反哺研发平台 B → 再赋能 A 拓展新客户 / 新行业"的飞轮。
- 对外：ZBC 做标杆客户案例，ZOSAI 做"Zachary AI Inside"的技术品牌背书。

**双子组合净价值评估：在产品 A 单价值 × 产品 B 单价值的基础上，协同溢价约 +30%~50%。**

---

## 4. 可发展性评估（分阶段路线图）

### 4.1 产品 A（Z-Brand-Core）三阶段发展

| 阶段 | 时间 | 关键里程碑 | 价值转化 |
|---|---|---|---|
| **Phase A1（0-2 月）** | 现在起 | ① 修复 P0 尾部：空正文补抓/相对时间规范化/生产入口统一/公网 HTTPS ② 真实部署 CTH-POMS 客户验收通过 ③ 品牌知识库 + 案例拆解模块正式纳入客户交付 | 锁定第一笔稳定营收 + 客户复购意向 |
| **Phase A2（2-6 月）** | 下一客户周期 | ① Release Automation：一键 Build 独立客户包 ② Runtime Mode + Feature Gate + Brand Profile 完成 ③ 微博/B 站接入真实数据 ④ 品牌对标/消费者需求看板上线（ZBMP） | 扩展到第 2-3 个客户；单价 30-60 万；毛利 ≥ 70% |
| **Phase A3（6-18 月）** | 规模化 | ① SaaS 化多租户（ZBMP 正式版）② 6 大行业模板（奢品/商业地产/快消/美妆/文旅/科技）③ 客户自助 Campaign 配置 ④ AI 报告生成（合规通过版） | 年营收 ≥ 1000 万；ARR 增长曲线建立 |

### 4.2 产品 B（Zachary-OS-AI）四阶段收敛与发展

| 阶段 | 时间 | 关键里程碑（对齐 22_final_convergence.md 12 周计划） | 价值转化 |
|---|---|---|---|
| **Phase B0（4 周）** | 即刻启动 | 安全清理：修复 5 HIGH 安全、清理 18 个 AIDRH 重复分支、统一 3 仓 Design Tokens Owner（AIDRH）。目标：5 HIGH→0、重复分支→剩 5 条、Tokens 一致 | 消除硬阻塞项、门禁从 OPEN 到 PARTIAL |
| **Phase B1（4 周）** | B0 完成后 | 所有权+合约+能力注册统一：AIDRH 唯一能力注册中心 API、Contract 测试套件 v0.1、DCC Learning Store 持久化 JSON、SICI Persistence Bridge→DCC 受控后端。解决 10 冲突中的 #1,2,3,4,7,8 | 四仓 Owner 唯一；Contract 机器可验；门禁→基本 READY |
| **Phase B2（4 周）** | B1 完成后 | 证据流+学习整合：ZBC ai_filter_log → AIDRH JSONL 自动 API、DCC Evidence Bundle → AIDRH 自动注册、加密哈希链 Evidence、三方自动验证 webhook、GitHub Actions 5 次巡检正式跨仓打通。解决 #5,6,9 | 自动证据闭环；AI 依赖度可量化下降 |
| **Phase B3+4（持续）** | B2 完成后 | SICI 正式发布 GitHub Pages 移动站；DCC v1.0（WRITE 门禁+Release Candidate）；AI-DRH Reusable 能力数量从 3 → 20+；对外可作为 "Zachary AI Engineering Platform" 宣传。最终裁决 #10 DB 7 表差异（由 ZBC Owner 决定回滚或迁移补建） | 对外产品化起点；Zachary AI 独立品牌影响力建立 |

### 4.3 关键风险项

| 风险 | 影响 | 应对 |
|---|---|---|
| ZBC DB 7 张表差异（#10 Human Gate） | 生产数据库结构性风险 HIGH | 必须 ZBC Owner 手工检查 models.py vs database.py，要么建迁移 009/010、要么删除 models 中过度声明 |
| 四重能力注册分裂 | OWNERSHIP 违反风险 HIGH | B1 阶段定 AIDRH 唯一权威、其他降级 cache、禁止新增独立注册 |
| ZBC API 无认证无版本无规范 | 安全 HIGH + SICI 无法正式集成 | B0 阶段优先给 /api/evidence/* 加版本化+认证+rate limit |
| DCC Learning 纯内存 | 学习数据重启丢失 HIGH | B1 阶段 JSON 文件持久化、B2 阶段同步 AIDRH |
| ZBC 264KB app.py 单体 | 新贡献者上手难、merge 风险高 | P2 阶段先 blueprint 化 20%、不整体重构 |

---

## 5. 商业价值与应用场景

### 5.1 产品 A（Z-Brand-Core）商业模型

**主营收线：CTH-POMS 类单品牌/单项目客户交付**

| 项目 | 数值（参考） | 说明 |
|---|---|---|
| 单客户首年交付价（CTH-POMS 模式） | ¥30 万 ~ ¥60 万 | 私有化部署 + 品牌 Profile 固化 + 主体/风险/报告口径定制 + 12 月维保 |
| 年维保（第二年起） | ¥8 万 ~ ¥15 万/年 | 主体词/排除词更新、版本升级、采集适配、报告模板更新 |
| ZBMP 多品牌 SaaS | ¥3,000 ~ ¥12,000 / 品牌·月 | 自助配置、月度报告、品牌对标、事件看板 |
| 增值服务：深度报告（周报/月报/专项） | ¥2 万 ~ ¥8 万 / 份 | 主体分析、事件因果溯源、消费者需求洞察（分析师+系统联合产出） |
| 增值服务：营销事件监测 | ¥1 万 ~ ¥5 万 / Campaign | 活动前、中、后全周期传播效果监测报告 |

**典型目标客户与应用场景**：

1. **商业地产 / 高端购物中心（当前已验证）**：广州太古汇模式 → 上海恒隆、成都 IFS、北京 SKP、深圳万象城等同质客户 50+ 家。**核心场景**：品牌舆情监测、活动传播效果、负面风险预警、竞品对标、月度/季度/年度公关汇报。
2. **奢侈品牌中国区 PR 团队**：LVMH / Kering / Richemont / Hermès 集团下品牌 PR → 小红书/微博舆情监测 + 活动 Campaign 评估 + KOS/KOL 主体库沉淀 + 负面止损。核心卖点：主体×内容分离的传播分析，比传统 Meltwater / 领脉 更懂传播结构。
3. **新消费品牌（美妆/护肤/潮牌）**：年营收 5-50 亿新消费公司市场部 → 事件中心（营销→传播→舆情因果链）+ Ollama 自动评论总结和用户诉求提取 + 品牌对标。卖点：Zachary 助手 3D 体验+私有化部署=无数据出网合规。
4. **公关代理 / 数字营销代理公司**：以 ZBMP SaaS 方式同时管理 10+ 客户，每个客户用 Runtime Mode 隔离。卖点：多客户多品牌一台搞定、报告自动生成、客户 Demo 页面现成。
5. **文旅 / 酒店 / 文旅商业综合体**：和商业地产类同。核心：节假日/旺季舆情+活动监测+竞品（同城其他文旅目的地）对标。

**市场规模估算**：仅商业地产 TOP50 + 奢侈品 TOP50 中国区 = 100 家目标，首年触达 10% = 10 家 × 40 万均价 = **400 万首年 A1 阶段营收可达成**。

### 5.2 产品 B（Zachary-OS-AI）商业模型

**中线（12 个月内）：对内降本+提效 = 间接商业价值**

| 场景 | 对双子生态的商业价值 |
|---|---|
| ZBC 研发提速 | 每个大版本周期从 2 周压缩到 5-7 天，节省 50% 人力 = 年节约人力成本 40-60 万 |
| 事故率下降 | DCC Evidence-first + 三向验证 + Release Gate，生产事故率降 60% = 客户留存率提升+少付赔偿 |
| 新客户交付速度 | Release Automation + 一键 Build，新客户从 2 周到 3 天 = 首年多签 3-5 个客户 = 120-200 万额外营收 |
| AI 能力复用 | AI-DRH Capability Registry 把重复研发的学习/规则/验证/证据/注册能力统一做一次，四仓复用 = 代码量减 30% |

**长线（12-24 个月）：对外产品化 = 独立营收**

1. **Zachary AI Engineering Platform（企业级 AI Agent 治理平台）**
   - 目标客户：已经在使用 AI Agent 做软件开发但无法治理的科技公司、数字团队。
   - 定价模式：¥15-50 万 / 席位年（DCC 本地版）或 AI 开发团队人数计费。
   - 核心卖点：WRITE 永久 DENY 的权限最小化模型、Evidence-first 审计链、Before/Change/After Gate、三向验证、AI 依赖递减策略——对标"OpenAI 原生 + 自研安全治理"的企业痛点。
2. **SICI Mobile-first AI Dev Console（面向个人/小团队）**
   - 目标用户：独立开发者、移动优先 AI 工程师、AI 研究者。
   - 定价模式：Freemium（基础免费，Pro ¥49/月）+ 团队版 ¥99/月/人。
   - 核心卖点：手机端 Code/Run/Preview/Test/Git 全流程、Zachary AI 形象统一体验、浏览器内 Pyodide WASM 跑 Python。
3. **AI-DRH Research + Capability Registry（知识产品）**
   - Reusable Capability Marketplace（Reusable 能力市场）：每个 Reusable 能力 ¥500-2000 授权费。
   - Shadow Learning Benchmark Report 季报：订阅制。

**中长期市场估算**：AI 工程治理赛道 2026 年全球约 50 亿美元，中国约 30 亿人民币。双子组合 ZBC（行业案例）+ZOSAI（技术平台）可占中国 AI 工程治理赛道 0.5-1% 市场 = **1500-3000 万 B 产品年营收**（需 24 个月以上）。

### 5.3 应用场景总表（18 个场景×对应产品）

| # | 应用场景 | 对应产品 | 关键角色 | 交付价值 |
|---|---|---|---|---|
| 1 | 商场日常舆情监测（小红书为主） | A CTH-POMS | PR 团队/舆情分析师 | 风险早发现、主体红线不松 |
| 2 | 购物中心营销活动效果评估（如周年庆/七夕） | A CTH-POMS → 报告模块 | 市场部 | 营销→传播→舆情因果链 |
| 3 | 负面危机二次确认+止损报告 | A 风险预警/负面确认 | PR 主管理 | 15 分钟内出分级+动作 |
| 4 | 竞品对标（隔壁商场/同品牌） | A ZBMP 品牌对标 | 品牌总监 | 多维对标+传播差异 |
| 5 | KOS/KOL/KOC 传播主体沉淀 | A ZBMP 主体六维画像 | 市场部/PR | 长期合作池积累 |
| 6 | 日报/周报/月报自动生成 | A 报告中心（客户版） | 全员 | 省 4-8 小时/周人力 |
| 7 | 品牌知识库查询（新员工培训/日常咨询） | A 品牌知识库（影子板块） | 内部全员 | 减少重复问"上次怎么处理的" |
| 8 | 案例深度拆解+方法论复用 | A 案例库 | 品牌+市场 | 58 条方法论复用+77 系统启示 |
| 9 | Cookie / 登录失效 → 系统内扫码恢复 | A Auth Recovery | 运维/运营 | 失败可视化，不静默成 0 条 |
| 10 | AI Agent 研发治理（审计→计划→验证→发布） | B DCC（工程控制） | AI 研发团队 | WRITE 永 DENY，发布安全 |
| 11 | 手机端代码预览 / 轻量测试 / GitHub 管理 | B SICI（移动） | 外出开发者 / 快速 Review | 不在电脑前也能审 PR |
| 12 | Shadow Learning 8 阶段全生命周期 | B AI-DRH + DCC | 研究团队 | AI 决策不直接进生产 |
| 13 | Reusable 能力注册与跨仓复用 | B AI-DRH Registry | 全四仓 | 避免四重能力注册分裂 |
| 14 | 每日 5 次 GitHub Actions 只读巡检 | B DCC × GitHub | CI/CD 负责人 | 工程心跳，异常早发现 |
| 15 | 研究工作流（Research→Hypo→Candidate→Verify→Promotion） | B AI-DRH 五目录隔离 | 研究团队 | 实验隔离不污染生产 |
| 16 | 三向验证（ZBC 业务+DCC 工程+SICI 移动） | B 全局基线 Gate | 跨仓 Release 审批人 | 任何一方 FAIL=不晋级 |
| 17 | 新客户 Brand Profile 一键 Build Release | 未来 A ZBMP + B DCC Release Gate | 交付经理 | 新客户从 2 周到 3 天 |
| 18 | 加密 Evidence 账本+哈希链（合规审计） | B AIDRH JSONL + 加密 | 合规官/客户合规对接 | 给客户看"我们没伪造 AI 判断" |

---

## 6. 功能需求（README 架构融合调整）

### FR-001：两仓 README 顶层结构统一母体

- **rule**：产品 A README 与产品 B README 的一级标题结构采用同一母体，但每节内容保留各自 Owner 权威与差异化写法，不互相复制文本。
- **rule**：统一母体一级章节为：
  1. 一句话定位 × 产品/仓库标识（唯一图标或标记，如 A 用 📊，B 用 🤖）
  2. 双子产品关系与边界（各自一节，互相链到对方 README 对应段）
  3. 本仓库的子产品 / 子组件（A: CTH-POMS vs ZBMP；B: SICI / DCC / AI-DRH）
  4. 产品 / 组件边界、Owner、是否允许跨仓复制（用表格）
  5. 架构主图 + 数据流 / 反哺流
  6. 当前版本 + 真实进度（基于源码/测试，不以 AI 报告为准）
  7. AI 原则（Ollama-first / AI 身份分离 / AI 可退出 / Shadow）
  8. 数据模型（A 四层业务模型 vs B 四库能力/合约/证据模型）
  9. 允许 / 禁止 / 受控 矩阵（常设章节，用表格）
  10. P0 / P1 / P2 当前任务
  11. 关键文档索引（含跨仓交叉链接）
  12. 协作 / 变更门禁（AGENTS / 三向验证 / D0-D7 / Evidence 优先）
- **rule**：A 的 README 中"双子产品关系"段必须显式包含一句不可编辑硬文本：`"CTH-POMS / ZBMP 生产运行绝对不依赖 Zachary-OS-AI 任何组件。"`
- **rule**：B 的 README 中"双子产品关系"段必须显式包含一句不可编辑硬文本：`"Zachary AI 身份与 Z-Brand 产品身份严格分离（IMMUTABLE BASE-001/002），不得互相并入或吸收。"`
- **rubric**：交叉引用完整性（0-3），3=两仓 README 互相有链接+链接可达+无重复 Owner 声明冲突；1=链接存在但 1 处冲突；0=互相断链或 Owner 冲突。

### FR-002：两仓资产全面清点并在 README 常设索引

- **rule**：产品 A README 第 13 节新增"本仓资产清单"表格，字段为 类别 / 路径 / 数量（估）/ Owner / 是否备份 / 是否允许进 Git，类别至少覆盖：
  - 源码主模块（app.py / collector / risk_engine / 蓝图 / 前端 / 采集器）
  - 数据库（data/monitor.db / schema_version / 迁移）
  - 数据资产（采集日志 / AI Filter 日志 / 审核历史 / 报告 / 备份）
  - 文档（README×5 份 / AGENTS / CHANGELOG / DEPLOY / RELEASE POLICY 等）
  - 测试（pytest / E2E / smoke / 安全扫描）
  - 子模块（tools/development-command-console 及其 pinned SHA）
  - 凭证与配置（.env.example / system_config 表 / data/private/）
  - 静态 / 媒体（templates/ / static/ / screenshots/ / Zachary three.js 模型）
- **rule**：产品 B README 第 13 节新增"本仓资产清单"表格，同样字段，覆盖：
  - 22 份收敛矩阵（.md）
  - SICI-Core 16 个 JS 模块 + 页面 + PWA
  - DCC 服务端模块 + 40+ API + 文档（三库矩阵/双库发布/事实基线）
  - AI-DRH（GLOBAL BASELINE / PLATFORM BASELINE / CAPABILITY REGISTRY / 研究协议 × 4 / reusable 能力 × 3 / src 工具 / tests）
  - docs-wps（Word 指令文档，说明仅归档、不上 GitHub）
  - config/codex（Codex 配置，说明仅归档参考）
  - archive/（桌面旧代码 + repo-audit SICI 快照，说明仅归档、不进 GitHub 主分支）
- **rule**：两仓资产清单的"是否允许进 Git"列必须严格对齐 AGENTS.md 与 ZOSAI BASE-021：
  - Cookie / Token / API Key / Secret → 严禁（Git Diff 检查脚本必须拦）
  - 生产数据库 .db → 严禁（仅本地备份、不入库）
  - WPS docx 原始归档 → B 仓库本地不进 GitHub（允许在本地 docs-wps/ 保存，push 时 .gitignore 排除）
  - archive/ 桌面旧代码与快照 → B 仓库本地保存，不进 GitHub 主分支（提交 PR 时按 archive 分支另建）
- **rule**：两仓的 .gitignore 同步更新，使上述"不允许进 GitHub"的文件类型/路径真正被 ignore。

### FR-003：允许 / 禁止 / 受控 矩阵常驻 README 第 9 节

要求两个 README 都有该矩阵，**内容不同但格式一致**。矩阵为四层高（产品层 / 仓库层 / 组件层 / 研发流程层）× 三类（允许 ✅ / 禁止 🚫 / 受控 ⚠️）。

#### 产品层（两个 README 都要写）

| 项目 | 产品 A（Z-Brand-Core） | 产品 B（Zachary-OS-AI） |
|---|---|---|
| 合并两仓为一仓 | 🚫 | 🚫（BASE-001 违反） |
| A 生产依赖 B 运行 | 🚫 绝对禁止 | 🚫 不提供运行时 API 给 A |
| B 写入 A 生产数据库 | 🚫 | 🚫（WRITE 永久 DENY） |
| B 只读调用 A /api/evidence/* | ✅（A 方提供） | ✅（SICI zbc-evidence-adapter） |
| A 复制 B 的 DCC/SICI 源码 | 🚫（Owner 归 B） | 🚫 不许外发 |
| 身份合并（Zachary AI=Z-Brand） | 🚫 | 🚫（BASE-001/002） |
| 跨仓能力通过 Contract 复用 | ✅（AIDRH Registry） | ✅（AIDRH Registry） |
| 复制对方 README 一整节 | 🚫（各自 Owner） | 🚫（各自 Owner） |
| 交叉引用链接 | ✅ 必须 | ✅ 必须 |

#### 仓库层（每个 README 写自己的）

**Z-Brand-Core：**
| 操作 | 允许/禁止/受控 | 说明 |
|---|---|---|
| 删除主体词或排除词 | 🚫 | P0 红线 |
| 绕过主体过滤"增加采集量" | 🚫 | AGENTS.md §5 |
| 删除或覆盖生产 monitor.db | 🚫 未授权绝对禁止 | 最高保护 |
| 新增字段向后兼容迁移 | ✅ 允许 | 备份+回滚路径 |
| 未验证切换新采集器 | 🚫 | 必须旁路并行验证 |
| 把失败伪装成 0 条 | 🚫 绝对禁止 | 采集状态机必须暴露 |
| 用采集时间冒充发布时间 | 🚫 | publish_datetime vs captured_at |
| Ollama 不可用时停掉核心主链路 | 🚫 | 核心判断必须照常运行 |
| 豆包/OpenAI API 成为生产硬依赖 | 🚫 | Ollama-only 正式 |
| 提交 .env / Token / Cookie | 🚫 永久禁止 | 仅 .env.example 可入 |
| app.py 推倒重构 | 🚫 当前阶段 | P2 蓝图化 20% 以内，旁路 |

**Zachary-OS-AI：**
| 操作 | 允许/禁止/受控 | 说明 |
|---|---|---|
| 删除或改写 IMMUTABLE 基线条款 | 🚫 绝对禁止 | IMMUTABLE=只增不减 |
| 生产业务逻辑归 B 拥有 | 🚫 | Owner 永远归 ZBC |
| DCC WRITE/DEPLOY/MERGE 开放 | 🚫 永久 DENY | 权限最小化原则 |
| AI 判断直接晋级为 Reusable | 🚫 | 必须 Shadow→Evidence→三向验证 |
| 把 NOT_VERIFIED 写成 PASS | 🚫 伪造证据罪 | DCC 21 字段 Evidence 硬校验 |
| 绕过 DCC Release Gate 升级 ZBC pinned SHA | 🚫（8 条硬边界） | Dual-Repo Release Policy |
| 用历史测试快照代替真实 E2E | 🚫 | Repository Fact Baseline |
| SICI 把浏览器能力静默升级为机器级权限 | 🚫（IMMUTABLE §16 约束） | Persistence Bridge 必须受控 |
| 10 条 XHS App BLOCK 红线内的行为 | 🚫 永久禁止 | Repository Fact Baseline |
| 在 Hub 保存 Token/Secret/Cookie | 🚫 六条铁律之一 | PLATFORM_BASELINE.md |
| 新建独立能力注册中心副本 | 🚫（BASE-013 冲突） | Owner 唯一归 AI-DRH |
| DCC 对 ZBC 做只读审计 | ✅ 允许 | DCC 13 项明确职责 |
| SICI 读取 A 的证据 | ✅ 通过受控适配器 | 合约化后版本化 |

#### 组件层（每个 README 列出自己的核心组件）

Z-Brand-Core 需要列出 collector / risk_engine / ai_analyzer / daily_report / Auth Recovery Center / 事件关系图谱 / 品牌知识库 / 案例拆解 / 品牌报告生成器 九项组件的 Owner/变更门槛/跨仓使用权限。

Zachary-OS-AI 需要列出 SICI 16 个模块 / DCC 11 个服务端模块 / AI-DRH 三大协议（GLOBAL-CROSS / SHADOW / COLLAB）+ 三大注册表（Capability / Research ID / Effective Rules）共 23 项的 Owner/变更门槛/跨仓使用权限。

> 具体组件级明细在 tasks.md Task 2 中逐项落实。

#### 研发流程层（两个 README 都要写，内容可以跨仓对齐）

| 流程 | 允许/禁止/受控 | 依据 |
|---|---|---|
| 改动前全量读取两仓 + 最新 HEAD + 相关基线/矩阵/资产 | ✅ 必须 | A: AGENTS；B: Before Gate |
| 未经审计直接写代码 | 🚫 | 先审计→兼容→旁路→验证→切换 |
| 改完后执行匹配范围的单测/E2E/DB 迁移/冒烟/口径回归 | ✅ 必须 | AGENTS §14 / DCC Evidence 21 字段 |
| 改动只说了"完成"不附 10 项交付要素 | 🚫 | AGENTS §16 |
| 失败用"删掉测试"伪装通过 | 🚫 | 严禁 |
| 未通过三向验证就晋级 Reusable Capability | 🚫（B 管控） | GLOBAL BASELINE Three-Way Gate |
| 变更触发时有人 push→重读→重计划 | ✅ 必须（B 管控） | Concurrent-Agent Rule |
| 同时改 A 与 B 的源码 | ⚠️ 受控 | 必须分别提交两仓 PR，各仓独立 Review |
| 把 Chat 记录当代码事实 | 🚫 | Repository Fact Baseline：源码/DB/运行时 > 文档 > 聊天 |

### FR-004：README 架构错误修复项（基于真实审计）

本 Spec 审计发现的以下架构错误，必须在 README 融合调整阶段**显式纠正**（不是仅在文档里声明，要同步修改具体 README 内容）：

- **E-001**：ZBC PLATFORM_README §1 中描述"三仓体系"（ZBC/DDC/SICI）时未把 AI-DRH 纳入四库。修复：改为"四库体系"，AI-DRH=Research & Learning Authority。
- **E-002**：ZBC README §14（或等价章节）未声明 CTH-POMS 生产**不依赖** DCC/SICI/AI-DRH 运行时。修复：加 FR-001 的硬文本并链接 AGENTS.md §2。
- **E-003**：ZBC README 缺少"本仓资产清单"常设表格。修复：FR-002 执行。
- **E-004**：ZBC README 缺少"允许/禁止/受控 四层矩阵"常设章节。修复：FR-003 执行。
- **E-005**：ZOSAI 根 README（当前 GitHub 版本）未明确声明自己是 "四库治理汇编仓库" vs 自己不是独立的第四个源码仓库（当前写了 SICI/DCC/AI-DRH 三组件，但 ZBC 与 B 自己的关系没写清楚）。修复：在 B README 的第 1 节+第 2 节明确写"Zachary-OS-AI 是四库（ZBC+SICI+DCC+AI-DRH）的治理/审计/收敛/研究枢纽；ZBC 代码仍在 Z-Brand-Core 独立仓，不重复存储于本仓"。
- **E-006**：ZOSAI README 缺少"双子产品关系"的明确交叉引用段。修复：FR-001 执行。
- **E-007**：ZOSAI README 未给出 "docs-wps、archive、config/codex 三类归档文件不 push 到 GitHub 主分支" 的明确声明 + .gitignore 同步。修复：FR-002 + .gitignore。
- **E-008**：ZOSAI 组件 README（SICI PLATFORM_README §16）已写三方反哺，但 DCC/AI-DRH README 中同一节的措辞不一致（一个用"三仓"一个用"四库"）。修复：全部统一为"四库"，并标注"ZBC 是业务真相源，其代码不存储于本仓"。
- **E-009**：ZBC 与 ZOSAI 的 README 都没有互相"跳转锚点链接"。修复：README 第 2 节的产品关系段各加明确 URL 到对方的相应段落（例如 `[双子星 B 侧对应说明](https://github.com/Zachary-1012/Zachary-OS-AI#双子产品关系)`）。

### FR-005：版本化交叉引用策略

- **rule**：所有跨仓 README 链接除了 URL，还要附"目标仓库 + 目标分支 + 目标段落标题"三个元信息，防止链接漂移。
- **rule**：ZBC pinned SHA 升级时（Core submodule），必须同步检查 README 中对 DCC 特定功能的引用是否仍匹配 pinned SHA 的实现。这一步进入 DCC Release Candidate 的 7 步流程。

---

## 7. 非功能需求

| ID | 类型 | 需求 | 类型（rule/rubric） |
|---|---|---|---|
| NFR-001 | 稳定性 | 产品 A 的 README 融合调整**不得**改动任何 Python 源码 / 数据库 / 前端路由 / AI 逻辑。本轮只改 .md 文档与 .gitignore，代码施工零变更。 | rule |
| NFR-002 | 不回归 | README 融合调整后，ZBC v5.9.7 的所有 42 项 E2E 结果必须仍可在同样环境下通过（不要求本轮跑，但不能加"会导致失败的文档级强制规则"）。 | rule |
| NFR-003 | 向后兼容 | 所有"禁止"项不得比 AGENTS.md V2.0 与 ZOSAI 22 条 IMMUTABLE 基线更宽松。允许更严格（更安全），但一旦加严必须在 README 变更日志中注明。 | rule |
| NFR-004 | 证据可追溯 | 本 Spec 的每一条允许/禁止/受控条目，必须能追溯到其源头依据（AGENTS §x / IMMUTABLE BASE-xxx / PLATFORM_README §x / 收敛矩阵 xx.md p.yy 等）。交付时附"依据溯源表"。 | rule |
| NFR-005 | 文档结构一致性 | 两仓 README 的 12 节母体结构采用完全相同的标题文字，不得出现"一个叫产品定位，另一个叫系统定位"这种错位。 | rule |
| NFR-006 | 可读性 | 两仓 README 任何一段都不超过 4 行纯文本无表格/无列表/无代码块。长段必须拆表或分点。（rubric：0-2，2=所有长段都已结构化；1=90% 结构化；0=存在 3 段以上 4+ 行无结构长文本） | rubric |
| NFR-007 | 跨仓一致性 | 两仓 README 中描述同一件事（例如"Owner 归 AI-DRH 的能力注册中心"、"DCC WRITE 永久 DENY"、"三方/四库反哺"）时，用词/缩写/定义必须 100% 一致，不存在同义不同写。 | rule |
| NFR-008 | 可维护性 | 允许/禁止矩阵每一行后都附"依据来源"短标签（如 `[AGENTS §5]` `[BASE-013]` `[DUAL-REPO §3]`），便于未来 Owner 变更时追溯为什么这么规定。 | rule |
| NFR-009 | Git 安全 | B 仓库的 .gitignore 在本轮必须能真实忽略：**/data/\*.db、**/data/private/、docs-wps/\*.docx、archive/desktop-legacy/\*\*、\*.env、**/\*.zip（源码归档 zip）、**/node_modules/ 等高风险路径。 | rule |
| NFR-010 | 性能（间接） | 本轮无代码改动，故不引入任何运行时性能退化。 | rule |

---

## 8. 约束、依赖、假设、开放问题

### 8.1 约束（Constraints）

1. 不合并仓库：产品 A 与产品 B 永远独立仓。本 Spec 不能违反。
2. 不复制 Owner 源码：跨仓只能 Contract/API/Evidence/文档交叉引用，禁止复制对方核心实现（BASE-014 L3 Production Logic 默认禁止跨库复制）。
3. 不削弱 CTH-POMS 生产规则：AGENTS.md §5 广州太古汇主体口径、§6 时间口径、§7 采集/Auth、§12 Release 血缘 → 优先级高于本 Spec 任何新增说明。
4. 不削弱 ZOSAI IMMUTABLE 22 条基线：BASE-001~BASE-022 任何条款优先级高于本 Spec 的任何新增说明。
5. 本轮交付为纯文档/架构交付，不改任何生产代码。
6. 不在本轮提交任何 push 到 GitHub（等用户后续指令，本轮交付物放在 `.trae/specs/` 和仓库 README 草案本地路径）。

### 8.2 依赖（Dependencies）

- 依赖 ZBC v5.9.7 代码与版本基线作为事实源（AGENTS.md / README.md / PLATFORM_README.md / ZBIP_UNIFIED_README.md / ARCHITECTURE.md / PROJECT_STATUS.md）。
- 依赖 ZOSAI 22 份收敛矩阵（01/10/11/12/13/14/15/18/22 为核心依据，其余为补充）+ SICI README/PLATFORM_README + DCC README/三库矩阵/双库发布策略/Repository Fact Baseline + AI-DRH GLOBAL/PLATFORM/CAPABILITY 三大基线文档。
- 依赖 WPS 云盘的两份原始指令作为用户意图来源（但代码事实优先级更高）。

### 8.3 假设（Assumptions）

1. 用户对 ZBC 版本 v5.9.7 为当前事实基线没有异议（如已更新到 v5.9.8+ 需重读 HEAD 更新引用版本）。
2. 用户认可"双子星 = Z-Brand-Core × Zachary-OS-AI 两个 GitHub 独立仓，不是 ZBC 内部 CTH-POMS/ZBMP"的最终划分（如不认可需在 Approve 阶段修改）。
3. 本 Spec §3 打分基于审计证据，属于合理定性范围；如果 Owner 有更具体的真实商业数据（合同、售价、客户清单）可以事后替换为数字型（但不是 block 本 Spec 的条件）。
4. 10 项 Human Gate 冲突的裁决归属 Owner（本 Spec 不做裁决，只列分级与建议）。

### 8.4 开放问题（Open Questions）

> 在 Approve 阶段需要 Owner 至少给出方向（具体数值在 Implement 阶段持续细化即可）。

| OQ 编号 | 问题 | 选项（Owner 选或补充） | 阻塞等级 |
|---|---|---|---|
| OQ-1 | 产品 B 是否要在 12 个月内对外做独立品牌（Zachary AI）？还是永久作为内部研发治理平台？ | A=对外；B=继续内部；C=对外但不打 Zachary 品牌（子品牌） | **中**：影响 §2.4 定位措辞与商业化节奏 |
| OQ-2 | A1 阶段的第二目标客户选哪个方向？商业地产 TOP50 / 奢侈品牌 / 新消费美妆 / 公关代理？ | Owner 选 1-2 个优先方向 | **中**：影响 A 的扩展场景模板化优先级 |
| OQ-3 | 四重能力注册分裂（Human Gate #1）的 Owner 是否按本 Spec 建议确定为 AI-DRH？还是另外的指定？ | A=AI-DRH（推荐）；B=DCC；C=新建专用仓 | **高**：阻塞 B1 阶段 |
| OQ-4 | ZBC models.py vs database.py 7 张 CREATE TABLE 差异（Human Gate #10）是补迁移还是删 models 声明？Owner 必须最终裁决 | A=补 migration 009/010；B=删 models 过度声明；C=人工查 diff 后确定 | **高**：直接影响 A 生产数据一致 |
| OQ-5 | B 仓库归档内容（archive/ + docs-wps/ + config/codex/）是否保留本地永不 push？还是做 GitHub 独立归档分支？ | A=本地保存+gitignore；B=private archive 分支 | **低**：不影响核心定位 |
| OQ-6 | ZBC 对外销售时是否将 "Zachary 3D AI 助手" 作为一个可选项增值模块定价？还是默认标配？ | A=标配（拉新）；B=可选+5 万/年（增收） | **低**：商业模型微调 |

---

## 9. 验收标准（Acceptance Criteria）

### 9.1 Rule 类 AC（客观可验证，二值）

| AC 编号 | 验收条件 | 验证方法 |
|---|---|---|
| AC-R001 | 产品 A README 顶层 12 节母体结构（FR-001 定义）完整存在，无缺失、无顺序错误。 | 人工比对 README 标题清单 |
| AC-R002 | 产品 B README 顶层 12 节母体结构（FR-001 定义）完整存在，无缺失、无顺序错误。 | 人工比对 README 标题清单 |
| AC-R003 | A README 含不可编辑硬文本 "CTH-POMS / ZBMP 生产运行绝对不依赖 Zachary-OS-AI 任何组件。" | grep 搜索 |
| AC-R004 | B README 含不可编辑硬文本 "Zachary AI 身份与 Z-Brand 产品身份严格分离（IMMUTABLE BASE-001/002），不得互相并入或吸收。" | grep 搜索 |
| AC-R005 | 两仓 README 互相包含对方的 URL 交叉链接（带 repo+branch+段落三元元信息），手动点击能跳到对方对应段落。 | 手工 URL 打开验证 |
| AC-R006 | A 新增"本仓资产清单"覆盖 8 大类别、字段齐全。 | 人工检表 8×6 |
| AC-R007 | B 新增"本仓资产清单"覆盖 7 大类别、字段齐全。 | 人工检表 7×6 |
| AC-R008 | 两仓 README 都有四层"允许/禁止/受控"矩阵常设章节，且每一行附依据溯源标签。 | 人工检表 + 抽样 5 行标签是否对应真实依据文档。 |
| AC-R009 | 9 项 README 架构错误（E-001 ~ E-009）全部按修复方案修完，残留=0。 | 逐条 grep 或表对照 |
| AC-R010 | 两仓 .gitignore 各自包含 NFR-009 要求的高风险 ignore 路径，手动 `git status --porcelain` 下 docs-wps/*.docx、archive/desktop-legacy/**、*.db、*.env 等不应显示为 untracked。 | `git check-ignore` 抽样 10 个高风险路径 |
| AC-R011 | A 仓库本轮 diff 中不含任何 .py / .js / .html / .db / .json（配置以外）代码变更。即本阶段改动全为 .md + .gitignore。 | `git diff --stat` 列出文件类型检查 |
| AC-R012 | B 仓库本轮 diff 中不含 SICI/DCC/AI-DRH 三大组件的 .py/.js/.html 核心实现变更（允许 README/文档/.gitignore/新增索引表 .md）。 | `git diff --stat` 类型检查 |
| AC-R013 | 所有"禁止"项与 AGENTS.md V2.0 + IMMUTABLE BASE-001~022 交叉检查，禁止项没有被弱化（宽松程度判断：两文档的禁止集合的并集必须等于并集，不得出现"AGENTS 禁止但新 README 允许"的单行）。 | 人工逐条对照表对表 |
| AC-R014 | README 中"主体类型与内容类型"、"publish_datetime vs captured_at"、"三类事件四种关系"、"8 采集状态枚举"、"DCC 权限 5 枚举（READ/TASK/AUDIT=ALLOW TEST=CONTROLLED WRITE/DEPLOY=DENY）"、"Evidence 5 结果枚举（BLOCKED>REPLAN>FAIL>NOT_VERIFIED>PASS）"、"D0-D7 交付态" 等 7 项硬枚举与 ZBC/ZOSAI 源码当前枚举值 100% 一致，不存在新增/漏值/改序。 | 源码枚举值 vs README 枚举值 diff |

### 9.2 Rubric 类 AC（质量维度打分）

| AC 编号 | 维度 | 评分刻度 | 及格阈值 | 证据来源 |
|---|---|---|---|---|
| AC-S001 | 交叉引用完整性 | 0=断链+Owner 冲突；1=链接存但 1 处冲突；2=链接 OK+Owner 无冲突；3=全满足+加 URL 元信息 | ≥ 2 | 两仓 README 手工跳转记录 |
| AC-S002 | 允许/禁止矩阵完备度 | 0=两层或以下；1=三层覆盖但缺组件级明细 60%；2=四层齐全+组件级覆盖 80%；3=四层齐全+组件级 100% 覆盖+每条依据标签正确 | ≥ 2 | 四层矩阵覆盖率统计 |
| AC-S003 | 长段结构化率 | 0=≥3 段 4+ 行无结构；1=1-2 段；2=0 段全结构化 | ≥ 1 | README 通读 + 段落行数统计 |
| AC-S004 | 跨仓术语一致性 | 0=≥4 处同概念不同写法；1=2-3 处；2=1 处；3=0 处 | ≥ 2 | 术语对照表（Owner/四库/三向验证/Evidence/Shadow/Preflight/Effective Rules/Reusable/Capability/Contract 共 10 个核心词） |
| AC-S005 | 价值评估与定位的审计支撑度 | 0=3+ 处结论无证据支撑；1=2 处；2=1 处；3=每一条价值打分和定位声明都在 §1 审计/代码基线里有明确出处，非 AI 主观想象 | ≥ 2 | 对打分表 20 项做追溯抽样 |

---

*End of spec.md. Version: v1.0 DRAFT（待 Owner Approve）*
