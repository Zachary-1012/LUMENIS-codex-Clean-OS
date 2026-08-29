# -*- coding: utf-8 -*-
"""生成苹果应用/系统图标 UI 设计参考数据库 JSON。数据来自 2026-08-29 GitHub 实时检索。"""
import json, hashlib, os

BASE = r"C:\Users\28049\Doubao\chats\2026-08-29\new-chat-2\apple-ui-reference"

def rec(rid, cat, full, lang, stars, updated, desc, use, paths=None, tags=None, archived=False, snippet=None):
    owner, name = full.split("/", 1)
    return {
        "id": rid,
        "category": cat,
        "full_name": full,
        "owner": owner,
        "name": name,
        "html_url": f"https://github.com/{full}",
        "clone_url": f"https://github.com/{full}.git",
        "api_repos_url": f"https://api.github.com/repos/{full}",
        "language": lang,
        "stars_at_2026_08_29": stars,
        "last_pushed_at": updated,
        "archived": archived,
        "description": desc,
        "use_case": use,
        "verified_key_paths": paths or [],
        "local_snippet": snippet,
        "tags": tags or [],
    }

records = []

# ============ A. SF Symbols 系统图标 ============
A = "A_sf_symbols_system_icons"
records += [
 rec("A01", A, "SFSafeSymbols/SFSafeSymbols", "Swift", 1890, "2026-08-09",
     "Safely access Apple's SF Symbols using static typing",
     "用类型安全枚举调用全部 SF Symbols，编译期校验图标名，覆盖 UIKit/SwiftUI/AppKit/AppIntents",
     ["Sources/SFSafeSymbols/Symbols/", "Sources/SFSafeSymbols/SymbolImages/",
      "Sources/SFSafeSymbols/Initializers/UIKit/UIImage+SFSymbol.swift",
      "Sources/SFSafeSymbols/Initializers/SwiftUI/", "Sources/SFSafeSymbols/Initializers/AppKit/",
      "SymbolsGenerator/", "Package.swift"],
     ["sfsymbols","type-safe","uikit","swiftui","appkit","codegen"],
     snippet="code-snippets/03-sfsafesymbols-type-safe-access.swift"),
 rec("A02", A, "davedelong/sfsymbols", "Swift", 473, "2026-08-06",
     "Export the shapes in the SF Symbols font (SVG/PNG/PDF/iconset)",
     "CoreText 从 SF Symbols 字体提取矢量 CGPath 并导出 SVG/PDF/PNG 的命令行工具，研究图标矢量结构的核心实现",
     ["Sources/sfsymbols/", "Sources/SFSymbolsCore/Glyph.swift",
      "Sources/SFSymbolsCore/Font.swift", "Sources/SFSymbolsCore/Font+Discovery.swift",
      "Sources/SFSymbolsCore/Exporter.swift",
      "Sources/SFSymbolsCore/Exporters/SVGExporter.swift",
      "Sources/SFSymbolsCore/Exporters/PNGExporter.swift",
      "Sources/SFSymbolsCore/Exporters/PDFExporter.swift",
      "Sources/SFSymbolsCore/Exporters/iOSExporter.swift",
      "Sources/SFSymbolsCore/Exporters/macOSExporter.swift", "Package.swift"],
     ["coretext","cgpath","svg-export","font","vector"], True,
     snippet="code-snippets/01-sfsymbols-glyph-extraction.swift"),
 rec("A03", A, "lukepistrol/SFSymbolsMacro", "Swift", 203, "2026-08-10",
     "A Swift Macro for type-safe SF Symbols",
     "Swift 宏方案：#SFSymbol(\"xmark\") 编译期校验，Xcode 15+ 首选轻量方案",
     [], ["swift-macro","type-safe","xcode15"]),
 rec("A04", A, "sparrowcode/SafeSFSymbols", "Swift", 202, "2026-08-14",
     "Safe access SFSymbols. If symbol not available, will show warning",
     "按系统版本回退：高版本图标在低系统上安全降级并告警",
     [], ["availability","fallback","uikit","swiftui"]),
 rec("A05", A, "robb/FolderIconGenerator", "Swift", 195, "2026-08-04",
     "Generate macOS folder icons from SF Symbols",
     "把 SF Symbol 渲染进 macOS 文件夹图标模板的生成器，学习系统图标合成",
     [], ["macos","folder-icon","generator"]),
 rec("A06", A, "alessiorubicini/SFSymbolsPickerForSwiftUI", "Swift", 183, "2026-08-18",
     "A customizable SwiftUI component for picking Apple's SF Symbols",
     "可直接嵌入 App 的 SwiftUI 图标选择器组件（网格/分类/搜索）",
     [], ["picker","swiftui-component","icons-grid"]),
 rec("A07", A, "birkir/react-native-sfsymbols", "Objective-C", 142, "2026-06-14",
     "SF Symbols in your iOS app (React Native bridge)",
     "跨平台栈调用原生 SF Symbols 的桥接实现，含 ObjC 原生侧代码",
     [], ["react-native","bridge","objective-c"]),
 rec("A08", A, "jaywcjlove/create-custom-symbols", "Swift", 141, "2026-08-18",
     "Convert any SVG icon into a custom SF symbol importable in Xcode",
     "SVG 转自定义 SF Symbol 模板（含 regular/medium/large 三档图层对齐）的 macOS 工具",
     ["README.md","README.zh.md","docs/","assets/"], ["svg-convert","custom-symbol","macos-app","swiftui"]),
 rec("A09", A, "atrinh0/sfsymbols", "Swift", 136, "2026-04-19",
     "SwiftUI app to search and showcase SF Symbols",
     "SwiftUI 实现的符号浏览/搜索 App，学习 LazyVGrid 图标陈列与分类筛选",
     [], ["swiftui-app","search","showcase"]),
 rec("A10", A, "cameronshemilt/MoreSFSymbols", "Swift", 130, "2026-08-15",
     "A collection of additional custom SFSymbols for Swift",
     "第三方补充符号包，学习自定义符号 SVG 模板规范与 SPM 分发",
     [], ["custom-icons","spm","extension-pack"]),
 rec("A11", A, "brendanballon/sfsymbols-svg", "Swift", 112, "2026-08-27",
     "Apple's SF Symbols in .svg format compiled into one place",
     "已转好的全量 SVG 资源 + Swift 导出脚本，可直接作为图标素材库读取",
     ["scripts/export_sf_symbols.swift","symbols/","README.md"], ["svg-assets","batch-export"]),
 rec("A12", A, "simonbs/SFSymbols", "Swift", 89, "2026-08-15",
     "Ready-to-use symbol picker for SwiftUI and async API for the system SF Symbols catalog",
     "异步读取系统内置符号目录的 API + 选择器，无需内置任何资源",
     [], ["system-catalog","async-api","picker"]),
 rec("A13", A, "noahsark769/sfsymbols.com", "JavaScript", 60, "2026-07-06",
     "SF Symbols reference site",
     "Web 端符号参考站源码，学习如何把符号目录做成可检索网页",
     [], ["web","reference-site","javascript"]),
 rec("A14", A, "menahishayan/HomeAssistant-Cupertino-Icons", "JavaScript", 226, "2026-08-06",
     "Apple SF Symbols icons for Home Assistant (6000+ icons)",
     "6000+ SF Symbols 的批量导出与命名映射脚本，最大规模的符号转存案例之一",
     [], ["bulk-export","mapping","home-assistant"]),
]

