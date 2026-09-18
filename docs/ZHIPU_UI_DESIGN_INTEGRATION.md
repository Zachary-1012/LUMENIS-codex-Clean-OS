# 智谱UI设计元素接入 ZBC 设计系统 — 集成文档

> **版本**: V1.0
> **日期**: 2026-09-07
> **状态**: VERIFIED
> **分支**: lumenis-dual-domain-v3
> **范围**: 仅限 AI 相关模块（AI Gateway / AI 对话工作台 / 浮动 AI 助手），不影响 ZBC 其他页面

---

## 1. 目标与原则

将智谱（Zhipu GLM / ZCode 3.0）设计语言中的核心元素接入 ZBC 的 AI 相关模块，与现有 ZBC 设计系统合并，**不破坏整体设计语言**。

### 核心原则
- **智谱元素仅限 AI 模块**：AI 对话工作台、浮动 AI 助手使用智谱蓝 `#2f6bff`；其他页面保持薄荷绿 `#00D4AA` 主色
- **深色模式仅限 AI 容器**：通过 `[data-ai-theme="dark"]` 作用于 AI 工作台容器，不全局切换
- **动效统一走 Motion System**：`LDMotion` / `ZBCMotion(AdaptiveMotion)`，不单独写 `@keyframes`
- **布局接入 Adaptive UI**：`.ad-container` + `data-size`（compact/comfortable/normal/expanded），不写固定宽度
- **B Shard 功能完整保留**：AI Task Engine、Provider 状态、调用日志、OWASP、评估面板全部不破坏

---

## 2. 智谱设计元素接入清单

| 智谱元素 | 接入方式 | 位置 |
|---------|---------|------|
| 三栏布局（历史+对话+详情） | `.ai-workspace` CSS Grid + Adaptive UI | `templates/system/ai.html` |
| AI 消息底部操作栏（复制/继续/停止） | `.ai-msg-actions` + `.ai-msg-action` | ai.html / ai-assistant.js |
| 打字机流式输出 + 闪烁光标 | JS `setInterval` 逐字输出，光标 JS 切换 `is-hidden` | ai-assistant.js / ai.html AIChat |
| AI 模块专属蓝色 `#2f6bff` | CSS 变量 `--ai-accent` | lumenis-global-design.css §20 |
| AI 模块深色主题 | `[data-ai-theme="dark"]` 容器级覆写 | lumenis-global-design.css §20.12 |
| 状态监控看板（ZCode 3.0 风格） | `.ai-monitor-grid` + `.ai-monitor-card` 大数字KPI+渐变文字 | ai.html |
| 多模态输入预览 | `.ai-attach-preview` + `.ai-attach-chip`（缩略图/文件名/大小/删除） | ai.html / ai-assistant.js |
| 大圆角卡片 (20-28px) | 复用 `--ld-radius-card` / `--ld-radius-card-lg` | 全局 |
| full-rounded 按钮 | `.ai-btn` + `border-radius: var(--ld-radius-pill)` | CSS §20.4 |
| 渐变文字效果 | `background-clip: text` + `--ai-gradient-text` | `.ai-monitor-card__value` |

---

## 3. CSS 变量定义（lumenis-global-design.css §20）

```css
:root {
  --ai-accent: #2f6bff;           /* 智谱蓝主色 */
  --ai-accent-hover: #4a80ff;
  --ai-accent-active: #1e56e6;
  --ai-accent-soft: rgba(47, 107, 255, 0.1);
  --ai-accent-border: rgba(47, 107, 255, 0.28);
  --ai-accent-glow: 0 0 20px rgba(47, 107, 255, 0.3);
  --ai-gradient: linear-gradient(135deg, #2f6bff 0%, #6366f1 100%);
  --ai-gradient-text: linear-gradient(135deg, #2f6bff 0%, #8b5cf6 100%);
  /* 智谱深色主题 */
  --ai-bg-dark: #1a1a1e;
  --ai-card-dark: #25252b;
  --ai-text-dark: #e8ecf1;
  --ai-border-dark: rgba(255, 255, 255, 0.08);
}
```

### 深色主题作用域
```css
[data-ai-theme="dark"] {
  --l-bg: var(--ai-bg-dark);
  --l-card: var(--ai-card-dark);
  --l-text: var(--ai-text-dark);
  /* ... 覆写现有 --l-* 变量 ... */
}
```
通过覆写 `--l-*` 全局变量，AI 容器内的所有现有组件（zbc-card、zbc-tag 等）自动适配深色，无需逐个重写。

