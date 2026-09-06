# Audit Report — SICI Runtime Preflight（工单 2 · P0）

- 日期：2026-09-01
- 工单：SICI-002 Runtime Preflight 统一启动预检（P0）
- 执行者：Doubao（SICI Owner）
- 语义对齐：DCC `server/startup-preflight.js`（只读学习，未复制源码）
- 前置依赖：工单 3 Effective Rules（`0b47793`）已完成，preflight 消费其 `resolveEffectiveRules()` / `isCapabilityAllowed()`

## 1. 基线与提交

| 项 | 值 |
|---|---|
| Baseline（远程父提交） | `72e5ce6`（工单 3 Audit） |
| Implementation SHA | `876859c` |
| Branch | main |
| Repository | Zachary-1012/SICI-Core |

## 2. 修改范围（5 文件，+417 / -2）

| 文件 | 变更 | 说明 |
|---|---|---|
| `js/preflight.js` | 新增 221 行 | UMD 10 项检查，env 注入可测 |
| `tests/preflight.test.js` | 新增 170 行 | 21 项 Node 断言 |
| `js/app.js` | +23 行（仅 init 区域） | `init()` 最前面调用 `Preflight.run()`，硬阻断显示安全页 |
| `index.html` | +1 行 | effective-rules 之后加载 preflight |
| `.github/workflows/platform-verify.yml` | +2/-2 | test_command 追加 preflight 测试 |

## 3. 未修改范围

- app.js 改动仅限 `@@ -638,7 +638,30 @@`（init 函数区域），未触碰认证/导航/事件绑定/业务逻辑
- 未修改 storage.js / runner.js / tester.js / github.js / deploy.js / sw.js / css/
- 未修改 DCC 仓库

## 4. 10 项检查（硬阻断 / 软警告）

| # | 检查项 | 级别 | 对齐 DCC |
|---|---|---|---|
| 1 | 来源校验（localhost / 127.0.0.1 / github.io / file://） | 硬阻断 | loopback + origin |
| 2 | 核心模块加载（6 个全局对象） | 硬阻断 | REQUIRED_FILES |
| 3 | runtime identity（product/version/protocol） | 硬阻断 | runtime_identity_incomplete |
| 4 | effective-rules resolve 成功且非空 | 硬阻断 | effective_rules |
| 5 | 危险模式（禁止 Shell 模块 / Runner 非 null） | 硬阻断 | FORBIDDEN_SERVER_PATTERNS |
| 6 | denied 能力锁定（github.write/shell.exec/production.deploy=false） | 硬阻断 | deniedCapabilities |
| 7 | 权限校验（已登录则角色须 admin，未登录放行） | 软警告 | permissions |
| 8 | 敏感信息（Token 长度 / DOM 泄露探测） | 软警告 | filterSensitiveData |
| 9 | 审计一致性（版本号 PROB-001） | 软警告 | github_audit |
| 10 | protocol registry（迁移期暂缺） | 软警告 | registry.json |

## 5. 测试结果

- 命令：`node tests/preflight.test.js`
- 结果：**21 passed, 0 failed**
- 覆盖：全 PASS / 来源非法 / Pages 合法 / file:// 合法 / 模块缺失 / ER 缺失 / ER 失败 / ER 为空 / denied 未锁定 / 未登录放行 / 非 admin 警告 / Token 警告 / registry 警告 / 版本警告 / Shell 模块阻断 / checks 完整性 / 状态合法性 / details 非空 / 常量暴露 / 单项函数可调用
- 回归：effective-rules 测试 **20 passed, 0 failed**（未被破坏）

## 6. Audit 检查项

| # | 检查项 | 结果 |
|---|---|---|
| 1 | 提交仅含预期 5 文件 | PASS |
| 2 | app.js 仅 init 区域改动（+23 行） | PASS |
| 3 | 未触碰其他业务模块 | PASS |
| 4 | 远程版两新文件存在（blob 校验） | PASS |
| 5 | 重跑测试 41/41（20+21） | PASS |
| 6 | index.html 引入顺序（ER→preflight→storage→…→app） | PASS |
| 7 | init() 预检逻辑正确（硬阻断 return，软警告 console.warn） | PASS |
| 8 | CI test_command 已追加 preflight 测试 | PASS |
| 9 | 语义对齐 DCC（10 项映射 / 返回结构 / fail code） | PASS |
| 10 | 阻断页不泄露敏感信息（仅显示检查 code+message） | PASS |

## 7. Evidence

- Implementation commit：`876859c`（已在 origin/main）
- 测试输出：`21 passed, 0 failed` + `20 passed, 0 failed`
- 远程 blob：`js/preflight.js` = `76117b3...`，`tests/preflight.test.js` = `762c77dc...`
- app.js diff hunk：`@@ -638,7 +638,30 @@`（证明仅 init 区域）

## 8. NOT_VERIFIED

- 浏览器内实际阻断页渲染（需 Pages 部署后手动触发非法来源验证）；本地 node 测试已覆盖逻辑。
- 与未来 Browser Surface 的联动（preflight 目前不检查 Browser Worker，P2 可扩展）。

## 9. 下一步

- 工单 4（P1）：Shared Capability Registry，将 Effective Rules + Runtime Preflight 登记为 SICI 暴露能力，供 DCC/AI-D 通过 Contract 引用。
- PROB-001 版本号统一、PROB-002 仓库名修正（低优先级，不顺手改，已记录）。
