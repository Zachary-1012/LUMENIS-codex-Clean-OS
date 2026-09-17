# 序 · 生态品牌架构 / Sequence Ecosystem Brand Architecture V1

> 品牌母体：**序**  
> 品牌哲学：**芥子纳须弥 · 于微处见全局，于一中见万象**

## 正式产品名

| 正式中文名 | 正式英文名 | 稳定技术标识 | Canonical Repository | 角色 |
|---|---|---|---|---|
| 序境 | LUMENIS | LUMENIS | `Zachary-1012/LUMENIS-codex-Clean-OS` | Production Core · Production Truth Owner |
| 序蕴 | LUMENIS Intelligence | OSAI / `Zachary-OS-AI` | `Zachary-1012/Zachary-OS-AI` | Shared Intelligence Capability |
| 序衍 | LUMENIS Growth | GGI / `global-growth-intelligence` | `Zachary-1012/global-growth-intelligence` | Independent Research & Growth Product |
| 序枢 | LUMENIS Command | COMMAND / `lumenis-command` | `Zachary-1012/lumenis-command` | R&D Control Sidecar · Engineering Evidence |

## 命名原则

“序”不是功能前缀，而是母品牌。四个产品以同一哲学形成不同作用：
- **境**：让复杂世界形成可理解、可行动的商业情境。
- **蕴**：让 Evidence、Reasoning、Evaluation、Memory、Learning、Skill 与 Agent 能力沉淀并生长。
- **衍**：从信号与证据向研究、趋势、机会、行动与增长展开。
- **枢**：观察、编排、验证与治理研发活动，但不成为业务运行时依赖。

## 兼容性规则

1. 正式品牌名用于 README、治理文档、产品展示、Canonical Registry 与新的人类可读文档。
2. `OSAI`、`GGI`、`COMMAND`、现有仓库名、package 名、环境变量、API namespace、DB key、历史链接继续作为稳定技术 alias；不得仅因品牌标准化而破坏性重命名。
3. `lumenis-ggi-cross-product` 继续作为稳定机器 `contract_id`；品牌升级不改变其身份语义。
4. 品牌同步不得改变 Truth Owner、数据库所有权、Runtime 独立性、权限、接口、业务实现或发布边界。
5. 旧展示名若仅用于历史说明可标记 Legacy；若会被 Codex/Agent 误认为当前正式名，应从当前治理入口移除或改为技术 alias。

## 当前机器协议

- Contract version: `1.1.0`
- Fingerprint: `68caa37c3f4a8d50f0c0b77befac0e8ae0c954b63b1a7583a8f822a28eaa690f`
- 生效日期：2026-09-17

此文档只定义品牌与治理语义，不授予任何跨产品运行时、数据库或写入权限。
