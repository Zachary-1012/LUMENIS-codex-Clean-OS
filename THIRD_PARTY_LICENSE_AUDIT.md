# 第三方代码 / 许可证审计基线---仅为参考以实际开发进度，本地唯一路径：D:\LUMENIS_REBUILD、线上唯一主线main，为准，并按照标准在每轮任务完成后进行更新

> 审计日期：2026-08-30
> 仓库：Zachary-1012/Z-Brand-Core
>
> 本文件用于商业化前的工程审计，不构成法律意见。最终商业授权判断应以各依赖的实际许可证、版本、发布包及律师意见为准。

## 1. 本仓库自研代码原则

Z-Brand-Core 的业务核心、平台适配边界、广州太古汇主体口径、风险/事件/报告逻辑和本次新增 Adapter Foundation 均按本项目需求独立开发。

本次研究 MediaCrawler 时，**不复制其源码、文件或受限实现**。仅参考公开的架构组织方式和功能边界，并重新设计本项目自己的接口。

## 2. MediaCrawler 明确排除

MediaCrawler 当前文件明确标注 `NON-COMMERCIAL LEARNING LICENSE 1.1`；其许可证允许的范围是非商业学习目的，并明确禁止未经书面同意的商业用途。其源码文件也重复携带该许可证声明。

因此：

- 不将 MediaCrawler 作为 Z-Brand-Core 的运行时依赖。
- 不复制 MediaCrawler 的 `.py` 文件、核心实现、注释头或其特有实现。
- 不把 MediaCrawler 的非商业许可证声明伪装成 Z-Brand-Core 的许可。
- 如未来确需使用其代码，必须先取得明确的书面商业授权，并重新进行许可证审计。

## 3. 普通第三方依赖

项目可以使用正常的开源依赖，例如 Flask、Playwright、requests、APScheduler、openpyxl、Pillow 等，但“依赖使用”和“复制第三方源码”必须严格区分。

商业发布前必须锁定实际版本，并为最终构建产物生成依赖清单及对应许可证清单。

## 4. 商业化前必须执行

1. 导出 `requirements.txt` / lock 文件中的全部直接及间接依赖。
2. 对每个实际安装版本确认许可证。
3. 检查是否存在 GPL/AGPL/非商业/研究用途/附加商业限制。
4. 检查仓库中是否误提交第三方源码、二进制、模型权重或带限制条款的示例数据。
5. 检查 NOTICE/COPYRIGHT 要求并在发行包中保留必要声明。
6. 检查所有平台的服务条款、机器人规则、开放接口授权和数据使用边界。
7. 商业客户交付前生成一份固定版本的 SBOM/依赖清单。

## 5. 自动化审计红线

豆包或其他代码代理不得：

- 为了实现功能而直接复制第三方仓库文件。
- 删除第三方许可证头来规避授权要求。
- 将非商业代码改名后当作自研代码。
- 自动引入未经许可证检查的爬虫项目。
- 将 Cookie、Session、代理认证、API Key、个人数据提交到 GitHub。

## 6. 审计结论（当前基线）

**当前开发路线：可以继续按自研 Adapter + 正常开源依赖的方式推进。**

但本文件不宣称“已经完成全仓库法律级许可证审计”。在真正商业化发布前，应完成一次基于最终锁定依赖版本和最终源码树的完整扫描。

---

## 7. Phase 17 全仓库源码来源审计补充（2026-09-06）

> 本次审计为 ZBC Phase 17 - Source Provenance / License Audit 的工程级补充。
> 完整报告见 `audit/SOURCE-PROVENANCE-AUDIT.md`，机器可读数据见 `audit/source_provenance.json`。

### 7.1 Python 依赖 License 全量清单（28 项直接依赖）

| 包名 | License | 商业使用 | NOTICE 要求 |
|---|---|---|---|
| Flask | BSD-3-Clause | 允许 | 是 |
| Werkzeug | BSD-3-Clause | 允许 | 是 |
| Flask-CORS | MIT | 允许 | 是 |
| Flask-Limiter | MIT | 允许 | 是 |
| waitress | ZPL-2.1 | 允许 | 是 |
| APScheduler | MIT | 允许 | 是 |
| schedule | MIT | 允许 | 是 |
| pandas | BSD-3-Clause | 允许 | 是 |
| openpyxl | MIT | 允许 | 是 |
| XlsxWriter | BSD-2-Clause | 允许 | 是 |
| beautifulsoup4 | MIT | 允许 | 是 |
| lxml | BSD-3-Clause | 允许 | 是 |
| python-docx | MIT | 允许 | 是 |
| reportlab | BSD-3-Clause | 允许 | 是 |
| playwright | Apache-2.0 | 允许 | 是 |
| psutil | BSD-3-Clause | 允许 | 是 |
| requests | Apache-2.0 | 允许 | 是 |
| httpx | BSD-3-Clause | 允许 | 是 |
| websocket-client | BSD-3-Clause | 允许 | 是 |
| python-dotenv | BSD-3-Clause | 允许 | 是 |
| python-dateutil | Apache-2.0 / BSD-3-Clause | 允许 | 是 |
| PyYAML | MIT | 允许 | 是 |
| colorama | BSD-3-Clause | 允许 | 是 |
| tqdm | MIT / MPL-2.0 | 允许 | 是 |
| aiohttp | Apache-2.0 | 允许 | 是 |
| yyds-logger | MIT | 允许 | 是 |
| tenacity | Apache-2.0 | 允许 | 是 |
| alembic | MIT | 允许 | 是 |

