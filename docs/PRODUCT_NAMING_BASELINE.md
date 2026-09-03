# 产品命名基线

> ⚠️ **LEGACY**：本文档为旧命名基线（2026-08 时期），其中「Z-Brand Intelligence Platform」为历史名称。
> 最新 Canonical 命名以 [`00-GOVERNANCE/CANONICAL-NAMING-AND-TWIN-SYNC.md`](../00-GOVERNANCE/CANONICAL-NAMING-AND-TWIN-SYNC.md) 为准：
> 中文品牌=**序境**，韩文=**서경**，英文 Canonical Brand=**TBD**，品牌哲学=**芥子纳须弥**。
> 本文档保留作为历史证据，不得作为新开发的命名依据。

> 本文件只负责产品正式命名与层级关系，不定义功能、不修改架构、不改变代码行为。

## 0. 统一平台层（最顶层）

- 中文/英文正式名称：**Z-Brand Intelligence Platform**
- 定位：三产品统一平台层（最顶层母平台）。**本层不新造英文缩写，正式文档统一使用全称。**
- 下辖三个**并列**的产品 / 业务平台：品牌业务生产平台（ZBP）、研发工程治理中枢（DCC）、智能研究学习中枢（SICI）。
- 关键层级认知：**ZBP 不是整个母平台/最顶层**；ZBP 与 DCC、SICI 并列，三者共同属于 Z-Brand Intelligence Platform。

```
Z-Brand Intelligence Platform（统一平台层）
├── 品牌业务生产平台 ZBP（产品/业务平台层）
│   ├── CTH-POMS（广州太古汇舆情监测系统）
│   └── ZBMP（Z-Brand 品牌监测平台，ZBP 内增强能力层）
├── 研发工程治理中枢 DCC
└── 智能研究学习中枢 SICI
```

## 1. 统一平台层下三个并列产品 / 业务平台

| 中文正式名称 | 英文正式名称 | 简称 | 上级 | GitHub 仓库 |
|---|---|---|---|---|
| 品牌业务生产平台 | Z-Brand Business Production Platform | ZBP | Z-Brand Intelligence Platform | Zachary-1012/Z-Brand-Core |
| 研发工程治理中枢 | Development Command Console | DCC | Z-Brand Intelligence Platform | Zachary-1012/Development-Command-Console |
| 智能研究学习中枢 | Intelligent Research & Learning Hub | SICI | Z-Brand Intelligence Platform | Zachary-1012/SICI-Core |

> DCC、SICI 不归属 ZBP；三者平级，共同上属于 Z-Brand Intelligence Platform。

## 2. 品牌业务生产平台（ZBP）内部产品

CTH-POMS 与 ZBMP 继续归属于品牌业务生产平台（ZBP）。

### CTH-POMS
- 中文全称：广州太古汇舆情监测系统
- 英文全称：CorTech Lab · Guangzhou Taikoo Hui Public Opinion Monitoring System
- 简称：CTH-POMS
- 定位：当前主力生产 / 客户交付入口

### ZBMP
- 中文全称：Z-Brand 品牌监测平台
- 英文全称：Z-Brand Monitoring Platform
- 简称：ZBMP
- 定位：品牌业务生产平台（ZBP）内部的母平台增强能力层（非第二套 Core，与 CTH-POMS 共用同一 Core / DB / Runtime）

## 3. 命名规则

1. 正式文档首次出现必须使用中文全称 + 英文全称 + 简称；最顶层统一写全称 Z-Brand Intelligence Platform，不自造缩写。
2. 后续可使用简称。
3. CTH-POMS 与 ZBMP 名称不得删除、缩写成模糊名称或互相替代；二者均隶属于 ZBP。
4. 层级表述固定为：Z-Brand Intelligence Platform →（ZBP / DCC / SICI 并列）→ ZBP 内 CTH-POMS / ZBMP。禁止再把 ZBP 表述为整个母平台或最顶层。
5. 本文件是命名基线；后续 UI、README、架构图、任务单、Evidence、Release 文档必须与本文件一致。
6. 本次仅修正命名层级认知，不进行代码重构、功能修改、数据库/采集/API/Runtime 变更或 UI 修改。
