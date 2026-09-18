# Responsive Matrix（真实回归证据，非缩放）

依据主方案 §8.3 / §17 Responsive / 增补 §31：**Adaptive Layout（重排不是等比缩放）**，8 视口全覆盖，1440/1024/390 为人工级精修母版。

## 视口断点与档位
| 档位 | 视口宽 | 角色 | 产物（每屏） |
| --- | --- | --- | --- |
| Desktop wide | 1920 | 回归基线 | `14_visual_regression/shots/<ID>/1920.jpeg` |
| **Desktop master** | **1440** | **人工精修（png）+ 深色 1440-dark** | `1440.png` / `1440-dark.jpeg` |
| Desktop | 1280 | 回归 | `1280.jpeg` |
| **Tablet master** | **1024** | **人工精修（png）** | `1024.png` |
| Tablet | 768 | 单列/折叠阈值回归 | `768.jpeg` |
| Large phone | 430 | 移动回归 | `430.jpeg` |
| **Mobile master** | **390** | **人工精修（png）** | `390.png` |
| Small phone | 360 | 最小屏回归 | `360.jpeg` |

## 覆盖计数（真实落盘）
- 屏幕总数：44（ACC 4 / CTH 10 / BMP 11 / AI 5 / SYS 8 / SH 6）
- 每屏 9 张：8 视口 + 1440 深色 = **44 × 9 = 396 张**
- 每屏 1 张 13 态状态板：`14_visual_regression/stateboards/<ID>.jpeg` = **44 张**
- 结构回归：横向溢出 >2px = 0；未渲染 `⟦key⟧` = 0；每屏到达 ready（详见 `14_visual_regression/regression_report.json`，errors=0）
- 关键屏 130% 缩放（AI-01/CTH-01/SH-01/AI-02/CTH-09/BMP-01）横向溢出 = 0px

## 自适应规则（不是缩放）
- ≥1025：侧栏索引目录 + 主区**页边序轴**；多列 minmax(0,1fr) 网格。
- 768–1024：侧栏收为可读文字窄栏（不空图标栏），网格降列。
- ≤768：抽屉式上下文默认关闭（修复早期手机覆盖问题），长步骤链横向滑动。
- ≤560：顶栏领域透镜隐藏（收入主体抽屉），底部 Dock 导航；≤430 抽屉变全宽 Sheet。
- 字号/间距全部 `clamp()` 流体（正文近恒定、展示级随屏缩放）；组件、字号、架构随设备自适应，非固定像素。
- 深色模式：1440-dark 全覆盖；`prefers-reduced-motion` 截图落定终态（动效在 demo 视频保留）。

## 复算方式
遍历 `14_visual_regression/shots/*`：每个屏幕目录应恰有 9 个文件；`build/capture_all.py` 为幂等再生成入口。
