# Z-Brand Intelligence Platform — Cross-Repository Baseline

> 生效：2026-08-31
> 目的：固定 SICI 在 ZBIP 三仓库体系中的职责、边界、交叉验证和变更纪律。

## 1. 平台关系

**Z-Brand Intelligence Platform（ZBIP）** 是统一平台层/组织入口，不是第四个运行时 Repository。

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

三个 Repository 继续独立研发、版本和发布；SICI 不因统一平台而吞并其他仓库，也不成为 CTH-POMS 的生产运行时依赖。

## 2. SICI 定位

SICI 是移动/云端开发控制台与执行表面，现有能力包括：代码运行、测试/E2E、GitHub 浏览与集成、部署管理、账号认证、PWA、移动端优先 UI。

SICI 可以读取和执行受控工程任务，但生产业务规则的 Owner 仍在 Z-Brand-Core；研发治理规则和 Release Gate 的 Owner 仍在 DCC。

## 3. 交叉验证

```text
最新 HEAD
 ↓
源码事实
 ↓
资产/功能总账
 ↓
Owner
 ↓
Contract
 ↓
测试 / Evidence
 ↓
Release Gate
```

未验证内容不得标记为已完成。

## 4. 变更纪律

1. 收敛不等于删除。
2. 旧代码、旧包、旧 API、旧页面、旧依赖必须先登记；完成依赖确认、替代确认、迁移确认和回归验证后才允许删除。
3. 修复问题只改问题本身，不顺手做无关优化。
4. UI 改造必须先依据完整功能地图固定信息架构，不得覆盖既有能力。
5. 不得让 SICI 成为 CTH-POMS 的运行时依赖。
6. GitHub 写入、部署和高风险动作必须服从 DCC 的权限与验证边界。

## 5. 当前状态

本文件只建立跨仓库治理基线，不修改 SICI 当前运行代码、认证实现、GitHub 集成或 UI。