# ============ B. App 图标（主屏幕/资产目录/HIG 几何） ============
B = "B_app_icons_asset_geometry"
records += [
 rec("B01", B, "raphaelhanneken/iconizer", "Swift", 890, "2026-07-10",
     "Create Xcode asset catalogs: generate macOS/iOS app icons, launch images, image sets",
     "一键生成全套 App 图标尺寸与 Contents.json 的原生 macOS 工具，含完整 idiom/scale 数据模型",
     ["Iconizer/Models/AppIcon.swift","Iconizer/Models/AssetCatalog.swift",
      "Iconizer/Models/ImageSet.swift","Iconizer/Models/LaunchImage.swift",
      "Iconizer/Models/iMessageIcon.swift","Iconizer/Controller/","Iconizer/Helper/","Iconizer/Views/"],
     ["xcassets","appicon","multi-size","contents.json"],
     snippet="code-snippets/04-appicon-asset-catalog.swift"),
 rec("B02", B, "aroundsketch/Apple-App-Icons", None, 60, "2026-07-30",
     "Apple App Icons Sketch file + SVG/PNG/PDF (iOS 13 era system app icons)",
     "iOS 系统 App 图标复刻素材（Sketch/SVG/PNG），研究官方图标的视觉构成",
     [], ["sketch","svg","png","system-app-replica"]),
 rec("B03", B, "yc-w-cn/macos-compliant-icon-generator", "TypeScript", 61, "2026-08-15",
     "按 HIG / App Icons and Images / Apple Design Resources 把满版图转为合规图标(13/16)",
     "HIG 图标安全区代码化：1024 画布、832 内容(13/16)、22% 连续圆角，Web Canvas 实现",
     ["src/components/ImageUploader.tsx","src/lib/contants.ts","src/lib/utils.ts",
      "src/app/","src/components/ui/","README.md"],
     ["hig","safe-area","continuous-corner","canvas","13/16"],
     snippet="code-snippets/05-hig-icon-geometry-canvas.tsx"),
 rec("B04", B, "pawello2222/AppIconGenerator", "Swift", 19, "2026-03-25",
     "A library for creating App Icons from SwiftUI views",
     "直接用 SwiftUI View 代码绘制并导出 App 图标，适合程序化生成品牌图标",
     [], ["swiftui-render","programmatic-icon","spm"]),
 rec("B05", B, "chris1111/SF-Symbols-Composer-PNG", None, 2, "2026-08-27",
     "Create Icon from Symbols with Icon Composer (Tahoe icons)",
     "macOS 26 Tahoe 新 Icon Composer 工作流：用 SF Symbols 拼合多层图标并导出 PNG",
     [], ["icon-composer","tahoe","layered-icon"]),
]

