# ZBIP Icon System

> Z-Brand Intelligence Platform 统一线性图标系统。所有产品共享此图标规范，确保视觉一致性。
>
> 版本：v1.0 · 维护者：AI-D Hub · 最后更新：2026-08-31

---

## 1. 核心原则

1. **Linear Only** — 只使用线性图标，不使用填充图标、不使用 emoji、不使用 3D 图标
2. **Monochrome** — 单色，通过 `currentColor` 继承父元素颜色
3. **统一 Stroke** — 所有图标线宽一致
4. **统一 Weight** — 视觉重量一致
5. **统一 Size** — 使用标准尺寸档位
6. **状态通过颜色表达** — 不通过图标形状变化表达状态
7. **不使用无意义的装饰性图标** — 每个图标必须有明确功能含义

---

## 2. 图标规格

### 2.1 尺寸档位

| Token | Size | 用途 |
|---|---|---|
| `--zb-icon-xs` | 14px | 标签内 / 紧凑列表 |
| `--zb-icon-sm` | 16px | 按钮 / 输入框 / 普通列表 |
| `--zb-icon-md` | 20px | 导航栏 / 工具栏 / 卡片标题 |
| `--zb-icon-lg` | 24px | 大按钮 / 空状态 / 功能入口 |
| `--zb-icon-xl` | 32px | 页面级空状态 / 引导页 |

### 2.2 线宽

| Token | Value | 用途 |
|---|---|---|
| `--zb-icon-stroke` | 1.8px | 默认线宽 |
| `--zb-icon-stroke-light` | 1.5px | 小尺寸图标 (≤16px) |
| `--zb-icon-stroke-bold` | 2.0px | 强调 / 大尺寸图标 (≥24px) |

### 2.3 其他属性

```css
--zb-icon-fill: none;
--zb-icon-stroke-linecap: round;
--zb-icon-stroke-linejoin: round;
--zb-icon-color: currentColor;
```

---

## 3. 颜色规则

图标颜色通过 `currentColor` 继承，不硬编码颜色。

| 场景 | 颜色 Token |
|---|---|
| 默认 / 普通 | `--zb-text-primary` |
| 辅助 / 次要 | `--zb-text-secondary` |
| 禁用 | `--zb-text-tertiary` (opacity 0.4) |
| 活跃 / 选中 | `--zb-blue` |
| 成功 / 通过 | `--zb-green` |
| 警告 / 待处理 | `--zb-orange` |
| 错误 / 风险 | `--zb-red` |
| AI / 指令 | `--zb-purple` |
| 信息 / 只读 | `--zb-teal` |

**禁止**：
- ❌ 在 SVG 中硬编码 `fill="#000"` 或 `stroke="#fff"`
- ❌ 使用渐变色图标
- ❌ 使用多色图标
- ❌ 使用 emoji 作为正式 UI 图标

---

## 4. 标准图标集

### 4.1 导航类

| 图标名称 | SVG Path 摘要 | 用途 |
|---|---|---|
| `home` | 房子轮廓 | 首页 / 主页 |
| `search` | 放大镜 | 搜索 |
| `menu` | 三条横线 | 菜单 / 更多 |
| `settings` | 齿轮 | 设置 |
| `user` | 人物轮廓 | 用户 / 账户 |
| `bell` | 铃铛 | 通知 |
| `grid` | 九宫格 | 应用列表 / 功能矩阵 |

### 4.2 操作类

| 图标名称 | SVG Path 摘要 | 用途 |
|---|---|---|
| `plus` | 加号 | 新建 / 添加 |
| `edit` | 铅笔 | 编辑 |
| `trash` | 垃圾桶 | 删除 |
| `copy` | 重叠矩形 | 复制 |
| `download` | 向下箭头+横线 | 下载 / 导出 |
| `upload` | 向上箭头+横线 | 上传 / 导入 |
| `share` | 分享节点 | 分享 |
| `refresh` | 环形箭头 | 刷新 / 重新加载 |
| `check` | 对勾 | 确认 / 完成 |
| `x` | 叉号 | 关闭 / 取消 |
| `chevron-right` | 右箭头 | 进入 / 展开 |
| `chevron-down` | 下箭头 | 展开 / 下拉 |
| `arrow-left` | 左箭头 | 返回 |
| `external-link` | 箭头+方框 | 外部链接 |

### 4.3 状态类

| 图标名称 | SVG Path 摘要 | 用途 |
|---|---|---|
| `circle` | 空心圆 | 默认 / 未完成 |
| `check-circle` | 圆内对勾 | 已完成 / 通过 |
| `alert-circle` | 圆内感叹号 | 警告 / 注意 |
| `x-circle` | 圆内叉号 | 错误 / 失败 |
| `info` | 圆内 i | 信息 |
| `clock` | 时钟 | 时间 / 历史 / 待处理 |
| `loader` | 旋转弧线 | 加载中（动画） |

