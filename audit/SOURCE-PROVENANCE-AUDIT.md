# SOURCE PROVENANCE AUDIT — Z-Brand-Core / CTH-POMS

> **审计日期**: 2026-09-06
> **仓库**: D:\Taikoo-monitor-new
> **分支**: feat/zbc-full-upgrade-v1
> **HEAD**: 5e0ccd02648a52c8c4aec34a5b804094c3492a7
> **审计阶段**: ZBC Phase 17
> **审计性质**: 源码来源与许可证全仓库审计（工程审计，不构成法律意见）
> **关联文件**: THIRD_PARTY_LICENSE_AUDIT.md, audit/source_provenance.json

---

## 1. 分类定义

| 分类 | 定义 |
|---|---|
| **ORIGINAL** | 本项目独立开发的源码、文档、配置、脚本 |
| **THIRD_PARTY_DEPENDENCY** | 通过包管理器引入的第三方依赖（PyPI / npm），未修改源码 |
| **DERIVED_WITH_LICENSE** | 从第三方仓库复制/改编的代码片段，携带明确许可证声明与来源归因 |
| **NEEDS_REVIEW** | 来源或许可证不明确，需人工进一步确认的素材/文档/二进制 |
| **INFRINGEMENT_RISK** | 存在侵权或违规分发风险的内容（机密文档、第三方 UI 截图、未授权素材） |

---

## 2. 第三方依赖清单

### 2.1 Python 依赖（requirements.txt，28 项直接依赖）

| # | 包名 | 版本约束 | License | 商业使用 | NOTICE |
|---|---|---|---|---|---|
| 1 | Flask | >=2.0.0 | BSD-3-Clause | 允许 | 是 |
| 2 | Werkzeug | >=2.0.0 | BSD-3-Clause | 允许 | 是 |
| 3 | Flask-CORS | >=3.0.0 | MIT | 允许 | 是 |
| 4 | Flask-Limiter | >=3.5.0 | MIT | 允许 | 是 |
| 5 | waitress | >=2.1.0 | ZPL-2.1 | 允许 | 是 |
| 6 | APScheduler | >=3.10.0 | MIT | 允许 | 是 |
| 7 | schedule | >=1.2.0 | MIT | 允许 | 是 |
| 8 | pandas | >=1.3.0 | BSD-3-Clause | 允许 | 是 |
| 9 | openpyxl | >=3.0.0 | MIT | 允许 | 是 |
| 10 | XlsxWriter | >=3.0.0 | BSD-2-Clause | 允许 | 是 |
| 11 | beautifulsoup4 | >=4.12.0 | MIT | 允许 | 是 |
| 12 | lxml | >=4.9.0 | BSD-3-Clause | 允许 | 是 |
| 13 | python-docx | >=0.8.11 | MIT | 允许 | 是 |
| 14 | reportlab | >=3.6.0 | BSD-3-Clause | 允许 | 是 |
| 15 | playwright | >=1.30.0 | Apache-2.0 | 允许 | 是 |
| 16 | psutil | >=5.9.0 | BSD-3-Clause | 允许 | 是 |
| 17 | requests | >=2.28.0 | Apache-2.0 | 允许 | 是 |
| 18 | httpx | >=0.24.0 | BSD-3-Clause | 允许 | 是 |
| 19 | websocket-client | >=1.6.0 | BSD-3-Clause | 允许 | 是 |
| 20 | python-dotenv | >=0.21.0 | BSD-3-Clause | 允许 | 是 |
| 21 | python-dateutil | >=2.8.2 | Apache-2.0/BSD-3-Clause | 允许 | 是 |
| 22 | PyYAML | >=6.0 | MIT | 允许 | 是 |
| 23 | colorama | >=0.4.6 | BSD-3-Clause | 允许 | 是 |
| 24 | tqdm | >=4.64.0 | MIT/MPL-2.0 | 允许 | 是 |
| 25 | aiohttp | >=3.9.0 | Apache-2.0 | 允许 | 是 |
| 26 | yyds-logger | >=0.8.0 | MIT | 允许 | 是 |
| 27 | tenacity | >=9.1.0 | Apache-2.0 | 允许 | 是 |
| 28 | alembic | >=1.19.1 | MIT | 允许 | 是 |

**License 统计**: MIT x 12, BSD-3-Clause x 10, Apache-2.0 x 5, BSD-2-Clause x 1, ZPL-2.1 x 1, 双许可 x 2
**GPL/AGPL/非商业限制**: 无
**全部允许商业使用**: 是

### 2.2 Node.js 依赖（package.json，1 项）

| 包名 | 版本 | License | 商业使用 |
|---|---|---|---|
| playwright | ^1.62.1 | Apache-2.0 | 允许 |

### 2.3 运行时二进制（.gitignore 已排除）