# ============ C. Apple 风格 UI 设计系统与组件 ============
C = "C_apple_style_ui_design_systems"
records += [
 rec("C01", C, "jordansinger/SwiftUI-Kit", "Swift", 2532, "2026-08-27",
     "A SwiftUI system components and interactions demo app",
     "苹果官方系统组件/交互的 SwiftUI 对照 demo，做原生 UI 时逐组件查写法",
     [], ["swiftui","components","interactions","demo"]),
 rec("C02", C, "alexzhirkevich/compose-cupertino", "Kotlin", 1650, "2026-08-27",
     "Compose Multiplatform UI components for iOS (Cupertino Widgets)",
     "非苹果栈复刻 iOS 控件（开关/滑块/选择器/弹窗）的算法与绘制参考",
     [], ["kotlin","compose-multiplatform","cupertino","cross-platform"]),
 rec("C03", C, "xmartlabs/Eureka", "Swift", 11803, "2026-08-25",
     "Elegant iOS form builder in Swift",
     "复刻 iOS 设置页分组表单样式的经典库，行/选区/校验模型完整",
     [], ["form","uitableview","settings-style"]),
 rec("C04", C, "Tencent/QMUI_iOS", "Objective-C", 7198, "2026-08-22",
     "QMUI iOS——提高项目 UI 开发效率的解决方案",
     "大型 iOS UI 解决方案：导航/弹窗/控件/工具类，含大量对系统样式的对齐实现",
     [], ["uikit","components","solution","objective-c"]),
 rec("C05", C, "NJHu/iOSProject", "Objective-C", 5419, "2026-08-16",
     "iOS demo 合集：CoreAnimation/CoreGraphics 绘图、RunLoop、runtime 等",
     "CoreGraphics 手绘图标/动画的海量 OC demo，适合研究 Quartz 2D 绘制",
     [], ["coregraphics","coreanimation","drawrect","demo-collection"]),
 rec("C06", C, "futuretap/InAppSettingsKit", "Objective-C", 3216, "2026-08-12",
     "This iOS framework allows settings to be in-app in addition to or instead of the Settings app",
     "系统设置 App 样式的 in-app 设置框架，研究 iOS 设置页视觉规范",
     [], ["settings","uikit-components","in-app"]),
 rec("C07", C, "WillieWangWei/SwiftUI-Tutorials", "Swift", 2454, "2026-08-18",
     "SwiftUI 示例与中文翻译教程项目",
     "中文 SwiftUI 系统控件示例集，适合快速对照官方 API 用法",
     [], ["swiftui","tutorial","chinese","examples"]),
]