---

## 4. 三栏布局与 Adaptive UI

### 布局结构
```
.ai-workspace.ad-container (CSS Grid)
├── .ai-pane--left   (260px, 可折叠)  历史对话列表
├── .ai-pane--center (minmax(0,1fr))   主对话区 + 输入框
└── .ai-pane--right  (320px, 可折叠)  详情面板（步骤/Evidence/风险/权限）
```

### 响应式断点（Adaptive Engine 驱动）
| data-size | 视口宽度 | 布局 |
|-----------|---------|------|
| expanded/wide | > 720px | 三栏全展开 |
| comfortable | 480-719px | 左栏+中栏，右栏自动收起 |
| compact | < 480px | 单栏堆叠，侧栏隐藏 |

折叠通过 `data-left-collapsed` / `data-right-collapsed` 属性控制，用户可手动切换。

### 媒体查询兜底
无 JS 环境下通过 `@media (max-width: 1024px)` / `@media (max-width: 720px)` 兜底。

---

## 5. 打字机效果实现

### 核心逻辑（ai.html AIChat / ai-assistant.js）
```javascript
_startTypewriter(bubbleEl, fullText, onDone) {
  // 1. 创建光标元素 .ai-cursor
  // 2. setInterval 每 ~21ms 追加 2 个字符（速度随文本长度自适应）
  // 3. 光标通过 setInterval(530ms) 切换 is-hidden 类实现闪烁
  // 4. 完成后清除定时器、移除光标、调用 onDone
  // 5. respects _reduced() — prefers-reduced-motion 时直接显示全文
}
```

### 关键设计
- **光标闪烁由 JS 驱动**，不使用 CSS `@keyframes`，符合"动效统一走 Motion System"约束
- **速度自适应**：`Math.max(10, Math.min(35, Math.floor(1400 / textLength)))`，长文本更快
- **可访问性**：检测 `ZBCMotion._reduced` / `LDMotion._reduced`，减少动画偏好时跳过打字机
- **消息进入动效**：`ZBCMotion.applyPreset(msgEl, 'enter')` 实现 fade-in + slide-up

---

## 6. AI 状态监控看板

### KPI 指标（4 卡片）
| 指标 | 数据来源 | 说明 |
|------|---------|------|
| 今日调用 | `/viz/ai-logs` → `/ai/logs` | 日志记录总数 |
| 成功率 | 同上 | 成功/总数 × 100% |
| 平均响应 | 同上 | `latency_ms` / `duration_ms` 均值 |
| 运行任务 | `/api/ai/task-engine/health` → `/api/ai/tasks` | 队列中 + 执行中 |

### 设计
- 大数字 KPI（36px, font-weight 800）
- 渐变文字（`--ai-gradient-text` + `background-clip: text`）
- 顶部 3px 智谱蓝渐变条（hover 时显示）
- 复用 `LDMotion.countUp` 实现数字滚动动画

---

## 7. 多模态输入预览

### 功能
- 文件选择按钮（回形针图标），支持 `image/*,.pdf,.txt,.docx,.xlsx,.csv`
- 上传后显示附件 chip：缩略图（图片）/ 文件类型图标 / 文件名 / 大小
- 支持删除单个附件
- **实际上传逻辑为 UI 预览**，附件信息以文本形式附加到任务输入中，后续可接入真实上传

### 实现
- `FileReader` / `URL.createObjectURL` 生成图片缩略图
- 附件大小自动格式化（KB/MB）
- 删除时 `URL.revokeObjectURL` 释放内存

---

## 8. 浮动 AI 助手升级（ai-assistant.js V2.1）

| 功能 | V1.0 | V2.1 |
|------|------|------|
| 主色 | 薄荷绿 `#0f766e` | 智谱蓝 `#2f6bff` |
| AI 回复显示 | 一次性文本 | 打字机逐字输出 |
| 消息操作 | 无 | 复制按钮（hover 显示） |
| 主题 | 跟随全局 | 独立深色/浅色切换（面板级） |
| 附件 | 无 | 多模态预览（图片/文件） |
| 输入框 | input | textarea（自适应高度） |
| 动效 | CSS @keyframes | ZBCMotion.applyPreset + JS 驱动 |
| API 对接 | Task Engine → /api/ai/chat → 本地提示 | 不变（完整保留降级链） |

---

