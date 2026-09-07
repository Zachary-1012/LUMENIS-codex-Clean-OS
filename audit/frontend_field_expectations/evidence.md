# 前端字段期望审计 · evidence（证据链）

> 审计时间：2026-09-08 · 只读静态分析 · **通用六态面板模板**

## 页面信息
- **模板文件**：`templates/cth/evidence.html`
- **路由**：`/lumenis/cth/evidence`
- **模板类型**：六态面板（loading/empty/error/success/degraded/partial）
- **初始化触发**：`LUMENIS.ready` → 读取 `data-api` → `LUMENIS.fetch()`

## API 调用清单

| # | 端点 | 方法 | 调用位置 | 用途 |
|---|---|---|---|---|
| 1 | `/api/evidence/list` | GET | evidence.html:31 (`data-api`) | 证据列表（唯一 API） |

## 期望响应字段树

**通用提取逻辑 `extractList()`**（evidence.html:~140）按优先级尝试：
```
response
├── data (array 或 object.list)
├── items[]
├── list[]
├── results[]
├── records[]
├── notes[]
├── cases[]
├── events[]
└── rows[]
```

**列推断 `inferColumns()`**：从第一条数据的 `Object.keys()` 动态生成列，无固定字段契约。

每条记录可能包含（取决于后端实际返回）：
- id / evidence_id
- title / name
- type / category
- source / platform
- related_event / event_id
- related_note / note_id
- created_at / captured_at
- content / description
- url / link

## 硬编码数据
- 页面标题"证据链"、空态文案"暂无证据数据"为硬编码
- 六态面板 UI 结构为硬编码

## 渲染假设与字段缺失处理
- **列表 key 多路径探测**：依次尝试 9 种 key，全失败则 `[]`
- **列名动态推断**：`Object.keys(firstItem)`，无数据则无列
- **空数据** → empty 态（图标 + 文案 + 刷新按钮）
- **加载中** → skeleton loading 态
- **错误** → error 态（错误信息 + 重试按钮）
- **字段缺失** → 单元格显示空字符串
- **降级** → degraded 横幅

## 备注
- 与 industries/kos/negative/official/event_graph/calendar/analysis/cases/case_analysis/knowledge/notes 共享完全相同的六态面板 JS 逻辑，仅 `data-api` 属性不同
- 无固定字段契约，完全依赖后端返回结构动态渲染
