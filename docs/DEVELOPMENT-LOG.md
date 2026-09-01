# Z-Brand-Core Development Log

## 2026-09-01 — Intelligence Reporting System + Architecture Continuity

### 变更类型
chore/docs: establish unified Z-Brand Intelligence Reporting specification

### 本次对话与研发决策摘要

本轮围绕 CTH-POMS 上线、ZBMP 定位、Development-Command-Console 研发中枢，以及 Z-Brand Core（ZBC）统一报告能力进行全局校准。

1. **CTH-POMS 当前仍为 P0 / 第一优先级**
   - 目标：优先完成稳定生产上线。
   - 新增报告能力不得阻塞或重构 CTH-POMS 当前生产链路。
   - CTH 上线前坚持 Release Gate，而非为了扩展功能继续扩大开发范围。

2. **ZBMP 架构边界再次确认**
   - ZBMP 不是第二个独立产品，不从 CTH-POMS 中拆出。
   - ZBMP 继续留在 Z-Brand-Core 内，作为受 Key / License / Feature Gate 控制的增强能力层。
   - 不复制第二套 Core、不建立与 CTH 相互竞争的长期运行主链。

3. **Development-Command-Console 定位确认**
   - DCC 是整个 Z-Brand 的内部 AI 研发中枢，不是 CTH-POMS 生产运行时依赖。
   - CTH、ZBMP、DCC 按既定优先级并行推进，但 CTH 上线不等待 DCC 或 ZBMP 全部完成。

4. **ZBC 制式报告能力与 Zachary 个人消息回复模板严格分离**
   - 本次报告规范属于 Z-Brand-Core（ZBC）的产品级 Intelligence Reporting System。
   - 不属于 Zachary 人格、个人交互、聊天回复或 AI 消息模板。
   - ZBC 报告标准必须保持专业、统一、可审计、可复用、可产品化。

### 新增能力规范

新增：`docs/ZBRAND_INTELLIGENCE_REPORTING_SPEC.md`

Commit：`6aea9da0620d22a16d9d001469c3cc392da78f79`

建立统一的：

`Evidence → Finding → Assessment → Implication → Action`

并加入 `Confidence` 置信度层，用于区分事实、发现、分析判断、商业影响和建议动作，避免 AI 推测被表达为事实。

### 六级报告深度

- **L0 即时**：风险弹窗、首页卡片、消息中心、实时事件。
- **L1 简约**：AE 快速浏览、日报摘要。
- **L2 标准**：日报、周报、月报、常规客户汇报。
- **L3 精细化**：专报、品牌分析、Campaign、招商专题、对标。
- **L4 深度研究**：消费者洞察、市场情报、品牌研究、重要招商研究。
- **L5 白皮书**：年度研究、行业研究、品牌/消费者白皮书。

### 统一页面/报告组件方向

逐步让弹窗、详情页、Dashboard、HTML 报告、PDF 报告共享同一内容模型和组件，包括：

- Executive Summary
- KPI
- Finding Card
- Evidence Card
- Assessment Card
- Risk Card
- Event Timeline
- Trend
- Entity / Brand Profile
- Benchmark
- Case Reference
- Recommendation
- Confidence
- Source & Method
- Limitations

### 适配与安全边界

本规范只定义统一模型和边界，本次不要求立即实现全部页面或报告。

禁止因模板改造而：

- 改写 `SUBJECT_WORDS` / `SUBJECT_EXCLUDE_WORDS`；
- 弱化 `subject_hit()` 或主体 SQL 过滤；
- 改变 `publish_datetime` / `captured_at` 语义；
- 让 AI 决定事实、主体、时间或最终风险；
- 让报告模板反向改变生产数据；
- 为报告模板引入新的生产运行时依赖；
- 将采集失败渲染为“无舆情”。

### 实施顺序

`CTH-POMS Release Gate → L0/L1/L2 最小适配 → L3 专报/案例 → ZBMP L3/L4 → L5 研究/白皮书`

本次新增属于**规范层增量**，不改变现有生产逻辑。

## 2026-08-31 — DCC Repository Architecture Convergence V1.0

### 变更类型
chore: restore development console as private submodule

### 背景
`Development-Command-Console`（DCC）原为 Z-Brand-Core 内 `tools/development-command-console/` 下的旧 v0.1 源码副本（仅 README.md + index.html）。DCC 已发展为独立 Private 仓库（v0.3 Local AI Bridge，82 个自动化测试），需通过 Git Submodule 方式回挂 Core，而非源码复制。

### 执行内容

1. **Before Baseline**
   - Core Before SHA: `1e251747a5a9d386f6abf443b5f7d4032009d319`
   - DCC Before SHA: `6bffaa9f4a8d82bb7c75b436e44d1c4968f220b5`
   - DCC Pinned SHA: `0e52b7fb8af003788960a5a54645e890584ddcb7`

2. **旧副本处理**
   - 备份旧副本到 `D:\Taikoo-monitor-new-backups\dcc-legacy-<timestamp>\`
   - 从 Core 移除 `tools/development-command-console/README.md` 和 `index.html`

3. **建立 Private Git Submodule**
   - `.gitmodules` 新增：
     - path = `tools/development-command-console`
     - url = `https://github.com/Zachary-1012/Development-Command-Console.git`
   - gitlink pinned to `0e52b7f`（mode 160000）

4. **旧 Workflow 退役**
   - 移除 `.github/workflows/development-command-console-pages.yml`

5. **文档更新**
   - 更新 `docs/REPOSITORY-FACT-BASELINE.md`
   - 新增本 DEVELOPMENT-LOG.md

### 验证结果

| 检查项 | 结果 |
|---|---|
| .gitmodules path/url 正确 | PASS |
| Submodule pinned SHA = DCC HEAD | PASS (`0e52b7f`) |
| SHA 在 DCC 仓库真实存在 | PASS |
| Core 无第二份 DCC 源码 | PASS |
| DCC 82 tests | PASS (82/82, 0 failed) |
| 安全扫描（无 Token/Secret） | PASS |
| Submodule integration check | PASS (7/7) |
| CTH-POMS 未修改 | PASS |
| ZBMP 未修改 | PASS |
| 生产业务逻辑未修改 | PASS |

### 未完成 / 待验证

- GitHub Actions 对 Private Submodule 的读取权限：待 Push 后 CI 运行验证
- GitHub 二次 HEAD 核验：待 Push 后执行
- DCC 仓库侧 baseline 文档同步：需在 DCC 仓库单独提交更新

### 安全声明

- 未将 DCC 或 Core 改为 Public
- 未写入任何 Token/PAT/Secret
- 未修改生产业务逻辑
- 未合并 DCC Git 历史到 Core
- DCC 继续作为独立 Private 仓库存在
