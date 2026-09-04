# LUMENIS Engineering Governance V1.0

## 1. Authority

本文件是 Z-Brand-Core 在 LUMENIS 双核融合阶段的工程治理基线。它不替代生产业务规则、数据库事实或测试证据；发生冲突时，以实际源码、运行结果、最新 Contract 与本治理基线共同判断，禁止以历史文档覆盖事实。

## 2. Architecture Boundary

```text
LUMENIS Intelligence OS
├── Intelligence Core  → Zachary-OS-AI
└── Production Core    → Z-Brand-Core
```

两个 Repository 保持物理分离。禁止建立第三核心或通过复制源码形成长期平行实现。共享通过 Contract、Evidence、Trace、Permission、Lifecycle、Skill Interface 与 AI Gateway Interface 完成。

## 3. Change Order

所有重要研发变更遵循：

`READ → AUDIT → ANALYZE → PLAN → PATCH PREVIEW → TEST → VERIFY → HUMAN APPROVAL → COMMIT → PUSH`

内部工程循环必须有界：

`INSPECT → PLAN → EXECUTE → VERIFY → REPAIR → VERIFY → EVIDENCE → EVALUATE`

必须有 iteration / time budget、checkpoint 与 blocked / failed 状态。禁止无限自动循环、绕过人工批准、自动 Merge 或未经批准 Push。

## 4. Production Truth

ZBC 对生产数据、生产业务规则、采集、主体过滤、风险、事件、报告与 Runtime 具有生产真相责任。AI / Agent / Research 输出必须通过 Evidence → Contract → Test → Audit → Release Gate 后才能进入生产能力。

## 5. Protected Rules

以下为硬保护项，不得因融合升级而削弱：

- `SUBJECT_WORDS`
- `SUBJECT_EXCLUDE_WORDS`
- `subject_hit()`
- `CollectorGuard`
- 现有生产数据库及其历史数据

不得未经授权删除、清空、覆盖或重建生产数据库；不得用 AI 绕过确定性业务规则或平台安全边界。

## 6. Repository / Runtime

不得硬编码个人 Windows 路径或用户目录。Repository Registry / Resolver 必须支持 Windows 与 macOS。Secret 必须与源码、前端、日志、测试样例和 Git 历史隔离。

## 7. Skill / AI Governance

Skill 必须有明确 Contract、Permission、Evidence、Evaluation 与 Lifecycle。AI Gateway 必须保持 Provider-Agnostic；现有模型能力不得因新模型接入而被无依据删除。

## 8. UI Governance

UI/UX 必须遵循 LUMENIS Design Language 与真实 State/API Contract。不得以假数据、假实时状态或视觉 Demo 证明功能完成。正式图标不得使用 Emoji。视觉、交互与后端业务边界分离。

## 9. Legacy / Deletion

所有旧文件、旧规则、旧接口和旧 UI 在处理前必须标记：`KEEP / MERGE / MIGRATE / LEGACY / ARCHIVE / DELETE / UNKNOWN`。

`DELETE` 只有在完成引用扫描、依赖扫描、运行验证、迁移/替代、回归测试并获得明确批准后才允许执行。新架构本身不是删除理由。

## 10. Evidence

重要变更必须形成：

`Task → Repository → File → Module → Function → Change → Test → Result → Evidence → Lifecycle → SHA`

文档声明不能替代源码、测试和运行证据。

## 11. Release Gate

上线前必须至少满足：核心功能验证、数据/指标一致性、Evidence 可追溯、Critical / Blocker = 0、故障可发现和可恢复/升级、具备回滚路径。

## 12. Status

**Active · LUMENIS Dual-Core Engineering Governance V1.0**
