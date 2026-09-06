# Case Library

> 研究案例库。持续研究工程实践与 AI 能力，禁止为了案例数量堆垃圾资料。

## 1. 案例质量标准

每个案例必须记录：

1. **案例来源** — URL / 论文 / 仓库 / 书籍，可追溯
2. **为什么值得研究** — 与 Zachary AI 平台的关联
3. **原项目解决什么问题** — 原始问题域
4. **我们可以吸收什么** — 原则 / 模式 / 技术
5. **哪些不能照搬** — 上下文差异、License 限制、安全风险
6. **License / provenance** — 许可证与来源审计
7. **如何适配三方平台** — Z-Brand / DDC / SICI 各自的适配方式
8. **是否值得写代码** — 是研究记录还是实现候选
9. **实验结果** — 如果做了实验，结果如何

**缺少以上任一字段的案例不得入库。**

## 2. 持续研究主题

### 工程实践
- GitHub 官方工程实践
- CI/CD 最佳实践
- Dev Container 与可复现开发环境
- Reproducible builds
- Software testing（单元 / 集成 / E2E / 契约测试）
- Sandbox 与隔离执行
- Security 与权限系统

### AI / Agent
- Agent architecture
- Agent evaluation
- Autonomous coding
- Human-in-the-loop
- Learning systems
- Shadow evaluation
- MLOps

### 平台 / 数据
- Evidence / provenance
- Mobile automation
- 多仓库协作模式

## 3. 案例存储

- 位置：`cases/`
- 命名：`YYYY-MM-DD-<topic>-<source>.md`
- 每个案例一个文件，包含上述 9 个字段
- 案例索引：`cases/INDEX.md`

## 4. 案例分级

| 级别 | 说明 |
|---|---|
| `reference` | 仅参考，不计划实现 |
| `candidate` | 候选实现，进入 Research 生命周期 |
| `adopted` | 已吸收为 reusable 能力 |
| `rejected` | 研究后决定不采用，记录原因 |

## 5. 已有案例

> Hub 初始化阶段，案例库为空。Z-Brand-Core 已有 `docs/learning/`（33 案例，commit `af28436`），DDC 已有工程学习记录。Hub 将通过 Research ID 逐步索引跨仓库案例，不复制。

| 案例 | 来源仓库 | 级别 | 索引状态 |
|---|---|---|---|
| Z-Brand docs/learning 33 案例 | Z-Brand-Core | reference | 待索引 |
| DDC research_learning 设计 | DDC | adopted | 已通过 Adapter 复用 |
| DDC five-inspections 巡检模式 | DDC | reference | 待研究 |

## 6. 禁止行为

- 禁止为了案例数量堆砌无价值资料
- 禁止无来源 / 无 License 审计的案例
- 禁止复制第三方代码入 Hub（只吸收原则）
- 禁止把 AI 生成的案例总结当作真实案例
