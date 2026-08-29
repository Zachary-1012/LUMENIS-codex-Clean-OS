# -*- coding: utf-8 -*-
import json, os
BASE = r"C:\Users\28049\Doubao\chats\2026-08-29\new-chat-2\apple-ui-reference"
db = json.load(open(os.path.join(BASE, "apple-ui-reference-db.json"), encoding="utf-8"))

CAT_TITLE = {
 "A_sf_symbols_system_icons": "A. SF Symbols 系统图标",
 "B_app_icons_asset_geometry": "B. App 图标（资产/几何）",
 "C_apple_style_ui_design_systems": "C. Apple 风格 UI 设计系统与组件",
 "D_ios26_liquid_glass": "D. iOS 26 Liquid Glass 液态玻璃",
 "E_curated_indexes": "E. 综合索引",
}
lines = ["# 参考仓库分类目录（36）\n",
         "> Star / 更新时间为 2026-08-29 检索快照；`归档`=仓库已 archived。\n"]
for cat, title in CAT_TITLE.items():
    rows = [r for r in db["records"] if r["category"] == cat]
    lines.append(f"\n## {title}（{len(rows)}）\n")
    lines.append("| ID | 仓库 | 语言 | Star | 最近更新 | 归档 | 用途 |")
    lines.append("|---|---|---|---:|---|:---:|---|")
    for r in rows:
        desc = r["use_case"].replace("|", "/")
        lang = r["language"] or "-"
        arch = "是" if r["archived"] else ""
        lines.append(f"| {r['id']} | [{r['full_name']}]({r['html_url']}) | {lang} | {r['stars_at_2026_08_29']} | {r['last_pushed_at']} | {arch} | {desc} |")
lines.append("\n## 本地代码样本\n")
lines.append("| 文件 | 对应仓库 | 内容 |")
lines.append("|---|---|---|")
SNIP = {
 "01": ("A02 davedelong/sfsymbols", "CoreText 按字形名提取 CGPath 矢量路径与元数据"),
 "02": ("A02 davedelong/sfsymbols", "CGPath 元素转标准 SVG path（含 y 轴翻转）"),
 "03": ("A01 SFSafeSymbols", "UIImage/Image 类型安全初始化器与可变值图标"),
 "04": ("B01 raphaelhanneken/iconizer", "AppIcon 多 idiom/scale 模型与 1024 无 alpha 规则"),
 "05": ("B03 yc-w-cn/macos-compliant-icon-generator", "1024 画布/832 内容(13/16)/22% 连续圆角 Canvas 实现"),
 "06": ("D01 conorluddy/LiquidGlassReference", "iOS26 glassEffect 全量 API、模式、兼容与规则"),
}
for k, (repo, what) in SNIP.items():
    fn = [x for x in os.listdir(os.path.join(BASE,"code-snippets")) if x.startswith(k)][0]
    lines.append(f"| `code-snippets/{fn}` | {repo} | {what} |")
out = os.path.join(BASE, "catalog.md")
open(out, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("catalog.md written, lines:", len(lines))
