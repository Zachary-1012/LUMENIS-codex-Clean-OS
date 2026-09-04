# 序境命名治理同步审计（2026-09-04）

- **指令**：同步把双子库里已经更新的命名更新
- **基线**：《序境｜产品命名与术语治理》（PRODUCT_NAMING_AND_TERMINOLOGY.md）
- **范围**：序境-Core（ZBC）+ 序境-Intelligence（OSAI）

## 审计结论：命名治理已全面落地，双库一致

### 1. 产品展示层（用户可见）— 已序境化 ✅
| 层 | ZBC | OSAI | 状态 |
|---|---|---|---|
| README 顶层 | `# 序境`（序境-Core，含 서경/品牌哲学/双子库边界） | `# 序境-智能 · Intelligence` | ✅ |
| UI 展示层 | 首页 DOM「序境」4 处 /「Zachary」0 处（UI_VISUAL_AUDIT_01 证实） | — | ✅ |
| Registry 文档 | FUNCTION/METRIC/CANONICAL 等全用「序境」 | INTELLIGENCE_REGISTRY `# 序境-Intelligence` | ✅ |
| templates/ 遗留多页面 | 无任何 Zachary 残留 | — | ✅ |
| 前端 i18n | `xujing-i18n.js` / `xujing-ui.js` / `xujing-crossfilter.js` 实际存在，文档引用一致 | — | ✅ |

### 2. 规范保留项（按序境规则不动）✅
- **历史审计/基线档案**（spec.md、FIRST-TIER-RND-BASELINE、evidence-traceability、review、checklist、CROSS-REPO、DUAL-REPO、MASTER-ENG 等）：保留原名作为历史证据，符合"旧名称进入 LEGACY，不产生新引用"。
- **代码技术标识**（CSS class `zachary-*`、JS 函数名 `toggleZacharyChat`、资源名、`zbip-shell` 等）：为技术标识，UI_VISUAL_AUDIT_05 明确"技术标识不动"，避免破坏登录/样式/功能。

### 3. 边界声明（README 已写入）
- `Zachary-OS-AI` / `Z-Brand-Core` 仅为 GitHub Repository identifier，不是中文产品名称。
- 历史 `Xujing / Xujing Core / Xujing Intelligence` 标记 LEGACY，仅历史兼容/审计，不新增引用。
- 英文 Canonical Brand = TBD（完成全球冲突/语言文化/商标/数字身份审查前保持 TBD）。

## 结论
双子库命名治理已同步到位：产品展示层 100% 序境化，历史档案与技术标识按规范保留。无命名不一致残留。