**License 统计**: MIT x 12, BSD-3-Clause x 10, Apache-2.0 x 5, BSD-2-Clause x 1, ZPL-2.1 x 1, 双许可 x 2
**GPL/AGPL/非商业限制**: 无
**全部允许商业使用**: 是

### 7.2 Node.js 依赖（1 项直接依赖）

| 包名 | License | 商业使用 | NOTICE 要求 |
|---|---|---|---|
| playwright (npm) | Apache-2.0 | 允许 | 是 |

### 7.3 运行时二进制（工作目录存在，.gitignore 已排除）

| 名称 | License | 入库状态 |
|---|---|---|
| Node.js 便携运行时 (nodejs/) | Node.js License (MIT + 第三方) | 已排除 |
| cloudflared.exe | Apache-2.0 | 已排除 (*.exe) |

### 7.4 第三方代码片段（DERIVED_WITH_LICENSE，6 项）

均位于 `docs/reference/apple-ui-reference/code-snippets/`，携带来源 URL / 源文件路径 / SHA / License 标注，**不在生产运行路径中**。

| 文件 | 来源仓库 | License |
|---|---|---|
| 01-sfsymbols-glyph-extraction.swift | davedelong/sfsymbols | MIT |
| 02-sfsymbols-svg-exporter.swift | davedelong/sfsymbols | MIT |
| 03-sfsafesymbols-type-safe-access.swift | SFSafeSymbols/SFSafeSymbols | MIT |
| 04-appicon-asset-catalog.swift | raphaelhanneken/iconizer | MIT |
| 05-hig-icon-geometry-canvas.tsx | yc-w-cn/macos-compliant-icon-generator | **待确认** |
| 06-liquid-glass-iOS26-cheatsheet.txt | conorluddy/LiquidGlassReference | **待确认** |

### 7.5 INFRINGEMENT_RISK 模块（8 项，均在 _pitch_dump/）

| 文件 | 类型 | 严重度 | 生产路径 |
|---|---|---|---|
| 提案Final【25年年度review】...txt | 客户机密 | 高 | 否 |
| v2-索尼音乐打卡活动Review...txt | 客户机密 | 高 | 否 |
| 【Study-NIO蔚来】...播客项目...txt | 客户机密 | 高 | 否 |
| 2024年广州太古汇播客专项-1104.txt | 客户机密 | 高 | 否 |
| For：Zachary.txt | 客户资料 | 中 | 否 |
| uth又识mediakit2025.txt | 第三方版权 | 中 | 否 |
| 播客先声.txt | 第三方版权 | 低 | 否 |
| 日谈公园介绍2024版.txt | 第三方版权 | 低 | 否 |

**关键事实**: 以上 8 项均为 .txt 文本 dump，不被任何 Python/JS 代码 import，**零生产路径侵权风险**。但 `_pitch_dump/` 虽在 .gitignore 中，因添加前已被跟踪，**当前仍在 Git 版本控制中**。商业化前必须执行 `git rm --cached -r _pitch_dump/`。

### 7.6 源码来源分类统计

| 分类 | 数量 | 说明 |
|---|---|---|
| ORIGINAL | ~600+ 文件 | 核心源码、模板、静态资源、项目文档 |
| THIRD_PARTY_DEPENDENCY | 29 直接依赖 | 28 Python + 1 Node.js |
| DERIVED_WITH_LICENSE | 6 文件 | apple-ui-reference 代码片段（MIT） |
| NEEDS_REVIEW | ~650+ 文件 | 媒体素材（ref_gpt_v2/、_ref_frames/、ui-research/） |
| INFRINGEMENT_RISK | 8 文件 | _pitch_dump/ 客户机密文档 |

### 7.7 Git 历史审计结论

- 未发现从第三方仓库 fork / merge / cherry-pick 的提交
- 所有 merge 均来自本项目自身分支
- .gitignore 正确排除了 .venv/、node_modules/、nodejs/、dependencies/、*.exe、*.db 等
- 唯一遗留问题：`_pitch_dump/` 仍在 Git 跟踪中

### 7.8 商业化前必须执行

1. `git rm --cached -r _pitch_dump/` — 客户机密文档移出 Git
2. 客户 Release 排除: `_pitch_dump/`、`ref_gpt_v2/`、`docs/reference/ui-research/source-videos/`、`docs/reference/apple-ui-reference/code-snippets/`
3. 补充项目自身 LICENSE 文件
4. 确认 05/06 号代码片段 License
5. 生成固定版本 SBOM
