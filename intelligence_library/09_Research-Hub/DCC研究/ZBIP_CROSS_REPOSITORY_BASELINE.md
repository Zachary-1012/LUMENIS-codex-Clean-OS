# Z-Brand Intelligence Platform — Cross-Repository Baseline

> 生效：2026-08-31
> 目的：将三个独立 Repository 的统一平台关系、职责边界、交叉验证和变更纪律固定下来。

## 1. 统一平台

**Z-Brand Intelligence Platform（ZBIP）** 是统一平台层/组织入口，不是第四个运行时 Repository，也不替代三个独立 Repository。

```text
Z-Brand Intelligence Platform（ZBIP）
│
├── 品牌业务生产平台（ZBP）
│   ├── CTH-POMS
│   └── ZBMP
│
├── 研发工程治理中枢（DCC）
│
└── 智能研究学习中枢（SICI）
```

三个 Repository 保持独立版本、独立研发、独立发布边界。统一平台只提供组织、契约、审计、证据和能力地图，不制造隐式运行时依赖。

## 2. Ownership

- **Z-Brand-Core**：业务生产 SoT；CTH-POMS 当前生产入口；ZBMP 受控能力层。
- **Development-Command-Console（DCC）**：研发控制平面；负责 Audit / Plan / Evidence / Gate / Release / Learning。
- **SICI-Core（SICI）**：移动/云端开发与执行控制台；负责开发、运行、测试、GitHub、部署等开发表面。

共享能力原则上只有一个 Owner。跨仓库调用必须通过明确 Contract、Evidence 和兼容性验证。

## 3. 交叉验证顺序

```text
最新 HEAD
 ↓
源码事实
 ↓
资产/功能总账
 ↓
Owner
 ↓
依赖关系
 ↓
Contract
 ↓
测试 / Evidence
 ↓
Release Gate
```

文档不能覆盖源码事实；未验证内容必须保持 `NOT_VERIFIED`。

## 4. 变更纪律

1. 收敛不等于删除。
2. 任何旧代码、旧包、旧 API、旧页面、旧数据库结构，在完成依赖确认、替代确认、迁移确认和回归验证前不得删除。
3. 修复问题时只修改问题本身，不顺手优化其他模块。
4. UI 改造不得覆盖业务能力；先固定功能树和页面占位，再施工视觉与交互。
5. 不得将 DCC 或 SICI 变成 CTH-POMS 的生产运行时依赖。
6. CTH-POMS P0 生产稳定性优先于平台理想化重构。

## 5. 交叉验证任务

每次跨仓库升级至少核对：

- 命名与产品定位
- Feature ID / Asset ID
- Owner
- API / Contract
- 数据边界
- Runtime 依赖
- 权限边界
- 测试结果
- Evidence
- Release / Rollback

## 6. 当前状态

本文件只建立治理基线，不修改生产业务代码、数据库、采集器或 UI。
