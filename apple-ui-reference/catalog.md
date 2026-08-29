# 参考仓库分类目录（36）

> Star / 更新时间为 2026-08-29 检索快照；`归档`=仓库已 archived。


## A. SF Symbols 系统图标（14）

| ID | 仓库 | 语言 | Star | 最近更新 | 归档 | 用途 |
|---|---|---|---:|---|:---:|---|
| A01 | [SFSafeSymbols/SFSafeSymbols](https://github.com/SFSafeSymbols/SFSafeSymbols) | Swift | 1890 | 2026-08-09 |  | 用类型安全枚举调用全部 SF Symbols，编译期校验图标名，覆盖 UIKit/SwiftUI/AppKit/AppIntents |
| A02 | [davedelong/sfsymbols](https://github.com/davedelong/sfsymbols) | Swift | 473 | 2026-08-06 | 是 | CoreText 从 SF Symbols 字体提取矢量 CGPath 并导出 SVG/PDF/PNG 的命令行工具，研究图标矢量结构的核心实现 |
| A03 | [lukepistrol/SFSymbolsMacro](https://github.com/lukepistrol/SFSymbolsMacro) | Swift | 203 | 2026-08-10 |  | Swift 宏方案：#SFSymbol("xmark") 编译期校验，Xcode 15+ 首选轻量方案 |
| A04 | [sparrowcode/SafeSFSymbols](https://github.com/sparrowcode/SafeSFSymbols) | Swift | 202 | 2026-08-14 |  | 按系统版本回退：高版本图标在低系统上安全降级并告警 |
| A05 | [robb/FolderIconGenerator](https://github.com/robb/FolderIconGenerator) | Swift | 195 | 2026-08-04 |  | 把 SF Symbol 渲染进 macOS 文件夹图标模板的生成器，学习系统图标合成 |
| A06 | [alessiorubicini/SFSymbolsPickerForSwiftUI](https://github.com/alessiorubicini/SFSymbolsPickerForSwiftUI) | Swift | 183 | 2026-08-18 |  | 可直接嵌入 App 的 SwiftUI 图标选择器组件（网格/分类/搜索） |
| A07 | [birkir/react-native-sfsymbols](https://github.com/birkir/react-native-sfsymbols) | Objective-C | 142 | 2026-06-14 |  | 跨平台栈调用原生 SF Symbols 的桥接实现，含 ObjC 原生侧代码 |
| A08 | [jaywcjlove/create-custom-symbols](https://github.com/jaywcjlove/create-custom-symbols) | Swift | 141 | 2026-08-18 |  | SVG 转自定义 SF Symbol 模板（含 regular/medium/large 三档图层对齐）的 macOS 工具 |
| A09 | [atrinh0/sfsymbols](https://github.com/atrinh0/sfsymbols) | Swift | 136 | 2026-04-19 |  | SwiftUI 实现的符号浏览/搜索 App，学习 LazyVGrid 图标陈列与分类筛选 |
| A10 | [cameronshemilt/MoreSFSymbols](https://github.com/cameronshemilt/MoreSFSymbols) | Swift | 130 | 2026-08-15 |  | 第三方补充符号包，学习自定义符号 SVG 模板规范与 SPM 分发 |
| A11 | [brendanballon/sfsymbols-svg](https://github.com/brendanballon/sfsymbols-svg) | Swift | 112 | 2026-08-27 |  | 已转好的全量 SVG 资源 + Swift 导出脚本，可直接作为图标素材库读取 |
| A12 | [simonbs/SFSymbols](https://github.com/simonbs/SFSymbols) | Swift | 89 | 2026-08-15 |  | 异步读取系统内置符号目录的 API + 选择器，无需内置任何资源 |
| A13 | [noahsark769/sfsymbols.com](https://github.com/noahsark769/sfsymbols.com) | JavaScript | 60 | 2026-07-06 |  | Web 端符号参考站源码，学习如何把符号目录做成可检索网页 |
| A14 | [menahishayan/HomeAssistant-Cupertino-Icons](https://github.com/menahishayan/HomeAssistant-Cupertino-Icons) | JavaScript | 226 | 2026-08-06 |  | 6000+ SF Symbols 的批量导出与命名映射脚本，最大规模的符号转存案例之一 |

## B. App 图标（资产/几何）（5）

| ID | 仓库 | 语言 | Star | 最近更新 | 归档 | 用途 |
|---|---|---|---:|---|:---:|---|
| B01 | [raphaelhanneken/iconizer](https://github.com/raphaelhanneken/iconizer) | Swift | 890 | 2026-07-10 |  | 一键生成全套 App 图标尺寸与 Contents.json 的原生 macOS 工具，含完整 idiom/scale 数据模型 |
| B02 | [aroundsketch/Apple-App-Icons](https://github.com/aroundsketch/Apple-App-Icons) | - | 60 | 2026-07-30 |  | iOS 系统 App 图标复刻素材（Sketch/SVG/PNG），研究官方图标的视觉构成 |
| B03 | [yc-w-cn/macos-compliant-icon-generator](https://github.com/yc-w-cn/macos-compliant-icon-generator) | TypeScript | 61 | 2026-08-15 |  | HIG 图标安全区代码化：1024 画布、832 内容(13/16)、22% 连续圆角，Web Canvas 实现 |
| B04 | [pawello2222/AppIconGenerator](https://github.com/pawello2222/AppIconGenerator) | Swift | 19 | 2026-03-25 |  | 直接用 SwiftUI View 代码绘制并导出 App 图标，适合程序化生成品牌图标 |
| B05 | [chris1111/SF-Symbols-Composer-PNG](https://github.com/chris1111/SF-Symbols-Composer-PNG) | - | 2 | 2026-08-27 |  | macOS 26 Tahoe 新 Icon Composer 工作流：用 SF Symbols 拼合多层图标并导出 PNG |

## C. Apple 风格 UI 设计系统与组件（7）

| ID | 仓库 | 语言 | Star | 最近更新 | 归档 | 用途 |
|---|---|---|---:|---|:---:|---|
| C01 | [jordansinger/SwiftUI-Kit](https://github.com/jordansinger/SwiftUI-Kit) | Swift | 2532 | 2026-08-27 |  | 苹果官方系统组件/交互的 SwiftUI 对照 demo，做原生 UI 时逐组件查写法 |
| C02 | [alexzhirkevich/compose-cupertino](https://github.com/alexzhirkevich/compose-cupertino) | Kotlin | 1650 | 2026-08-27 |  | 非苹果栈复刻 iOS 控件（开关/滑块/选择器/弹窗）的算法与绘制参考 |
| C03 | [xmartlabs/Eureka](https://github.com/xmartlabs/Eureka) | Swift | 11803 | 2026-08-25 |  | 复刻 iOS 设置页分组表单样式的经典库，行/选区/校验模型完整 |
| C04 | [Tencent/QMUI_iOS](https://github.com/Tencent/QMUI_iOS) | Objective-C | 7198 | 2026-08-22 |  | 大型 iOS UI 解决方案：导航/弹窗/控件/工具类，含大量对系统样式的对齐实现 |
| C05 | [NJHu/iOSProject](https://github.com/NJHu/iOSProject) | Objective-C | 5419 | 2026-08-16 |  | CoreGraphics 手绘图标/动画的海量 OC demo，适合研究 Quartz 2D 绘制 |
| C06 | [futuretap/InAppSettingsKit](https://github.com/futuretap/InAppSettingsKit) | Objective-C | 3216 | 2026-08-12 |  | 系统设置 App 样式的 in-app 设置框架，研究 iOS 设置页视觉规范 |
| C07 | [WillieWangWei/SwiftUI-Tutorials](https://github.com/WillieWangWei/SwiftUI-Tutorials) | Swift | 2454 | 2026-08-18 |  | 中文 SwiftUI 系统控件示例集，适合快速对照官方 API 用法 |

## D. iOS 26 Liquid Glass 液态玻璃（7）

| ID | 仓库 | 语言 | Star | 最近更新 | 归档 | 用途 |
|---|---|---|---:|---|:---:|---|
| D01 | [conorluddy/LiquidGlassReference](https://github.com/conorluddy/LiquidGlassReference) | - | 333 | 2026-08-27 |  | 最完整的 Liquid Glass 参考文档：材质变体/glassEffect/Container/morphing/UIKit/兼容/性能，直接喂给系统当知识库 |
| D02 | [ryanashcraft/FabBar](https://github.com/ryanashcraft/FabBar) | Swift | 343 | 2026-08-28 |  | 高保真复刻 iOS 26 液态玻璃 TabBar 的可运行代码 |
| D03 | [Prisma-Labs-Dev/apple-skills](https://github.com/Prisma-Labs-Dev/apple-skills) | TypeScript | 323 | 2026-08-28 |  | 结构化的 iOS 26 API/Liquid Glass 知识库（面向 AI 编码代理），可直接当参考库 |
| D04 | [GonzaloFuentes28/LiquidGlassCheatsheet](https://github.com/GonzaloFuentes28/LiquidGlassCheatsheet) | - | 211 | 2026-08-20 |  | 液态玻璃实现速查表，偏代码片段与迁移步骤 |
| D05 | [youshen2/MeloX](https://github.com/youshen2/MeloX) | Swift | 203 | 2026-08-29 |  | 完整生产级 App 中落地液态玻璃与 Apple Music 风格图标的真实案例 |
| D06 | [mertozseven/LiquidGlassSwiftUI](https://github.com/mertozseven/LiquidGlassSwiftUI) | Swift | 60 | 2026-08-01 |  | 最小可运行的玻璃材质/符号过渡动画示例 |
| D07 | [muhittincamdali/SwiftUI-iOS26-Showcase](https://github.com/muhittincamdali/SwiftUI-iOS26-Showcase) | Swift | 16 | 2026-08-27 |  | 50+ 个 iOS 26 新 API 单点 demo，按需查阅 |

## E. 综合索引（3）

| ID | 仓库 | 语言 | Star | 最近更新 | 归档 | 用途 |
|---|---|---|---:|---|:---:|---|
| E01 | [vsouza/awesome-ios](https://github.com/vsouza/awesome-ios) | Swift | 53198 | 2026-08-29 |  | iOS 生态总索引，需要更多 UI/图标库时从这里按类目下钻 |
| E02 | [matteocrippa/awesome-swift](https://github.com/matteocrippa/awesome-swift) | Ruby | 26232 | 2026-08-28 |  | Swift 库总索引（UI / Images / 组件分类） |
| E03 | [Blackjacx/WWDC](https://github.com/Blackjacx/WWDC) | Shell | 2596 | 2026-08-28 |  | 历年 WWDC 设计与 SwiftUI session 文字精要，追官方设计口径 |

## 本地代码样本

| 文件 | 对应仓库 | 内容 |
|---|---|---|
| `code-snippets/01-sfsymbols-glyph-extraction.swift` | A02 davedelong/sfsymbols | CoreText 按字形名提取 CGPath 矢量路径与元数据 |
| `code-snippets/02-sfsymbols-svg-exporter.swift` | A02 davedelong/sfsymbols | CGPath 元素转标准 SVG path（含 y 轴翻转） |
| `code-snippets/03-sfsafesymbols-type-safe-access.swift` | A01 SFSafeSymbols | UIImage/Image 类型安全初始化器与可变值图标 |
| `code-snippets/04-appicon-asset-catalog.swift` | B01 raphaelhanneken/iconizer | AppIcon 多 idiom/scale 模型与 1024 无 alpha 规则 |
| `code-snippets/05-hig-icon-geometry-canvas.tsx` | B03 yc-w-cn/macos-compliant-icon-generator | 1024 画布/832 内容(13/16)/22% 连续圆角 Canvas 实现 |
| `code-snippets/06-liquid-glass-iOS26-cheatsheet.txt` | D01 conorluddy/LiquidGlassReference | iOS26 glassEffect 全量 API、模式、兼容与规则 |
