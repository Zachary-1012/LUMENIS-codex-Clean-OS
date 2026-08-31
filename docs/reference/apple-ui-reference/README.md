# 苹果应用及系统图标 UI 设计 · GitHub 参考数据库

> 生成时间：2026-08-29（Asia/Shanghai）
> 数据来源：GitHub Search/Repositories + Contents API 实时检索（github-remote）
> 用途：作为本地系统的**参考知识库**，后续可由系统/Agent 直接读取 `apple-ui-reference-db.json` 调用。

---

## 1. 目录结构

```
apple-ui-reference/
├── README.md                      # 本文件：说明与调用方式
├── catalog.md                     # 36 个仓库的人类可读分类清单（表格）
├── apple-ui-reference-db.json     # ★ 结构化数据库（机器可读，系统调用入口）
├── code-snippets/                 # 从核心仓库抽取的真实源码样本（已核对 SHA）
│   ├── 01-sfsymbols-glyph-extraction.swift     # SF Symbols 字体→矢量路径
│   ├── 02-sfsymbols-svg-exporter.swift         # 矢量路径→SVG
│   ├── 03-sfsafesymbols-type-safe-access.swift # 类型安全调用系统图标
│   ├── 04-appicon-asset-catalog.swift          # 全套 App 图标尺寸模型
│   ├── 05-hig-icon-geometry-canvas.tsx         # HIG 13/16 安全区 + 22% 圆角
│   └── 06-liquid-glass-iOS26-cheatsheet.txt    # iOS 26 液态玻璃 API 速查
└── raw/
    ├── build_db.py                # 数据库生成脚本（可重跑/增量更新）
    └── _raw_search_iosicons.json  # 一次原始检索结果留档
```

## 2. 数据库怎么被系统调用

主文件：`apple-ui-reference-db.json`

- 顶层 `records[]`，共 **36** 条，每条是一个 GitHub 参考仓库。
- 字段说明：

| 字段 | 含义 |
|---|---|
| `id` | 分类内编号（A01…E03） |
| `category` | 五大分类之一，见 `category_legend` |
| `full_name` / `owner` / `name` | GitHub 仓库坐标 |
| `html_url` / `clone_url` / `api_repos_url` | 网页 / git clone / REST API 三种链接 |
| `language` | 主语言（Swift / Objective-C / TypeScript / Kotlin / JS） |
| `stars_at_2026_08_29` | 检索时刻 star 快照（实时值以 API 为准） |
| `last_pushed_at` | 最近推送时间，判断维护活跃度 |
| `archived` | 是否已归档（true 表示只读、不再维护，但代码仍可参考） |
| `use_case` | **面向调用方的一句话用途**（系统选型时优先读它） |
| `verified_key_paths` | 已通过 Contents API 实际核对过的关键文件/目录路径，可直接拼接读取 |
| `local_snippet` | 对应的本地代码样本路径（如有） |
| `tags` | 检索标签 |

调用示例（Python）：

```python
import json, os
db = json.load(open("apple-ui-reference-db.json", encoding="utf-8"))
# 1) 找"系统图标矢量导出"相关仓库
hits = [r for r in db["records"] if "svg-export" in r["tags"]]
# 2) 取某仓库的关键文件直链
r = next(x for x in db["records"] if x["id"] == "A02")
for p in r["verified_key_paths"]:
    print(f'{r["html_url"]}/blob/{p}')
# 3) 只看 2026 年仍活跃、未归档的高相关项目
active = [r for r in db["records"] if not r["archived"] and r["last_pushed_at"] >= "2026-07"]
```

需要**拉取源码到本地**时：对目标记录执行
`git clone --depth 1 <clone_url>`（浅克隆即可，体积小）。

## 3. 五大分类

| 分类 | 数量 | 覆盖内容 |
|---|---:|---|
| A. SF Symbols 系统图标 | 14 | 类型安全调用、从字体提取矢量路径、SVG/PNG/PDF 导出、符号选择器 UI、RN/跨平台桥接、自定义符号 |
| B. App 图标 | 5 | 全套尺寸与 Asset Catalog 生成、HIG 安全区（13/16=832/1024）与连续圆角几何、Tahoe Icon Composer |
| C. Apple 风格 UI 设计系统/组件 | 7 | SwiftUI/UIKit 系统组件对照、Cupertino 跨平台复刻、设置页样式、CoreGraphics 手绘 |
| D. iOS 26 Liquid Glass | 7 | WWDC2025 液态玻璃新设计语言：glassEffect、Container、morphing、UIKit、向后兼容（最新时效内容） |
| E. 综合索引 | 3 | awesome-ios / awesome-swift / WWDC 笔记，用于继续扩展 |

## 4. 选型建议（按需求场景）

- **在 App 里用系统图标，怕拼错名字** → A01 SFSafeSymbols（或 A03 Swift Macro）
- **想把 SF Symbols 批量导成 SVG/PNG 做素材** → A02 davedelong/sfsymbols + A11 sfsymbols-svg（导出脚本样本见 code-snippets 01/02）
- **需要一个图标选择界面** → A06 SFSymbolsPickerForSwiftUI / A12 simonbs/SFSymbols
- **生成 App 全套尺寸图标** → B01 iconizer（样本 04）；**用代码画图标** → B04 AppIconGenerator
- **图标圆角/安全区不合规被驳回** → B03（样本 05，硬编码 1024/832/22% 规则）
- **做 iOS 26 最新液态玻璃风格** → D01 参考文档（样本 06）+ D02 TabBar 复刻 + D05 完整 App 案例
- **非苹果技术栈要复刻 iOS 观感** → C02 compose-cupertino（Kotlin）/ A07 react-native-sfsymbols

## 5. 苹果官方一手参考（非 GitHub，务必同时对照）

- SF Symbols 总览：https://developer.apple.com/design/human-interface-guidelines/sf-symbols
- SF Symbols App 下载：https://developer.apple.com/sf-symbols/
- App 图标 HIG：https://developer.apple.com/design/human-interface-guidelines/app-icons
- Materials（材质/液态玻璃）HIG：https://developer.apple.com/design/human-interface-guidelines/materials
- Liquid Glass 文档：https://developer.apple.com/documentation/TechnologyOverviews/liquid-glass
- Apple Design Resources（Figma 官方设计套件）：见 db.json 的 `official_reference_urls`

> 注意：SF Symbols 字体与符号本身受 Apple 许可约束，**只能在 Apple 平台 App 内按系统 API 使用**，导出 SVG 仅可用于设计/开发参考，不能作为自有素材对外分发商用。

## 6. 更新方式

- 重跑 `raw/build_db.py` 可重建 JSON（修改其中记录即可增删）。
- star 数、最近更新时间会变化，需要刷新时用 GitHub API：
  `GET https://api.github.com/repos/<owner>/<repo>`。
- 扩展新仓库的检索式示例：`topic:sf-symbols`、`sfsymbols in:name`、`liquid glass ios 26 swiftui`、`app icon generator swift`。

## 7. 采集与核对说明

- 所有仓库均来自 2026-08-29 当天的实时检索结果，未凭记忆编造；star 数与更新时间为当天快照。
- 标注 `verified_key_paths` 的路径均通过 Contents API 实际列目录/读文件核对。
- `code-snippets/` 中每份样本顶部都标注了来源仓库、原始文件路径与读取时的 commit SHA，便于回溯。
- GitHub 代码全局搜索（search_code）在采集期间一度服务异常，故代码级样本以「选定核心仓库→直接读文件」方式获取，不影响结论可靠性。
