# Z-Brand-Core Development Log

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
   - 原因：DCC 自有仓库已配置独立 pages.yml + test.yml，旧 workflow 仅服务旧副本，无其他引用

5. **文档更新**
   - 更新 `docs/REPOSITORY-FACT-BASELINE.md` 为收敛后状态
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
