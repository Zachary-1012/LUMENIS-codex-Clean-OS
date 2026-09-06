# CASE-2026-0010: GitHub Actions Reusable Workflow 模式研究

## 案例来源
- **来源仓库：** Zachary-1012/Development-Command-Console
- **来源文件：** `.github/workflows/reusable-verify.yml`
- **来源 SHA：** `878ebbf5546976cfb49238fd2bd5003022ae2c5b`
- **License：** Internal (Zachary AI Platform)
- **维护状态：** active

## 为什么值得研究
DDC 已经实现了一个 `workflow_call` 触发的 reusable verification workflow，支持 Node.js 和 Python 双 runtime，自动产出 verification-report.json 和 test.log 作为 artifact。这是三仓库共享验证能力的现成模式，Hub 可以直接复用而不是重新设计 CI。

## 原项目解决什么问题
1. **统一验证入口：** 三个仓库不需要各自写完整的验证 workflow，只需调用 DDC 的 reusable workflow
2. **双 runtime 支持：** 通过 `inputs.runtime` 切换 node/python，条件式 setup
3. **Evidence 产出：** 每次运行自动生成 `verification-report.json`（含 repository, commit, runtime, test_command, exit_code）和 `test.log`
4. **最小权限：** `permissions: contents: read`，验证流程只读
5. **Artifact 保留：** `actions/upload-artifact@v4` 上传验证证据，`if-no-files-found: error`

## 我们可以吸收什么
| 模式 | Hub 适配方式 |
|---|---|
| `workflow_call` + inputs 参数化 | Hub 的 research-validation.yml 可改为被三仓库调用 |
| verification-report.json 结构化输出 | Hub data/evidence/ 可引用此格式 |
| `set +e` 捕获 exit_code 但仍失败退出 | Hub CI 应采用同样模式，确保测试失败时 workflow 失败但证据已保存 |
| `if: always()` 上传 artifact | 即使测试失败也保留 Evidence |
| 最小权限 `contents: read` | Hub workflow 同样只读 |

## 哪些不能照搬
1. **DDC 的 reusable-verify.yml 是验证执行器，Hub 不是验证执行器** — Hub 的 CI 只验证 Hub 自身代码，不替三仓库执行验证
2. **`install_command` 输入** — Hub 当前无外部依赖，不需要；但未来如果增加依赖应支持
3. **SQLite 验证** — Hub 不使用 SQLite，不应包含
4. **ReportLab 安装** — Hub 不需要 PDF 生成

## 如何适配三方平台
- **Z-Brand：** 可调用 DDC reusable-verify 验证 Python 业务代码，Hub 不介入
- **DDC：** 已有 reusable-verify.yml，是 Owner，Hub 引用其模式
- **SICI：** PWA 项目可调用 node runtime 验证，Hub 不介入
- **Hub：** 自身 CI 采用相同的 Evidence 产出模式（verification-report.json），但不暴露为 reusable workflow（Hub 不是验证服务）

## 是否值得写代码
**值得，但范围有限：**
- ✅ 在 Hub 的 research-validation.yml 中增加 verification-report.json 产出（与 DDC 格式一致）
- ✅ 在 data/evidence/ 中建立 verification-report 索引格式
- ❌ 不在 Hub 创建 reusable workflow（DDC 已有，避免重复）
- ❌ 不替三仓库执行验证

## 实验结果
- **实验：** 读取 DDC reusable-verify.yml 源码，分析其输入输出和权限模型
- **结果：** 模式可复用；Hub CI 应增加结构化 Evidence 产出
- **Evidence：** DDC commit 878ebbf, file SHA 716040e4c26bed7929fea641e9529f3908e7e5bc
- **NOT VERIFIED：** Hub CI 增加 verification-report.json 后的实际运行结果（待下次 push 后 Actions 运行确认）

## 适配判断
- **研究价值：** high
- **适配价值：** medium
- **风险：** low
- **下一步：** R-2026-0002 中更新 Hub CI 增加 verification-report.json 产出
