# SICI Shared Capability Registry

> ZBIP 四产品共享能力注册表 — SICI 侧。
> 遵循：共享能力唯一 Owner；跨库使用 Contract / Adapter / API，不复制核心代码。

## 1. SICI 暴露的能力（5 项）

| Capability ID | 名称 | Owner | 版本 | 状态 | 接口 | Evidence |
|---|---|---|---|---|---|---|
| `SICI-EFFECTIVE-RULES` | Effective Rules Engine | SICI | 1.0 | active | `window.EffectiveRules` | `0b47793` |
| `SICI-RUNTIME-PREFLIGHT` | Runtime Preflight | SICI | 1.0 | active | `window.Preflight` | `876859c` |
| `SICI-MOBILE-UI` | Mobile UI Components | SICI | 1.0 | active | `index.html + css/style.css` | `cb13e57` |
| `SICI-TEST-RUNNER` | Frontend Test Runner | SICI | 1.0 | active | `window.Tester` | `46079f2` |
| `SICI-CI-VERIFY` | CI Verification (via DCC) | SICI | 1.0 | active | `.github/workflows/platform-verify.yml` | `0b47793` |

## 2. SICI 依赖的外部能力（1 项）

| Capability ID | 名称 | Owner | 类型 | 引用 | 状态 |
|---|---|---|---|---|---|
| `DCC-CI-VERIFY` | DCC Reusable Verify Workflow | DCC | github_reusable_workflow | `reusable-verify.yml@448ba21` | active |

## 3. 调用方式

其他产品（DCC / AI-D / Z-Brand）使用 SICI 能力时：
1. 通过本 Registry 查询 capability id、interface、methods、constraints
2. 通过 Contract / Adapter / API 调用，**不复制 SICI 源码**
3. 记录 Evidence（调用方 commit + 被调用方 capability version）

## 4. 运行时查询

```js
// 浏览器
CapabilityRegistry.list();                    // 全部能力
CapabilityRegistry.get('SICI-EFFECTIVE-RULES'); // 单个
CapabilityRegistry.isAvailable('SICI-RUNTIME-PREFLIGHT'); // true
CapabilityRegistry.getContract('SICI-EFFECTIVE-RULES');   // 契约详情
CapabilityRegistry.getDependencies();          // 外部依赖
CapabilityRegistry.getSummary();               // 统计摘要
```

## 5. 变更规则

- 新增能力：必须含 id / owner / version / status / interface / methods / constraints / evidence_commit / contract
- 废弃能力：status 改为 `deprecated`，保留至少一个版本周期
- 能力升级：version 递增，methods 变更须在 contract 中注明破坏性变更
- 禁止：跨库复制源码、未登记即使用、绕过 Registry 直接依赖内部实现
