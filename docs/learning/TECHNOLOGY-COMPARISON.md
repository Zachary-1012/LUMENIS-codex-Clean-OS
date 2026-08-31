# TECHNOLOGY-COMPARISON · 技术方案横向择优

> 评分 1–5（5 最好）。原则：**最小复杂度 + 最大可靠性 + 足够性能 + 可持续扩展**；不默认"最新=最优"。数据来源见 CASE-STUDIES（2026-08-31 GitHub 一手）。

## 1. 浏览器自动化
| 方案 | 正确性 | 稳定 | 生态 | 资源 | 复杂度 | 兼容现状 | 结论 |
|---|---|---|---|---|---|---|---|
| Playwright Py（Apache-2.0,15k★） | 5 | 5 | 4 | 4 | 4 | 5（已在用） | **主** |
| Selenium（Apache-2.0,34k★） | 4 | 3 | 5 | 3 | 3 | 2（本仓 0 import） | DEPRECATED 候选，回归后退 |
| Crawlee Py（Apache-2.0,9.5k★） | 4 | 4 | 3 | 3 | 3 | 2 | 学队列/自适应限速，不引框架 |

## 2. 调度
| 方案 | 可靠 | 运维成本 | 复杂度 | 动态频率契合 | 结论 |
|---|---|---|---|---|---|
| APScheduler（MIT,7.6k★，进程内） | 4 | 5（无外部依赖） | 5 | 5 | **采用** |
| Celery（BSD,28.8k★，需 broker） | 5 | 2（要 Redis/Rabbit） | 2 | 3 | 单机场景不采用 |
| Windows Task Scheduler | 3 | 4 | 5 | 2 | 仅用于 Git 同步等 OS 级定时 |

## 3. 生产 WSGI / 进程守护（关键：Windows 约束）
| 方案 | Windows 原生 | 生产级 | 结论 |
|---|---|---|---|
| Flask dev server | 是 | 1（不可生产） | 仅本地调试 |
| **waitress（1.6k★，纯Py跨平台）** | **是** | 4 | **Windows 阶段采用** |
| gunicorn（10.7k★） | 否 | 5 | 仅未来 Linux |
| supervisor（9.1k★） | 否 | 4 | 仅未来 Linux |
| run_supervised（自研看门狗） | 是 | 3 | 现状保留，逐步与 waitress 组合 |
| Docker restart:unless-stopped + healthcheck | 需 Docker Desktop | 5 | 可选自愈路径 |

## 4. 数据库迁移
| 方案 | 可回滚 | 自动生成 | 风险 | 结论 |
|---|---|---|---|---|
| 手写向后兼容（现状） | 中 | 否 | 依赖人 | 保留为底线 |
| **Alembic（MIT,4.4k★）** | 5（downgrade） | 是 | 首次 baseline 需 Staging 验证 | **候选采用**，红线表只读 baseline |

## 5. 自身服务健壮性（非对抗平台）
| 需求 | 选择 | License/star | 备注 |
|---|---|---|---|
| 对外 API 限流 | slowapi | MIT/2.1k | 保护自身，不用于撞平台 |
| 网络退避重试 | **tenacity** | Apache-2.0/8.8k | 与 backoff（MIT/2.7k）**二选一**，不并引 |
| 熔断状态机 | 自研保留 | — | 贴合 300012/验证码语义，学 circuitbreaker 三态命名 |

## 6. 可观测
| 阶段 | 选择 | 说明 |
|---|---|---|
| 现在 | structlog（4.9k★）统一日志键 | 低成本、立即可做 |
| 下一步 | prometheus_client /metrics（4.4k★） | 指标化采集健康/调度 |
| 远期 | OpenTelemetry（2.6k★） | 多服务链路时才上，现在过度 |

## 7. 学习/知识存储
| 方案 | 额外服务 | 契合单文件 | 语义检索 | 结论 |
|---|---|---|---|---|
| 纯 SQLite 表（现状） | 无 | 5 | 1 | 结构化足够先用 |
| **sqlite-vec（Apache-2.0,8.1k★）** | 无（扩展） | 4 | 4 | **候选**，案例/事件语义检索 |
| Chroma/Qdrant 等独立向量库 | 要 | 1 | 5 | 违背最小复杂度，不采用 |

## 8. 依赖/环境与多仓
- uv（Apache-2.0,89k★）：Staging 可复现环境候选，不强制替换现有 venv。
- Nx（MIT,29k★）/Changesets（MIT,12.3k★）：三仓独立非 monorepo，**不引 Nx**；学 Changesets 变更单绑定版本。

## 9. UI Token
- Style Dictionary（Apache-2.0,4.8k★）：学 primitive/semantic/component 三层 token 方法；实现用原生 CSS 变量，不引 Node 构建链。

## 10. 择优总览（NOW 可做 / 候选 / 不采用）
- **NOW（低风险、纯增量或离线工具）**：pytest 统一入口、pydeps 交叉校验、tenacity 替代手写网络重试（仅网络层）、ADR 编号规范、structlog 日志键。
- **CANDIDATE（需 Staging + Gate）**：waitress（Windows 生产入口）、alembic（迁移 baseline）、sqlite-vec（学习库）、slowapi、prometheus /metrics、watchdog（自动版本触发）、uv（环境复现）。
- **REJECT（当前阶段）**：Celery、Nx、Scrapy、独立向量库、gunicorn/supervisor（Windows 不可用）、Backstage 平台本体、tree-sitter（当前正则足够）。
