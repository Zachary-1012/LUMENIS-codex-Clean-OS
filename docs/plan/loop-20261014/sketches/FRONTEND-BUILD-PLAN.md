# 序境 LUMENIS 前端分步建设计划（草稿，2026-10-14，待 PO 审核）

> 依据：现有屏幕规格 44 屏、本目录各 *-ADD-* 草图、product-plan-full.md（四表面 F 行、G16、G18-G20、G45）、Experience Constitution（禁止 ChatGPT 克隆/通用 SaaS 仪表盘/复制他人交互序列，§24/§33/§38）、THIRD-PARTY-COMPONENT-REGISTER。
> 全部闭环内；前端与后端并行。上线后仅真实用户验证与付费/授权来源。

## 0. 统一约定（每步都适用）
| 项 | 约定 |
|---|---|
| 技术栈 | Flutter（Web/Win/macOS/iOS 一套代码）+ go_router + http；官网 Astro；新依赖须走第三方登记（许可不明=阻断） |
| 构建顺序 | 合同/数据适配 → 页面骨架（真实数据或「数据缺失」）→ 交互 → 动效 → 三语 → 无障碍 → 四端验收 |
| UX 原则 | 任务决定呈现；先给有用内容；流入内容不抢焦点；键盘可达 + ⌘/Ctrl+K 命令面板 + 右键上下文菜单（参 Linear [L1]）；常用操作 ≤100ms 乐观更新，失败回滚并提示 |
| AIGC | 只出现在：AI-01 对话与卡片、AI-02 产物、AI-03 分析、BMP-06/08 内容与播客、CTH-10 报告草稿、角色/Logo 草图。标注：整份 AI 生成=「AI 生成」，部分=「含 AI 内容」（参 C2PA [C1]）+ 水印「据实生成 · 来源可溯 · AI生成信息请辛苦核对」；每段可展开来源；发布/导出前需人工确认；可一键撤销/重生成；模型不可用显示「不可用」，不切换 |
| 动效令牌 | 进入 250ms 标准减速；退出 200ms 标准加速；面内变化 300ms 标准；大面板/页面切换 400ms 强调减速（参 Material 3 [M1]）；状态小反馈 ~200ms 不阻塞（[L2]）；动效可被打断，不等待动画完成（Apple HIG [A1]） |
| 减少动态 | 读取系统设置（Flutter MediaQuery.disableAnimationsOf [F1]）+ 设置里可手动开关；开启后：位移/缩放/视差/旋转 → 淡入淡出或颜色变化，持续动画（加载转圈除外）停止（[A2]） |
| 缺失与规则 | 缺失显示「数据缺失」不补 0/50；无账号墙；无主体写死；无自动回退；用户选择保留 |
| 验收 | 每步：flutter analyze/test 绿 + 真实数据或真实缺失截图 + 三语 + 200% 字号 + 减少动态 + 四端启动/离开返回 |