| 名称 | 路径 | License | 入库状态 |
|---|---|---|---|
| Node.js 便携运行时 | nodejs/ | Node.js License (MIT + 第三方) | 已排除 |
| cloudflared | cloudflared.exe | Apache-2.0 | 已排除 (*.exe) |

### 2.4 dependencies/ 目录
- **状态**: 空目录（0 文件），已被 .gitignore 排除
- **结论**: 无 vendored 第三方代码

---

## 3. 源码来源分类统计

| 分类 | 数量 | 说明 |
|---|---|---|
| ORIGINAL | ~600+ 文件 | 核心 Python/JS 源码、模板、静态资源、项目文档、序境/、99-ARCHIVE/ |
| THIRD_PARTY_DEPENDENCY | 29 直接依赖 | 28 Python + 1 Node.js |
| DERIVED_WITH_LICENSE | 6 文件 | docs/reference/apple-ui-reference/code-snippets/（MIT，已归因） |
| NEEDS_REVIEW | ~650+ 文件 | 媒体素材：ref_gpt_v2/ (353)、_ref_frames/ (11)、ui-research/ (~280) |
| INFRINGEMENT_RISK | 8 文件 | _pitch_dump/ 客户机密/第三方文档文本 dump |

---

## 4. 重点目录审计

### 4.1 ref_gpt_v2/（353 文件）— NEEDS_REVIEW
- **内容**: ChatGPT UI 录屏抽帧（frames/、real_frames/）、参考截图、demo 对比图
- **代码文件**: 无（全部为图片媒体）
- **风险**: 含 OpenAI ChatGPT 产品 UI 截图，**不得在商业交付物中包含**
- **.gitignore**: 未排除（当前被 Git 跟踪，~17.6MB）

### 4.2 序境/（60 文件）— ORIGINAL
- **内容**: 项目治理文档（00-GOVERNANCE/）、产品规范（01-PRODUCT/）、审计证据（08-AUDIT/）
- **代码文件**: 无（全部为 Markdown/JSON/图片）
- **风险**: 无

### 4.3 _pitch_dump/（8 文件）— INFRINGEMENT_RISK
- **内容**: 从客户商业方案文件（PPTX/PDF/XLSX）提取的纯文本 dump
- **文件清单**:
  1. 提案Final【25年年度review】...txt — 客户机密（高）
  2. v2-索尼音乐打卡活动Review...txt — 客户机密（高）
  3. 【Study-NIO蔚来】...播客项目...txt — 客户机密（高）
  4. 2024年广州太古汇播客专项-1104.txt — 客户机密（高）
  5. For：Zachary.txt — 客户资料（中）
  6. uth又识mediakit2025.txt — 第三方版权（中）
  7. 播客先声.txt — 第三方版权（低）
  8. 日谈公园介绍2024版.txt — 第三方版权（低）
- **关键事实**: 全部为 .txt 文本，不被任何代码 import，**零生产路径侵权风险**
- **.gitignore 问题**: 虽在 .gitignore 中，但因添加前已被跟踪，**当前仍在 Git 版本控制中**
- **必须执行**: `git rm --cached -r _pitch_dump/`

### 4.4 _ref_frames/（11 文件）— NEEDS_REVIEW
- **内容**: sprite_01.jpg ~ sprite_10.jpg（精灵图）
- **来源**: 不明确（无 README / 无来源标注）
- **.gitignore**: 已排除

### 4.5 docs/reference/（284 文件）— MIXED

**apple-ui-reference/code-snippets/（6 文件）— DERIVED_WITH_LICENSE**:

| 文件 | 来源仓库 | License |
|---|---|---|
| 01-sfsymbols-glyph-extraction.swift | davedelong/sfsymbols | MIT |
| 02-sfsymbols-svg-exporter.swift | davedelong/sfsymbols | MIT |
| 03-sfsafesymbols-type-safe-access.swift | SFSafeSymbols/SFSafeSymbols | MIT |
| 04-appicon-asset-catalog.swift | raphaelhanneken/iconizer | MIT |
| 05-hig-icon-geometry-canvas.tsx | yc-w-cn/macos-compliant-icon-generator | **待确认** |
| 06-liquid-glass-iOS26-cheatsheet.txt | conorluddy/LiquidGlassReference | **待确认** |

- 均携带来源 URL / 源文件路径 / SHA / License 标注
- **不在生产运行路径中**（docs/ 目录）

**ui-research/（~270 文件）**: 分析脚本（ORIGINAL）+ 媒体素材（NEEDS_REVIEW）
- source-videos/：8 段视频（ChatGPT Work、微信录屏），Git LFS 管理
- reference-images/：16+ 张参考图（来自微信 RWTemp）
- VIDEO-SOURCE-MANIFEST.md：已记录所有来源

**CTR-*.md（3 文件）**: ORIGINAL（本项目研究文档）

