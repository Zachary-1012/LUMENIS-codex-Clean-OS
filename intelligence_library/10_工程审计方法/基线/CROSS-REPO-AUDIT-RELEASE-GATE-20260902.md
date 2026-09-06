# Cross-Repo Audit + Release Gate（2026-09-02）

> 施工阶段：P0 Browser Runtime 能力落地 + 业务接入 + Failure Recovery
> 双库：Z-Brand-Core（生产执行） × Zachary-OS-AI（研究/契约）

---

## 1. Cross-Repo Audit：Contract ↔ 实现 一致性

### 1.1 Contract 验收（CTR-BROWSER-RUNTIME-P0-01）
| 验收项 | 要求 | OSAI Contract | ZBC 实现 | 状态 |
|---|---|---|---|---|
| T1 分层存在 | 四层可 import | ✅ 定义 | ✅ 7 文件 | ✅ |
| T2 路由正确 | CDP/Playwright 选择 | ✅ | ✅ 单测 | ✅ |
| T3 降级 | 可配置降级 | ✅ | ✅ get_with_fallback | ✅ |
| T4 证据 | record_evidence 无密钥 | ✅ | ✅ BEEP on_evidence | ✅ |
| T5 健康 | health() 对接 | ✅ | ✅ E2E online | ✅ |
| T6 红线 | 现有逻辑未改 | ✅ | ✅ 回归 286 | ✅ |
| T7 回归 | 全量+E2E | ✅ | ✅ 286 passed | ✅ |
| T8 安全 | 无密钥入库 | ✅ | ✅ secret scan clean | ✅ |

### 1.2 双库关键文件对照
| OSAI 侧 | ZBC 侧 | 对应 |
|---|---|---|
| contracts/CTR-BROWSER-RUNTIME-P0-01.md | browser_runtime/（contract/policy/router/adapters） | ✅ |
| pytest.ini + tests/test_contracts_baseline.py | tests/browser_runtime/（48 测试） | ✅ |
| 施工报告 V1 | docs/P0-BROWSER-RUNTIME-EVIDENCE-20260902.md | ✅ |

---

## 2. Browser Router 业务接入（本轮新增）

### 2.1 新增模块
- `browser_runtime_api.py`：注册 2 个只读端点
  - `GET /api/browser-runtime/status` → Provider 注册表 + 状态机 + 失败分类
  - `POST /api/browser-runtime/probe` → Policy Gate + Router 探测（health/navigate）
- `app.py`：最小注册（try/except，向后兼容，不改变现有 internal-browser API）

### 2.2 真实 E2E（系统启动 8321 端口实测）
| 用例 | 结果 |
|---|---|
| status | 200，providers=[cdp,playwright] |
| probe cdp health | 200，online=true（小红书 explore，XHS_CN_PRIMARY）|
| probe cdp navigate（白名单）| 200，Policy Gate 放行 |
| probe cdp navigate（非白名单 evil-example.com）| 400，failure_class=platform_risk |
| probe playwright health | 200，status=up |

---

## 3. Failure Recovery 增强（本轮新增）

### 3.1 classify_failure 修复（发现并修复 2 处缺陷）
| 缺陷 | 修复前 | 修复后 |
|---|---|---|
| Policy Gate 拒绝 | `unknown`（应 Cooldown/Stop）| `platform_risk` |
| `timed out` 变体 | `unknown`（应有限重试）| `transient` |

### 3.2 新增测试（test_failure_recovery.py，17 项）
- FailureClass 分类：transient/session/page_changed/permission/platform_risk 全覆盖
- BEEP 有限重试：transient 重试至成功、**禁止无限重试（≤MAX_RETRY=3）**、verify 失败标记
- Policy 冷却语义：policy 拒绝→platform_risk→cooldown_or_stop（非重试）
- Evidence 闭环：on_evidence 回调、无密钥

### 3.3 测试基线演进
| 阶段 | 结果 |
|---|---|
| P0 初版 | 269 passed |
| 本轮（+17 Failure Recovery）| **286 passed**（无回归）|

---

## 4. Release Gate 状态

### 4.1 逐项验收
| Gate | 要求 | 状态 |
|---|---|---|
| G-01 单元测试 | browser_runtime 48 项 | ✅ PASS |
| G-02 全量回归 | ZBC 286 passed | ✅ PASS |
| G-03 E2E | 真实系统启动 + CDP/Playwright 实测 | ✅ PASS |
| G-04 契约一致 | T1-T8 全过 | ✅ PASS |
| G-05 红线 | 未改产品逻辑/无密钥/无新依赖 | ✅ PASS |
| G-06 失败恢复 | transient 重试 + platform_risk 冷却 | ✅ PASS |
| G-07 双库一致 | Contract↔实现 对齐 | ✅ PASS |

### 4.2 结论
**Release Gate：P0 Browser Runtime 模块级 = PASS**（能力层完全落地）
**整体 Release Gate：仍为 NOT COMPLETE**（P0 仅为最小修改，业务全链路接入、P1 队列、剩余 Contract 待后续，不达标禁止 App 开发）

---

## 5. 双库提交记录
| 仓库 | commit | 内容 |
|---|---|---|
| ZBC | 8bebf82（HEAD）| browser_runtime_api + classify_failure 修复 + test_failure_recovery + 自动保存（已推送）|
| OSAI | ced5eee | CTR-BROWSER-RUNTIME-P0-01 验收 T1-T8 全过 |