## 1. 分步计划
| 步 | 范围（屏/能力） | 搭建方式与组件 | UX 模式 | AIGC | 交互 | 动效（时长/缓动；减少动态时） |
|---|---|---|---|---|---|---|
| F0 | 设计令牌与外壳：颜色/字号/间距/动效令牌、导航壳、命令面板、SYS-05 外观、视觉风格、Logo、五角色 | ThemeExtension 令牌；shell/ 导航；Logo/角色自有矢量 SVG | 设置即时预览；角色只作身份提示 | 角色草图可用 AI 出方向，定稿人工矢量，标来源 | ⌘K、右键菜单、主题切换不丢状态 | 主题切换 300ms 颜色过渡；减少动态→直接切换 |
| F1 | ACC-01 登录/注册、首次「改进模型」询问；ACC-03 首页；ACC-04 守卫恢复 | 邮箱验证码 + Apple/Google OAuth 适配层；首页聊天入口 | 无账号墙，「先不登录」始终可见；首次询问无预选 | 无 | 验证码自动跳格、粘贴整码；OAuth 回原页 | 页面进入 250ms 淡入+8px 上移；减少动态→仅淡入 |
| F2 | 账号设置（通用/账号/安全/模型与API/连接器/用量/数据控制/开发者/关于） | 左导航+右内容，手机二级页；ACC-01 设置草图 | 分区设置、危险操作二次确认 | 无 | 删除输入邮箱确认；30 天撤销条；退出所有设备确认 | 分区切换 200ms 交叉淡化；面板 400ms 强调减速滑入；减少动态→淡化 |
| F3 | ACC-02 主体/视角选择 | 主体注册表读取；通用主体，无写死 | 选择只改工作上下文 | 无 | 搜索、键盘选择、最近使用 | 列表项进入 150ms 依次（最多 6 项）；减少动态→同时出现 |
| F4 | AI-01 意图入口 + 智能卡片 + 工具确认；AI-02 任务阶段；AI-03 来源优先分析 | 流式渲染、类型化卡片（不执行生成的 HTML/JS） | 先出有用内容；高风险操作人工确认 | 全部回答标「AI 生成」，引用可点开来源；可停止/重生成 | 流式不抢焦点；卡片内操作；停止按钮 | 流式文字无逐字动画抖动，新块 200ms 淡入；卡片展开 300ms；减少动态→无位移 |
| F5 | AI-04 Skills 商店 + GitHub/MCP 连接器；AI-05 模型拓扑 + 自带 API | 目录列表、权限说明、白名单 | 安装前看权限；连接前审查 | Skill 产出按 F4 规则标注 | 安装/停用/撤销；测试连接 | 安装进度条线性；完成 200ms 勾选反馈 |
| F6 | SYS-06 内置浏览器（标签/地址栏/折叠）+ 登录失效弹窗；SYS-02 采集状态 + 手动采集 | 内置浏览器组件，后台采集；外部浏览器仅「查看原文」 | 像普通浏览器，可折叠；失效即弹窗重登 | 无 | 标签拖拽、前进后退、折叠 | 折叠/展开 300ms 强调；弹窗 250ms 进入/200ms 退出；减少动态→淡化 |
| F7 | CTH-01~10（总览、主体、监测、事件、舆情日历、负面、趋势、案例、风险决策+数学结果卡、报告） | 时间轴、日历、图表（自绘），区间/置信展示 | 先结论后证据；时序≠因果标注 | CTH-10 报告草稿、CTH-09 建议标「AI 生成」，需人工确认才定稿 | 范围切换保留选中；钻取不丢上下文 | 图表数据切换 300ms 标准插值；缺失段显示空白+「数据缺失」不插值；减少动态→直接替换 |
| F8 | BMP-01~11（总览、竞品谱系、机会雷达、传播路径、创作者+KOS 漏斗+AI 发现观测、内容台+视频剪辑、活动台+营销日历+出海矩阵、播客制作室全链、评估+公开数据 MMM、风险、基准） | 同 F7 组件；剪辑/播客按规划 §14 E1–E11/P1–P12：逐词稿编辑器（删词即剪）、多轨时间线（真实波形、播放头与素材预览分离）、检查器（字幕/响度实测/章节/说话人/封面）、步骤条；FFmpeg 渲染与 OTIO 预检走后端；MMM 用公开数据/财报 + OpenAI Math | 文本优先剪辑（参 Descript）、提议需确认、计划与结果分开 | 脚本「AI 生成」、配音「AI 配音」、素材「含 AI 内容」+水印；平台披露自动带（可改不可删）；发布前人工确认 | 删词即剪、拖拽排期与轨道、空格播放/J K L 穿梭、试听循环、版本对比、画幅切换 | 播放头跟随无缓动；删词后稿件 150ms 淡出并合拢；漏斗/路径 400ms 强调；波形不做装饰动画；减少动态→直接合拢 |
| F9 | SH-01~06（能力目录、证据库、指标浏览、导出中心、学习资产、通知待办） | 只读列表/检查器；导出可重开 | 可定位引用；导出必须可重开 | 学习资产标来源与评估 | 筛选、预览、重开 | 列表筛选 200ms；减少动态→无 |
| F10 | SYS-01/03/04/07/08（运行健康、数据库真相链、安全与密钥合规、评测验收、可观测与运营/工作区生命周期） | 只读状态 + 安全操作 | 不暴露内部策略与凭据 | 无 | 轮换/撤销密钥、备份/恢复、诊断包 | 状态变化 200ms 颜色过渡 |
| F11 | 开发者模式：SYS-04 用户开发者模式（协议+备份恢复）；SYS-07 创始人内部发布（上传→测试→签名→分批→回滚） | 协议勾选表单；发布流水线状态；签名更新（Tauri/Sparkle/electron-updater 思路 [U1-U3]） | 逐项同意才可开；测试全绿才可发布 | 无 | 暂停/扩大批次/回滚 | 流水线步骤推进 300ms；减少动态→仅颜色 |
| F12 | 全屏视觉定稿：材质、图标、插画、角色图入屏、官网 Astro | 自有矢量资产，许可登记 | 序境自己的视觉，不借他牌风格 | 草图可 AI 辅助并标注 | — | 统一复核全部动效令牌 |
| F13 | 四端联合验收（G45）+ 性能/无障碍（G16：60fps、p95≤16.7ms、WCAG 2.2 AA、200% 字号） | 自动化 + 截图证据 | — | 抽查标注完整 | 键盘全流程 | 减少动态全屏抽查 |

## 2. 参考来源
- [M1] Material 3 easing & duration：https://m3.material.io/styles/motion/easing-and-duration/applying-easing-and-duration
- [A1] Apple HIG Motion：https://developer.apple.com/design/human-interface-guidelines/motion
- [A2] Apple Reduced Motion 评估标准：https://developer.apple.com/help/app-store-connect/manage-app-accessibility/reduced-motion-evaluation-criteria/
- [F1] Flutter MediaQuery.disableAnimationsOf：https://api.flutter.dev/flutter/widgets/MediaQuery/disableAnimationsOf.html
- [L1] Linear 上下文菜单与快捷键：https://linear.app/now/invisible-details
- [L2] Linear 设计模式整理（第三方，非官方）：https://github.com/marcus/marcus-skills/blob/main/skills/linear-design-patterns/references/linear-design-system.md
- [C1] C2PA UX 标注建议：https://spec.c2pa.org/specifications/specifications/2.0/ux/UX_Recommendations.html
- [U1] electron-builder 自动更新/分批：https://www.electron.build/docs/features/auto-update
- [U2] Tauri updater（签名必需、可回滚）：https://v2.tauri.app/plugin/updater/
- [U3] Sparkle 分阶段推送：https://sparkle-project.org/documentation/publishing/
- [D1] Descript 文本剪辑：https://www.descript.com/video-editing
- 未专门检索：ChatGPT/Grok/Arc 的动效细节（无可靠官方文档，未引用）。