# ============ D. iOS 26 Liquid Glass 最新设计语言 ============
D = "D_ios26_liquid_glass"
records += [
 rec("D01", D, "conorluddy/LiquidGlassReference", None, 333, "2026-08-27",
     "iOS 26 Liquid Glass: Ultimate Swift/SwiftUI Reference",
     "最完整的 Liquid Glass 参考文档：材质变体/glassEffect/Container/morphing/UIKit/兼容/性能，直接喂给系统当知识库",
     ["README.md"], ["ios26","liquid-glass","swiftui","reference","hig"],
     snippet="code-snippets/06-liquid-glass-iOS26-cheatsheet.txt"),
 rec("D02", D, "ryanashcraft/FabBar", "Swift", 343, "2026-08-28",
     "A faithful recreation of the iOS 26 Liquid Glass tab bar with FAB",
     "高保真复刻 iOS 26 液态玻璃 TabBar 的可运行代码",
     [], ["tabbar","fab","recreation","uikit"]),
 rec("D03", D, "Prisma-Labs-Dev/apple-skills", "TypeScript", 323, "2026-08-28",
     "Apple development skills: latest iOS 26+ APIs, SwiftUI, Liquid Glass",
     "结构化的 iOS 26 API/Liquid Glass 知识库（面向 AI 编码代理），可直接当参考库",
     [], ["ios26","api-knowledge","agent-skills"]),
 rec("D04", D, "GonzaloFuentes28/LiquidGlassCheatsheet", None, 211, "2026-08-20",
     "CheatSheet on how to implement Liquid Glass on iOS 26 with SwiftUI",
     "液态玻璃实现速查表，偏代码片段与迁移步骤",
     [], ["cheatsheet","migration","swiftui"]),
 rec("D05", D, "youshen2/MeloX", "Swift", 203, "2026-08-29",
     "SwiftUI + Liquid Glass 原生第三方网易云客户端，参考 iOS 26 Apple Music UI",
     "完整生产级 App 中落地液态玻璃与 Apple Music 风格图标的真实案例",
     [], ["full-app","apple-music-style","production"]),
 rec("D06", D, "mertozseven/LiquidGlassSwiftUI", "Swift", 60, "2026-08-01",
     "Sample app demonstrating iOS 26 Liquid Glass (quote card, action buttons, symbol transitions)",
     "最小可运行的玻璃材质/符号过渡动画示例",
     [], ["sample-app","symbol-transition"]),
 rec("D07", D, "muhittincamdali/SwiftUI-iOS26-Showcase", "Swift", 16, "2026-08-27",
     "50+ iOS 26 new API demos in one app - Liquid Glass, Foundation Models & more",
     "50+ 个 iOS 26 新 API 单点 demo，按需查阅",
     [], ["demo-collection","ios26","new-api"]),
]