## 9. 文件变更清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `static/css/lumenis-global-design.css` | 追加 §20（~280行） | AI 模块专属 CSS 变量、组件、深色主题、三栏布局、响应式 |
| `templates/system/ai.html` | 插入 + 追加 JS | 状态监控看板（4 KPI）、三栏对话工作台、AIChat JS 模块（~350行） |
| `static/js/ai-assistant.js` | 重写（V2.1） | 打字机、复制操作栏、深色模式、多模态预览、智谱蓝主色 |

### 未修改文件
- `ai_task_engine.py` — AI Core，API 调用链不变
- `SUBJECT_WORDS` / `SUBJECT_EXCLUDE_WORDS` / `subject_hit()` — 主体口径不变
- 数据库 — 无迁移、无表结构变更
- 其他页面模板 — 设计语言不变

---

## 10. 测试结果

### 页面渲染
- [x] AI 页面 `/lumenis/system/ai` 正常加载（HTTP 200）
- [x] 三栏结构渲染：左栏（历史）+ 中栏（对话）+ 右栏（详情）
- [x] 状态监控看板 4 KPI 卡片渲染
- [x] B Shard 功能完整：Provider 状态（4卡片）、调用日志、OWASP、评估面板、Task Engine

### 交互功能
- [x] 深色/浅色切换：`data-ai-theme` 在 light/dark 间切换，仅作用于 AI 容器
- [x] 左栏折叠/展开：`data-left-collapsed` 控制
- [x] 右栏折叠/展开：`data-right-collapsed` 控制
- [x] 新建对话：创建会话并显示在历史列表
- [x] 打字机效果：逐字输出 + 光标闪烁，完成后显示复制操作栏
- [x] 复制按钮：点击后显示"已复制"反馈
- [x] 多模态预览：附件 chip 渲染、文件名显示、删除功能
- [x] 浮动 AI 助手：打开/关闭、深色切换、打字机回复

### 响应式
- [x] Adaptive UI：940px 视口自动识别 `comfortable`，右栏收起（220px 288px 0px）
- [x] 媒体查询兜底：1024px / 720px 断点

### 设计一致性
- [x] `--ai-accent: #2f6bff` 生效，与薄荷绿 `#00D4AA` 区分
- [x] 深色模式不影响其他页面（容器级作用域）
- [x] 动效走 `LDMotion` / `ZBCMotion`，无独立 `@keyframes`
- [x] 大圆角（20-28px）、full-rounded 按钮、毛玻璃风格与 ZBC 一致

### 回归
- [x] 8201 服务重启后 healthz 返回 200
- [x] AI Task Engine 状态 HEALTHY
- [x] 无新增 JS 错误（404 为现有 API 端点，非本次引入）

---

## 11. 已知限制与后续建议

### 当前限制
1. **监控看板数据源**：`/viz/ai-logs` 端点返回 404 时 KPI 显示"日志接口不可用"，需 J Shard 完善 Provider/日志 API 后自动恢复
2. **多模态实际上传**：当前为 UI 预览，附件信息以文本附加到任务输入，真实文件上传需后端 API 支持
3. **打字机速度**：短文本（< 100 字）完成较快（~0.7s），长文本自适应减速
4. **浮动助手会话**：浮动助手不持久化对话历史（页面刷新后清空），工作台会话持久化到 localStorage

### 后续建议（P2）
1. 与 J Shard 协调 AI Provider 切换状态，接入监控看板实时 Provider 健康度
2. 与 H Shard 协调内容制作激活，将 AI 对话嵌入内容生成流程
3. 实现真实多模态文件上传 API（后端接收 + 向量存储）
4. 打字机效果接入 SSE 流式响应（当前为轮询完成后一次性打字）
5. 右侧详情面板增加 Git 分支图谱（ZCode 3.0 风格）

---

## 12. 硬约束遵守情况

| 约束 | 状态 |
|------|------|
| 不修改 SUBJECT_WORDS / subject_hit() | ✅ 未触碰 |
| 不破坏数据库（125表） | ✅ 无迁移 |
| 不破坏 AI Core API 调用链 | ✅ /api/ai/tasks 等端点不变 |
| 不破坏 ZBC 整体设计语言 | ✅ 智谱蓝仅限 AI 模块 |
| 不删除 B Shard AI Task Engine 功能 | ✅ 完整保留 |
| 动效统一走 motion_engine / adaptive-motion | ✅ 无独立 @keyframes |
| 布局接入 Adaptive UI | ✅ .ad-container + data-size |
| 不自动 merge main | ✅ 本地分支修改 |
| 代码自研 | ✅ |
| 微信跳过 | ✅ |

---

**最终状态**: VERIFIED
