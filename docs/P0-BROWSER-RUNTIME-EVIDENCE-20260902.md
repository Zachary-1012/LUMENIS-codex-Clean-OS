# P0 Browser Runtime 施工 Evidence（2026-09-02）

> 依据：CTR-BROWSER-RUNTIME-P0-01（OSAI Contract）+《Zachary × ZBC AI 编程基线 v1.0》
> 施工方：Z-Brand-Core | 验证方式：本地全量测试 + 真实 E2E

---

## 1. 施工内容（最小新增，未改现有逻辑）

### 1.1 browser_runtime/ 四层模块（ZBC）
| 文件 | 职责 |
|---|---|
| rowser_runtime/contract.py | Browser Contract 接口 + 状态机 + BEEP 执行协议 + 失败分类（P0-BR-01/02/03/07/09） |
| rowser_runtime/policy.py | Browser Policy Engine（P0-BR-04/05，复用 safety_boundary） |
| rowser_runtime/router.py | Browser Router：Provider 注册/选择/降级（P0-BR-12） |
| rowser_runtime/adapters/cdp_adapter.py | CDP Adapter（对接 internal_browser，默认 Provider，不改变现有驻场行为） |
| rowser_runtime/adapters/playwright_adapter.py | Playwright Adapter（P0-BR-10，确定性执行） |
| rowser_runtime/__init__.py | 包入口 + Provider 注册 |

### 1.2 OSAI Contract + 测试基线
| 文件 | 职责 |
|---|---|
| contracts/CTR-BROWSER-RUNTIME-P0-01.md | Browser Runtime 分层 Contract（P0-BR-01） |
| pytest.ini + 	ests/test_contracts_baseline.py | OSAI 最小测试基线（P0-5） |

---

## 2. 测试结果（Test Baseline → 施工后）

| 阶段 | 结果 |
|---|---|
| 施工前 ZBC 基线 | 238 项通过（pytest tests -m "not online"） |
| browser_runtime 单元测试 | **31 项通过**（contract/beep 14 + policy/router 17） |
| 施工后 ZBC 全量回归 | **269 项通过**（238 + 31，无回归） |
| OSAI 最小测试基线 | **8 项通过**（contracts/报告/learning-feed 完整性） |

---

## 3. 真实 E2E 验证（本地）

### 3.1 CDP Adapter（默认 Provider，驻场浏览器）
- CDP health：online=True，port 9222，URL=小红书 explore，page_count=2 → **驻场浏览器正常**

### 3.2 Playwright Adapter（确定性浏览器）
- health：up
- navigate https://github.com → OK，title="GitHub · Change is constant..."
- snapshot → title 正常
- screenshot → 成功生成 PNG
→ **Playwright Adapter 真实可用**

---

## 4. 验收对照（CTR-BROWSER-RUNTIME-P0-01）

| # | 验收项 | 结果 |
|---|---|---|
| T1 | 分层存在（Contract/Router/Adapter/Provider） | ✅ 四层文件全部落地 |
| T2 | 路由正确（CDP/Playwright 选择，未知报错） | ✅ 单测覆盖 |
| T3 | 降级（可配置，默认不降级保稳定） | ✅ enable_fallback 参数 |
| T4 | 证据（record_evidence，无密钥泄露） | ✅ BEEP trace 测试 |
| T5 | 健康（health() 对接） | ✅ CDP health 实测 online |
| T6 | 红线（现有 internal_browser/browser_session 未改） | ✅ 仅新增外层封装，回归 269 通过 |
| T7 | 回归（全量+E2E） | ✅ 269 全过 + E2E 实测 |
| T8 | 安全（无密钥） | ✅ 契约测试扫描无密钥 |

---

## 5. 红线遵守确认
- ❌ 未修改 SUBJECT_WORDS / subject_hit / 产品 Truth
- ❌ 未删除任何稳定功能
- ❌ 未改 internal_browser / browser_session 内部逻辑（仅外层封装）
- ❌ 未引入第三方框架（仅复用已装 Playwright 1.62）
- ✅ 默认 Provider = CDP（不改变现有驻场行为）

---

*Evidence 生成：2026-09-02 | 归属：Z-Brand-Core docs | 状态：P0 施工完成*