# ============ E. 综合索引 / 导航 ============
E = "E_curated_indexes"
records += [
 rec("E01", E, "vsouza/awesome-ios", "Swift", 53198, "2026-08-29",
     "A curated list of awesome iOS ecosystem, including Objective-C and Swift Projects",
     "iOS 生态总索引，需要更多 UI/图标库时从这里按类目下钻", [], ["awesome-list","index"]),
 rec("E02", E, "matteocrippa/awesome-swift", "Ruby", 26232, "2026-08-28",
     "A collaborative list of awesome Swift libraries and resources",
     "Swift 库总索引（UI / Images / 组件分类）", [], ["awesome-list","swift","index"]),
 rec("E03", E, "Blackjacx/WWDC", "Shell", 2596, "2026-08-28",
     "WWDC session gist 提取合集（含 design / swiftui / darkmode 等）",
     "历年 WWDC 设计与 SwiftUI session 文字精要，追官方设计口径", [], ["wwdc","design","notes"]),
]

db = {
    "database": "apple-ui-icon-design-reference",
    "version": "1.0",
    "generated_at": "2026-08-29T06:40:00+08:00",
    "source": "GitHub Search/Repositories & Contents API (live queries via github-remote MCP)",
    "star_note": "stars_at_2026_08_29 为检索时刻快照，会随时间变化；以 html_url 实时数据为准",
    "category_legend": {
        "A_sf_symbols_system_icons": "苹果系统图标 SF Symbols：类型安全调用 / 字体矢量提取 / SVG 导出 / 选择器 / 跨平台桥接",
        "B_app_icons_asset_geometry": "App 主屏幕图标：全套尺寸生成 / Asset Catalog / HIG 安全区与连续圆角几何",
        "C_apple_style_ui_design_systems": "Apple 风格 UI 设计系统与组件库（SwiftUI / UIKit / 跨平台 Cupertino）",
        "D_ios26_liquid_glass": "iOS 26 Liquid Glass 液态玻璃新设计语言（WWDC2025，2025-2026 最新）",
        "E_curated_indexes": "综合导航索引，用于继续扩展本数据库",
    },
    "official_reference_urls": {
        "sf_symbols_overview": "https://developer.apple.com/design/human-interface-guidelines/sf-symbols",
        "sf_symbols_download": "https://developer.apple.com/sf-symbols/",
        "app_icons_hig": "https://developer.apple.com/design/human-interface-guidelines/app-icons",
        "materials_hig": "https://developer.apple.com/design/human-interface-guidelines/materials",
        "liquid_glass_doc": "https://developer.apple.com/documentation/TechnologyOverviews/liquid-glass",
        "design_resources": "https://www.figma.com/community/file/1251588934545984324/Apple-Design-Resources-iOS-and-iPadOS-26",
        "swiftui_glasseffect": "https://developer.apple.com/documentation/swiftui/view/glasseffect(_:in:)",
    },
    "local_snippets_index": {
        "01": "code-snippets/01-sfsymbols-glyph-extraction.swift  CoreText 提取系统图标矢量路径",
        "02": "code-snippets/02-sfsymbols-svg-exporter.swift      CGPath→SVG 导出器",
        "03": "code-snippets/03-sfsafesymbols-type-safe-access.swift 类型安全图标调用",
        "04": "code-snippets/04-appicon-asset-catalog.swift       多尺寸 App 图标资产模型",
        "05": "code-snippets/05-hig-icon-geometry-canvas.tsx      HIG 13/16 安全区+22%圆角",
        "06": "code-snippets/06-liquid-glass-iOS26-cheatsheet.txt iOS26 液态玻璃 API 速查",
    },
    "record_count": len(records),
    "records": records,
}

out = os.path.join(BASE, "apple-ui-reference-db.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(db, f, ensure_ascii=False, indent=2)

# 校验：回读
with open(out, encoding="utf-8") as f:
    chk = json.load(f)
print("records:", chk["record_count"], "| parsed back OK")
cats = {}
for r in chk["records"]:
    cats[r["category"]] = cats.get(r["category"], 0) + 1
for k, v in cats.items():
    print(" ", k, v)
print("sha256:", hashlib.sha256(open(out,"rb").read()).hexdigest()[:16])
