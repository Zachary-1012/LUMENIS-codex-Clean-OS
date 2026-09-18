# LUMENIS P0-D 当前源码能力找回证据

生成时间：2026-09-12T11:14:44.425879+00:00

## 事实摘要

- Commit：`2a3be0ab2ef79cb0274c5b9a21114f3ce2e371af`
- Git 跟踪文件：3800
- Python 文件：983，解析错误：0
- UI 文件：100
- Python 函数：11200，类：1464
- 后端路由声明：843，前端 API 引用：216
- 数据表引用：456
- Runtime 入口：app.py
- 入口静态可达 Python：241；未达生产候选：287

## 状态解释

`RUNTIME_REACHABLE_CANDIDATE` 只表示从入口静态 import 可达，不等于运行中或已发布。
`UNREACHED` 不等于 DEAD；动态 import、蓝图注册、脚本入口与外部进程必须在后续 Runtime 验证中确认。
归档、研究、测试和治理目录只记录其仓库区域，不据此判断业务功能是否无效。

## 能力信号覆盖

| 能力族 | 文件候选数 | Runtime 静态可达数 | 路由数 | 表引用数 | UI API 引用数 |
|---|---:|---:|---:|---:|---:|
| Collection | 583 | 157 | 659 | 383 | 88 |
| Evidence | 262 | 67 | 444 | 314 | 78 |
| Canonical Data | 186 | 63 | 457 | 211 | 21 |
| Report | 234 | 73 | 563 | 255 | 43 |
| Risk | 439 | 130 | 567 | 308 | 149 |
| Event | 346 | 99 | 598 | 321 | 133 |
| Case | 193 | 38 | 390 | 212 | 135 |
| KOS/KOL/KOC | 128 | 44 | 409 | 226 | 13 |
| AI Gateway | 240 | 75 | 484 | 237 | 17 |
| Agent | 257 | 60 | 468 | 231 | 30 |
| Browser/Auth | 488 | 132 | 668 | 348 | 119 |
| Permission/Security | 205 | 56 | 460 | 209 | 75 |
| Evaluation/Learning | 235 | 76 | 577 | 252 | 48 |
| Runtime | 325 | 86 | 482 | 315 | 26 |
| Content Creation | 73 | 13 | 325 | 140 | 14 |

## 红线结论

- 该产物是源码事实索引，不是完成率报告。
- 产品归属只能是 CTH、BMP、Shared Capability、SYSTEM；Agent 是跨产品执行层。
- 所有未达候选保留为 UNKNOWN/UNREACHED，未经依赖与 Runtime 验证不得删除。
- 完整逐文件、逐函数、逐路由、逐表和逐 UI API 证据位于同名 JSON。