> **注意**：状态优先使用 **彩色小圆点**（Status Dot），图标仅作为辅助。

### 4.4 开发 / 工程类

| 图标名称 | SVG Path 摘要 | 用途 |
|---|---|---|
| `git-branch` | 分支节点 | 分支 / 版本 |
| `git-commit` | 圆点+连线 | Commit |
| `git-pull-request` | 分支合并 | PR / Merge |
| `code` | `</>` | 代码 |
| `terminal` | `>_` | 终端 / 命令行 |
| `test-tube` | 试管 | 测试 |
| `shield` | 盾牌 | 安全 / 权限 |
| `database` | 数据库圆柱 | 数据 / 存储 |
| `server` | 服务器 | 服务 / Bridge |
| `file-text` | 文档 | 文件 / 文档 |
| `folder` | 文件夹 | 目录 |
| `layers` | 层叠 | 架构 / 层级 |
| `activity` | 心跳线 | 活动 / 监控 / 审计 |
| `zap` | 闪电 | 性能 / 快速 |
| `eye` | 眼睛 | 查看 / 只读 / 审计 |
| `lock` | 锁 | 私有 / 安全 / 权限 |

### 4.5 AI / 研究类

| 图标名称 | SVG Path 摘要 | 用途 |
|---|---|---|
| `sparkles` | 星星闪光 | AI / 智能 |
| `brain` | 脑轮廓 | 学习 / 记忆 |
| `flask` | 烧瓶 | 实验 / Shadow |
| `book-open` | 打开的书 | 研究 / 案例库 |
| `target` | 靶心 | 目标 / Benchmark |
| `trending-up` | 上升趋势 | 能力提升 / Delta |
| `git-compare` | 对比箭头 | 对比 / 验证 |

---

## 5. SVG 模板

### 5.1 标准 SVG 结构

```svg
<svg
  width="20"
  height="20"
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  stroke-width="1.8"
  stroke-linecap="round"
  stroke-linejoin="round"
>
  <!-- 图标路径 -->
</svg>
```

### 5.2 CSS 类方式

```css
.zb-icon {
  width: var(--zb-icon-md, 20px);
  height: var(--zb-icon-md, 20px);
  fill: none;
  stroke: currentColor;
  stroke-width: var(--zb-icon-stroke, 1.8px);
  stroke-linecap: round;
  stroke-linejoin: round;
  flex-shrink: 0;
}
```

### 5.3 示例：搜索图标

```svg
<svg class="zb-icon" viewBox="0 0 24 24">
  <circle cx="11" cy="11" r="7"/>
  <line x1="16.5" y1="16.5" x2="21" y2="21"/>
</svg>
```

---

## 6. 各仓库实现状态

| 仓库 | 图标系统状态 | 说明 |
|---|---|---|
| AI-D | ✅ 本文件为母规范 | 待产出 SVG 图标集文件 |
| DCC | ⚠️ 部分实现 | index.html 内联 SVG（搜索/主题切换），github-audit.js 无图标 |
| SICI | ⚠️ 待确认 | 未读取 index.html 确认图标实现 |
| Z-Brand-Core | ⚠️ 待确认 | Dashboard 图标待确认 |

---

## 7. 反模式（禁止）

| 反模式 | 正确做法 |
|---|---|
| ❌ 使用 emoji 作为图标 | ✅ 使用 SVG 线性图标 |
| ❌ 图标硬编码颜色 | ✅ 使用 currentColor |
| ❌ 不同页面使用不同风格图标 | ✅ 统一从图标集选取 |
| ❌ 用图标形状变化表达状态 | ✅ 用颜色 + 状态圆点表达 |
| ❌ 填充图标和线性图标混用 | ✅ 全部线性 |
| ❌ 图标尺寸随意 | ✅ 使用标准尺寸档位 |
| ❌ 装饰性无意义图标 | ✅ 每个图标有明确功能 |
| ❌ 多色 / 渐变图标 | ✅ 单色 |

---

## 8. 待办

- [ ] 产出完整 SVG 图标集文件（`design-system/icons/` 目录）
- [ ] DCC 提取内联 SVG 为统一图标组件
- [ ] SICI 确认并适配图标系统
- [ ] Z-Brand Dashboard 图标适配
- [ ] 图标可访问性（aria-label / title）

---

*本文件由 AI-D Hub 维护，图标集变更需经过 Shadow 验证和 Cross-Repository Validation。*