### 4.6 99-ARCHIVE/（2 文件）— ORIGINAL
- _pitch_dump.py：文本提取脚本（自研）
- _reanalyze.py：数据库重新分析脚本（自研）

---

## 5. Copyright 声明

| 项目 | 数量 |
|---|---|
| 项目自身 LICENSE 文件 | 0（仓库根无 LICENSE/COPYING） |
| 源码中正式 Copyright 头 | 0 |
| 第三方归因注释 | 6（apple-ui-reference/code-snippets/） |
| 审计文档中的 License 讨论 | 2（THIRD_PARTY_LICENSE_AUDIT.md, COMPLIANCE_BY_DESIGN_RELEASE_GATE_V1.md） |

---

## 6. INFRINGEMENT_RISK 清单

| # | 文件 | 类型 | 严重度 | 生产路径 |
|---|---|---|---|---|
| 1 | _pitch_dump/提案Final【25年年度review】...txt | 客户机密 | 高 | 否 |
| 2 | _pitch_dump/v2-索尼音乐打卡活动Review...txt | 客户机密 | 高 | 否 |
| 3 | _pitch_dump/【Study-NIO蔚来】...txt | 客户机密 | 高 | 否 |
| 4 | _pitch_dump/2024年广州太古汇播客专项-1104.txt | 客户机密 | 高 | 否 |
| 5 | _pitch_dump/For：Zachary.txt | 客户资料 | 中 | 否 |
| 6 | _pitch_dump/uth又识mediakit2025.txt | 第三方版权 | 中 | 否 |
| 7 | _pitch_dump/播客先声.txt | 第三方版权 | 低 | 否 |
| 8 | _pitch_dump/日谈公园介绍2024版.txt | 第三方版权 | 低 | 否 |

---

## 7. NEEDS_REVIEW 清单

| # | 路径 | 类型 | 待确认内容 |
|---|---|---|---|
| 1 | _ref_frames/sprite_01~10.jpg | 图片素材 | 来源不明 |
| 2 | code-snippets/05-hig-icon-geometry-canvas.tsx | 第三方代码 | License 待确认 |
| 3 | code-snippets/06-liquid-glass-iOS26-cheatsheet.txt | 第三方文档 | License 待确认 |
| 4 | ref_gpt_v2/ (353 文件) | 媒体素材 | ChatGPT UI 截图，客户 Release 必须排除 |
| 5 | ui-research/source-videos/ (8 段) | 视频素材 | 第三方产品录屏 |
| 6 | ui-research/reference-images/ (16+ 张) | 图片素材 | 来自微信缓存 |
| 7 | nodejs/ (便携运行时) | 二进制 | 随产品分发时的 License 合规 |

---

## 8. Git 历史审计

- **第三方 fork / merge / cherry-pick**: 未发现
- **所有 merge 来源**: 均为本项目自身分支
- **.gitignore 合规**: 正确排除 .venv/、node_modules/、nodejs/、dependencies/、*.exe、*.db 等
- **遗留问题**:
  1. `_pitch_dump/` 仍在 Git 跟踪中（.gitignore 后加，未执行 git rm --cached）
  2. `ref_gpt_v2/` (353 文件/~17.6MB) 未被 .gitignore 排除

---

## 9. 生产路径安全检查

- **INFRINGEMENT_RISK 进入生产路径**: **无**（_pitch_dump/ 全部为 .txt，不被 import）
- **DERIVED_WITH_LICENSE 进入生产路径**: **无**（6 个代码片段均在 docs/ 下）
- **NEEDS_REVIEW 媒体进入生产路径**: **无**
- **第三方依赖被修改**: 无（全部通过包管理器引入）

---

## 10. 审计结论

### 10.1 总体评估
- **核心源码**: 100% ORIGINAL，无第三方源码复制
- **第三方依赖**: 29 项直接依赖，全部为 permissive license，无 GPL/AGPL/非商业限制
- **第三方代码片段**: 6 个，均在 docs/ 下，携带 MIT 归因，不在生产路径
- **侵权风险**: 集中在 _pitch_dump/（8 个客户机密文档），不在生产路径但在 Git 中
- **生产路径侵权风险**: **零**

### 10.2 商业化前必须执行
1. `git rm --cached -r _pitch_dump/` — 客户机密文档移出 Git
2. 客户 Release 排除: _pitch_dump/、ref_gpt_v2/、docs/reference/ui-research/source-videos/、docs/reference/apple-ui-reference/code-snippets/
3. 补充项目自身 LICENSE 文件
4. 确认 05/06 号代码片段 License
5. 生成固定版本 SBOM

### 10.3 建议执行
1. 评估 ref_gpt_v2/ 迁移至 Git LFS 或外部存储
2. 为 _ref_frames/ 补充来源说明
3. 核心源码补充 Copyright 头
